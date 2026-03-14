import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

class ModerationLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings_file = "data/warnings.json"
        self.warning_expiry_days = 30  # Warnings expire after 30 days
        self.load_warnings()
        self.cleanup_expired_warnings.start()
    
    @tasks.loop(hours=1)
    async def cleanup_expired_warnings(self):
        """Auto-cleanup expired warnings"""
        now = datetime.now()
        updated = False
        
        for member_id in list(self.warnings.keys()):
            active_warnings = []
            for warn in self.warnings[member_id]:
                warn_time = datetime.fromisoformat(warn['timestamp'])
                days_old = (now - warn_time).days
                if days_old < self.warning_expiry_days:
                    active_warnings.append(warn)
                else:
                    updated = True
            
            if active_warnings:
                self.warnings[member_id] = active_warnings
            else:
                del self.warnings[member_id]
                updated = True
        
        if updated:
            self.save_warnings()
    
    @cleanup_expired_warnings.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()
    
    def load_warnings(self):
        """Load warnings from JSON file"""
        if os.path.exists(self.warnings_file):
            with open(self.warnings_file, 'r') as f:
                self.warnings = json.load(f)
        else:
            self.warnings = {}
    
    def save_warnings(self):
        """Save warnings to JSON file"""
        with open(self.warnings_file, 'w') as f:
            json.dump(self.warnings, f, indent=2)
    
    async def get_modlog_channel(self, guild: discord.Guild):
        """Get modlog channel from guild"""
        modlog_channel_id = os.getenv('MODLOG_CHANNEL_ID')
        if not modlog_channel_id:
            return None
        
        try:
            return await self.bot.fetch_channel(int(modlog_channel_id))
        except Exception as e:
            print(f"Error fetching modlog channel: {e}")
            return None
    
    async def log_action(self, guild: discord.Guild, action: str, moderator: discord.Member, target: discord.User, reason: str = "No reason provided"):
        """Log moderation action to channel"""
        modlog_channel = await self.get_modlog_channel(guild)
        if not modlog_channel:
            return
        
        # Create embed based on action
        if action == "warn":
            color = discord.Color.yellow()
            emoji = "⚠️"
        elif action == "kick":
            color = discord.Color.orange()
            emoji = "👢"
        elif action == "ban":
            color = discord.Color.red()
            emoji = "🔨"
        elif action == "unwarn":
            color = discord.Color.green()
            emoji = "✅"
        elif action == "clearwarnings":
            color = discord.Color.green()
            emoji = "🔄"
        else:
            color = discord.Color.blurple()
            emoji = "📋"
        
        embed = discord.Embed(
            title=f"{emoji} {action.upper()} Action Logged",
            description=f"**Target:** {target.mention}\n**Moderator:** {moderator.mention}",
            color=color,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Target ID", value=target.id, inline=True)
        embed.add_field(name="Moderator ID", value=moderator.id, inline=True)
        
        if action == "warn" and str(target.id) in self.warnings:
            warn_count = len(self.warnings[str(target.id)])
            embed.add_field(name="Total Warnings", value=warn_count, inline=True)
        
        embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
        embed.set_footer(text=f"Guild: {guild.name}")
        
        await modlog_channel.send(embed=embed)
    
    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="Member to warn", reason="Reason for warning")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        """Warn a member"""
        
        # Prevent warning bot or self
        if member.bot:
            await interaction.response.send_message("❌ Can't warn a bot!", ephemeral=True)
            return
        
        if member == interaction.user:
            await interaction.response.send_message("❌ You can't warn yourself!", ephemeral=True)
            return
        
        # Add warning
        member_id = str(member.id)
        if member_id not in self.warnings:
            self.warnings[member_id] = []
        
        self.warnings[member_id].append({
            "reason": reason,
            "moderator": str(interaction.user.id),
            "timestamp": datetime.now().isoformat()
        })
        self.save_warnings()
        
        warn_count = len(self.warnings[member_id])
        
        # Log to modlog channel
        await self.log_action(interaction.guild, "warn", interaction.user, member, reason)
        
        # Send response
        embed = discord.Embed(
            title="⚠️ Member Warned",
            description=f"{member.mention} has been warned",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warnings", value=warn_count, inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="kick", description="Kick a member from server")
    @app_commands.describe(member="Member to kick", reason="Reason for kicking")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        """Kick a member"""
        
        # Prevent kicking bot or self
        if member.bot:
            await interaction.response.send_message("❌ Can't kick a bot!", ephemeral=True)
            return
        
        if member == interaction.user:
            await interaction.response.send_message("❌ You can't kick yourself!", ephemeral=True)
            return
        
        # Check hierarchy
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ You can't kick someone with equal or higher role!",
                ephemeral=True
            )
            return
        
        try:
            # Log to modlog channel BEFORE kicking
            await self.log_action(interaction.guild, "kick", interaction.user, member, reason)
            
            # Send DM to member
            try:
                embed = discord.Embed(
                    title="👢 You were kicked",
                    description=f"You were kicked from {interaction.guild.name}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
                await member.send(embed=embed)
            except discord.Forbidden:
                pass  # User has DMs disabled
            
            # Kick the member
            await interaction.guild.kick(member, reason=reason)
            
            # Send response
            embed = discord.Embed(
                title="👢 Member Kicked",
                description=f"{member} has been kicked from the server",
                color=discord.Color.orange()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to kick this member!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error kicking member: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="ban", description="Ban a member from server")
    @app_commands.describe(member="Member to ban", reason="Reason for banning", delete_messages="Delete messages (0-7 days)")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided", delete_messages: int = 0):
        """Ban a member"""
        
        # Validate delete_messages
        if not 0 <= delete_messages <= 7:
            await interaction.response.send_message(
                "❌ delete_messages must be between 0-7 days!",
                ephemeral=True
            )
            return
        
        # Prevent banning bot or self
        if member.bot:
            await interaction.response.send_message("❌ Can't ban a bot!", ephemeral=True)
            return
        
        if member == interaction.user:
            await interaction.response.send_message("❌ You can't ban yourself!", ephemeral=True)
            return
        
        # Check hierarchy
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ You can't ban someone with equal or higher role!",
                ephemeral=True
            )
            return
        
        try:
            # Log to modlog channel BEFORE banning
            reason_with_deletion = f"{reason}\n(Messages deleted from last {delete_messages} days)"
            await self.log_action(interaction.guild, "ban", interaction.user, member, reason_with_deletion)
            
            # Send DM to member
            try:
                embed = discord.Embed(
                    title="🔨 You were banned",
                    description=f"You were banned from {interaction.guild.name}",
                    color=discord.Color.red()
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
                await member.send(embed=embed)
            except discord.Forbidden:
                pass  # User has DMs disabled
            
            # Ban the member
            await interaction.guild.ban(member, reason=reason, delete_message_seconds=delete_messages*86400)
            
            # Send response
            embed = discord.Embed(
                title="🔨 Member Banned",
                description=f"{member} has been banned from the server",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Messages Deleted", value=f"{delete_messages} days", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to ban this member!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error banning member: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="warnings", description="Check warnings for a member")
    @app_commands.describe(member="Member to check")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        """Check member warnings"""
        
        member_id = str(member.id)
        
        if member_id not in self.warnings or not self.warnings[member_id]:
            embed = discord.Embed(
                title=f"📋 Warnings for {member}",
                description="No warnings recorded",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        warns = self.warnings[member_id]
        embed = discord.Embed(
            title=f"📋 Warnings for {member}",
            description=f"Total warnings: {len(warns)}",
            color=discord.Color.yellow()
        )
        
        for i, warn in enumerate(warns[-10:], 1):  # Show last 10 warnings
            timestamp = datetime.fromisoformat(warn['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
            embed.add_field(
                name=f"Warning #{len(warns)-10+i}",
                value=f"**Reason:** {warn['reason']}\n**Date:** {timestamp}",
                inline=False
            )
        
        embed.set_footer(text=f"Warnings expire after {self.warning_expiry_days} days")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unwarn", description="Remove the last warning from a member")
    @app_commands.describe(member="Member to remove warning from")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unwarn(self, interaction: discord.Interaction, member: discord.Member):
        """Remove the last warning from a member"""
        
        member_id = str(member.id)
        
        if member_id not in self.warnings or not self.warnings[member_id]:
            await interaction.response.send_message(
                f"❌ {member} has no warnings!",
                ephemeral=True
            )
            return
        
        # Remove last warning
        removed_warn = self.warnings[member_id].pop()
        
        if not self.warnings[member_id]:
            del self.warnings[member_id]
        
        self.save_warnings()
        
        # Log to modlog
        await self.log_action(
            interaction.guild,
            "unwarn",
            interaction.user,
            member,
            f"Removed warning: {removed_warn['reason']}"
        )
        
        embed = discord.Embed(
            title="✅ Warning Removed",
            description=f"Last warning removed from {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Removed Reason", value=removed_warn['reason'], inline=False)
        
        remaining = len(self.warnings.get(member_id, []))
        embed.add_field(name="Remaining Warnings", value=remaining, inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="clearwarnings", description="Clear all warnings for a member")
    @app_commands.describe(member="Member to clear warnings from")
    @app_commands.checks.has_permissions(ban_members=True)
    async def clearwarnings(self, interaction: discord.Interaction, member: discord.Member):
        """Clear all warnings for a member"""
        
        member_id = str(member.id)
        
        if member_id not in self.warnings or not self.warnings[member_id]:
            await interaction.response.send_message(
                f"❌ {member} has no warnings to clear!",
                ephemeral=True
            )
            return
        
        warn_count = len(self.warnings[member_id])
        
        # Clear all warnings
        del self.warnings[member_id]
        self.save_warnings()
        
        # Log to modlog
        await self.log_action(
            interaction.guild,
            "clearwarnings",
            interaction.user,
            member,
            f"Cleared {warn_count} warning(s) - Fresh start"
        )
        
        embed = discord.Embed(
            title="🔄 Warnings Cleared",
            description=f"All warnings cleared for {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Warnings Cleared", value=warn_count, inline=True)
        embed.add_field(name="Status", value="Fresh start ✅", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ModerationLog(bot))
