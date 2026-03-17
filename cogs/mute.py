"""Mute/Timeout Command - Moderate members"""
import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
import re

class Mute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def parse_duration(self, duration_str: str) -> timedelta:
        """Parse duration string (e.g., '30m', '2h', '1d') to timedelta"""
        match = re.match(r'(\d+)([mhd])', duration_str.lower())
        
        if not match:
            raise ValueError("Invalid format. Use: 30m, 2h, 1d, etc.")
        
        amount = int(match.group(1))
        unit = match.group(2)
        
        if unit == 'm':
            return timedelta(minutes=amount)
        elif unit == 'h':
            return timedelta(hours=amount)
        elif unit == 'd':
            return timedelta(days=amount)
        else:
            raise ValueError("Invalid unit. Use: m (minutes), h (hours), d (days)")
    
    def format_duration(self, duration: timedelta) -> str:
        """Format timedelta to readable string"""
        total_seconds = int(duration.total_seconds())
        
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "Less than a minute"
    
    @app_commands.command(name="mute", description="Timeout a member for specified duration")
    @app_commands.describe(
        member="Member to mute",
        duration="Duration (e.g., 30m, 2h, 1d)",
        reason="Reason for mute (optional)"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, 
                   duration: str, reason: str = None):
        """Mute/timeout a member"""
        
        # Check if trying to mute bot
        if member.bot:
            await interaction.response.send_message(
                "Cannot mute a bot",
                ephemeral=True
            )
            return
        
        # Check if trying to mute self
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "You cannot mute yourself",
                ephemeral=True
            )
            return
        
        # Check role hierarchy - user cannot mute someone with equal or higher role
        if member.top_role >= interaction.user.top_role:
            embed = discord.Embed(
                title="Cannot Mute",
                description=f"You cannot mute {member.mention} because their role is equal to or higher than yours",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check role hierarchy - bot cannot mute someone with equal or higher role than bot
        if member.top_role >= interaction.guild.me.top_role:
            embed = discord.Embed(
                title="Cannot Mute",
                description=f"I cannot mute {member.mention} because their role is equal to or higher than mine",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Parse duration
        try:
            timeout_duration = self.parse_duration(duration)
        except ValueError as e:
            embed = discord.Embed(
                title="Invalid Duration",
                description=str(e),
                color=discord.Color.red()
            )
            embed.add_field(
                name="Examples",
                value="`/mute @user 30m` - 30 minutes\n"
                      "`/mute @user 2h` - 2 hours\n"
                      "`/mute @user 1d` - 1 day",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Max timeout is 28 days
        if timeout_duration > timedelta(days=28):
            await interaction.response.send_message(
                "Maximum mute duration is 28 days",
                ephemeral=True
            )
            return
        
        try:
            # Apply timeout
            await member.timeout(timeout_duration, reason=reason)
            
            # Log to modlog
            modlog_cog = self.bot.get_cog('ModerationLog')
            if modlog_cog:
                log_reason = f"Muted for {self.format_duration(timeout_duration)}. Reason: {reason or 'No reason provided'}"
                await modlog_cog.log_action(interaction.guild, "mute", interaction.user, member, log_reason)
            
            # Create success embed
            embed = discord.Embed(
                title="Member Muted",
                description=f"{member.mention} has been muted",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="Duration",
                value=self.format_duration(timeout_duration),
                inline=True
            )
            embed.add_field(
                name="Muted By",
                value=interaction.user.mention,
                inline=True
            )
            embed.add_field(
                name="Reason",
                value=reason or "No reason provided",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to mute this member",
                ephemeral=True
            )
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Failed to mute member: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unmute", description="Remove mute from a member")
    @app_commands.describe(
        member="Member to unmute",
        reason="Reason for unmute (optional)"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, 
                     reason: str = None):
        """Unmute/remove timeout from member"""
        
        # Check if member is actually timed out
        if not member.is_timed_out():
            embed = discord.Embed(
                title="Not Muted",
                description=f"{member.mention} is not currently muted",
                color=discord.Color.yellow()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Remove timeout
            await member.timeout(None, reason=reason)
            
            # Log to modlog
            modlog_cog = self.bot.get_cog('ModerationLog')
            if modlog_cog:
                log_reason = f"Unmuted. Reason: {reason or 'No reason provided'}"
                await modlog_cog.log_action(interaction.guild, "unmute", interaction.user, member, log_reason)
            
            # Create success embed
            embed = discord.Embed(
                title="Member Unmuted",
                description=f"{member.mention} has been unmuted",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Unmuted By",
                value=interaction.user.mention,
                inline=True
            )
            embed.add_field(
                name="Reason",
                value=reason or "No reason provided",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to unmute this member",
                ephemeral=True
            )
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Failed to unmute member: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(Mute(bot))
