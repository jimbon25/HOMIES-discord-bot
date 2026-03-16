"""Dynamic Voice Channel Management"""
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

class VoiceChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vc_data_file = "data/voice_channels.json"
        self.rename_cooldowns = defaultdict(lambda: None)  # Track rename cooldowns per user
        self.load_vc_data()
    
    def load_vc_data(self):
        """Load voice channel data"""
        if not os.path.exists(self.vc_data_file):
            self.save_vc_data({})
    
    def get_vc_data(self):
        """Get voice channel data"""
        if os.path.exists(self.vc_data_file):
            with open(self.vc_data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_vc_data(self, data):
        """Save voice channel data"""
        os.makedirs(os.path.dirname(self.vc_data_file), exist_ok=True)
        with open(self.vc_data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_user_voice_channel(self, user: discord.Member) -> discord.VoiceChannel:
        """Get user's current voice channel"""
        return user.voice.channel if user.voice else None
    
    def is_channel_owner(self, user_id: int, channel_id: int) -> bool:
        """Check if user owns the voice channel"""
        data = self.get_vc_data()
        channel_data = data.get(str(channel_id), {})
        return channel_data.get("owner_id") == user_id
    
    def check_rename_cooldown(self, user_id: int) -> tuple:
        """Check if user is on rename cooldown. Returns (is_on_cooldown, remaining_seconds)"""
        last_rename = self.rename_cooldowns[user_id]
        
        if last_rename is None:
            return False, 0
        
        elapsed = (datetime.now() - last_rename).total_seconds()
        cooldown_duration = 300  # 5 minutes in seconds
        
        if elapsed < cooldown_duration:
            remaining = int(cooldown_duration - elapsed)
            return True, remaining
        
        return False, 0
    
    def set_rename_cooldown(self, user_id: int):
        """Set rename cooldown for user"""
        self.rename_cooldowns[user_id] = datetime.now()
    
    def register_channel(self, channel_id: int, owner_id: int, guild_id: int):
        """Register a voice channel as managed"""
        data = self.get_vc_data()
        data[str(channel_id)] = {
            "owner_id": owner_id,
            "guild_id": guild_id,
            "created_at": datetime.now().isoformat(),
            "original_name": None,
            "is_locked": False
        }
        self.save_vc_data(data)
    
    def unregister_channel(self, channel_id: int):
        """Remove channel from management"""
        data = self.get_vc_data()
        if str(channel_id) in data:
            del data[str(channel_id)]
            self.save_vc_data(data)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice channel state updates"""
        # Check if user left a voice channel (either disconnect or moved to different channel)
        if before.channel and (not after.channel or before.channel != after.channel):
            channel = before.channel
            data = self.get_vc_data()
            
            if str(channel.id) in data:
                # Check if channel is now empty and should be deleted
                if len(channel.members) == 0:
                    try:
                        await channel.delete()
                        self.unregister_channel(channel.id)
                    except Exception as e:
                        print(f"Error deleting empty VC: {e}")
    
    vc_group = app_commands.Group(name="vc", description="Voice channel management commands")
    
    @vc_group.command(name="rename", description="Rename your voice channel")
    @app_commands.describe(name="New channel name (max 100 characters)", channel="Target voice channel (leave empty for your current channel)")
    async def vc_rename(self, interaction: discord.Interaction, name: str, channel: discord.VoiceChannel = None):
        """Rename voice channel"""
        # Get channel - use provided channel or user's current channel
        if channel is None:
            if not interaction.user.voice or not interaction.user.voice.channel:
                embed = discord.Embed(
                    title="❌ No Channel Specified",
                    description="You must be in a voice channel or specify a channel",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            channel = interaction.user.voice.channel
        
        # Check cooldown (Discord rate limit: 2 renames per 10 minutes)
        is_cooldown, remaining = self.check_rename_cooldown(interaction.user.id)
        if is_cooldown:
            embed = discord.Embed(
                title="⏳ Cooldown Active",
                description=f"You can rename again in {remaining} seconds",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Reason",
                value="Discord limits channel renames to 2 per 10 minutes",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check permissions
        if not (self.is_channel_owner(interaction.user.id, channel.id) or 
                interaction.user.guild_permissions.administrator):
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only channel owner or server admin can rename this channel",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Validate name length
        if len(name) > 100:
            embed = discord.Embed(
                title="❌ Name Too Long",
                description="Channel name must be 100 characters or less",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await channel.edit(name=name)
            
            # Set cooldown
            self.set_rename_cooldown(interaction.user.id)
            
            # Update data
            data = self.get_vc_data()
            if str(channel.id) in data:
                data[str(channel.id)]["original_name"] = channel.name
                self.save_vc_data(data)
            
            embed = discord.Embed(
                title="✅ Channel Renamed",
                description=f"Voice channel renamed to **{name}**",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Cooldown",
                value="You can rename again in 5 minutes",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f"Error renaming channel: {str(e)}",
                ephemeral=True
            )
    
    @vc_group.command(name="limit", description="Set user limit in voice channel")
    @app_commands.describe(limit="User limit (0 for unlimited, 1-99)")
    async def vc_limit(self, interaction: discord.Interaction, limit: int):
        """Set voice channel limit"""
        # Validate limit
        if limit < 0 or limit > 99:
            await interaction.response.send_message(
                "❌ Limit must be between 0 (unlimited) and 99",
                ephemeral=True
            )
            return
        
        # Check if user in voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ You must be in a voice channel to use this command",
                ephemeral=True
            )
            return
        
        channel = interaction.user.voice.channel
        
        # Check permissions
        if not (self.is_channel_owner(interaction.user.id, channel.id) or 
                interaction.user.guild_permissions.administrator):
            await interaction.response.send_message(
                "❌ You don't have permission to modify this channel",
                ephemeral=True
            )
            return
        
        try:
            await channel.edit(user_limit=limit)
            
            limit_text = "unlimited" if limit == 0 else str(limit)
            await interaction.response.send_message(
                f"✅ Voice channel limit set to **{limit_text}** users",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error setting limit: {str(e)}",
                ephemeral=True
            )
    
    @vc_group.command(name="lock", description="Lock or unlock your voice channel")
    @app_commands.describe(action="Lock action: lock or unlock", channel="Target voice channel (leave empty for your current channel)")
    async def vc_lock(self, interaction: discord.Interaction, action: str, channel: discord.VoiceChannel = None):
        """Lock/unlock voice channel"""
        # Validate action
        if action.lower() not in ["lock", "unlock"]:
            await interaction.response.send_message(
                "❌ Use 'lock' or 'unlock'",
                ephemeral=True
            )
            return
        
        # Get channel - use provided channel or user's current channel
        if channel is None:
            if not interaction.user.voice or not interaction.user.voice.channel:
                embed = discord.Embed(
                    title="❌ No Channel Specified",
                    description="You must be in a voice channel or specify a channel",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            channel = interaction.user.voice.channel
        
        # Check permissions
        if not (self.is_channel_owner(interaction.user.id, channel.id) or 
                interaction.user.guild_permissions.administrator):
            await interaction.response.send_message(
                "❌ You don't have permission to lock/unlock this channel",
                ephemeral=True
            )
            return
        
        try:
            is_locking = action.lower() == "lock"
            
            # Get everyone role
            everyone_role = interaction.guild.default_role
            
            if is_locking:
                # Lock: deny view/connect
                await channel.set_permissions(
                    everyone_role,
                    view_channel=False,
                    connect=False
                )
                status = "🔒 locked"
            else:
                # Unlock: reset permissions
                await channel.set_permissions(everyone_role, view_channel=None, connect=None)
                status = "🔓 unlocked"
            
            # Update data
            data = self.get_vc_data()
            if str(channel.id) in data:
                data[str(channel.id)]["is_locked"] = is_locking
                self.save_vc_data(data)
            
            await interaction.response.send_message(
                f"✅ Voice channel is now {status}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error locking channel: {str(e)}",
                ephemeral=True
            )
    
    @vc_group.command(name="claim", description="Claim ownership of a voice channel")
    async def vc_claim(self, interaction: discord.Interaction):
        """Claim voice channel ownership"""
        # Check if user in voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ You must be in a voice channel to use this command",
                ephemeral=True
            )
            return
        
        channel = interaction.user.voice.channel
        data = self.get_vc_data()
        
        # Check if channel is already owned by someone else
        if str(channel.id) in data:
            owner_id = data[str(channel.id)]["owner_id"]
            if owner_id != interaction.user.id:
                await interaction.response.send_message(
                    f"❌ This channel is already owned by <@{owner_id}>",
                    ephemeral=True
                )
                return
            else:
                await interaction.response.send_message(
                    "❌ You already own this channel",
                    ephemeral=True
                )
                return
        
        # Claim the channel
        self.register_channel(channel.id, interaction.user.id, interaction.guild.id)
        
        await interaction.response.send_message(
            f"✅ You now own this voice channel! Use `/vc` commands to manage it",
            ephemeral=True
        )
    
    @vc_group.command(name="info", description="Get info about current voice channel")
    @app_commands.describe(channel="Target voice channel (leave empty for your current channel)")
    async def vc_info(self, interaction: discord.Interaction, channel: discord.VoiceChannel = None):
        """Get voice channel info"""
        # Get channel - use provided channel or user's current channel
        if channel is None:
            if not interaction.user.voice or not interaction.user.voice.channel:
                embed = discord.Embed(
                    title="❌ No Channel Specified",
                    description="You must be in a voice channel or specify a channel",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            channel = interaction.user.voice.channel
        
        data = self.get_vc_data()
        channel_data = data.get(str(channel.id), {})
        
        embed = discord.Embed(
            title="🎙️ Voice Channel Info",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Channel", value=f"**{channel.name}**", inline=False)
        embed.add_field(name="Members", value=f"**{len(channel.members)}**", inline=True)
        
        limit_text = "Unlimited" if channel.user_limit == 0 else str(channel.user_limit)
        embed.add_field(name="User Limit", value=limit_text, inline=True)
        
        if str(channel.id) in data:
            owner_id = channel_data.get("owner_id")
            is_locked = channel_data.get("is_locked", False)
            embed.add_field(name="Owner", value=f"<@{owner_id}>", inline=True)
            embed.add_field(name="Status", value=f"{'🔒 Locked' if is_locked else '🔓 Unlocked'}", inline=True)
        else:
            embed.add_field(name="Owner", value="None (not managed)", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @vc_group.command(name="kick", description="Kick a member from voice channel")
    @app_commands.describe(member="Member to kick from the voice channel", channel="Target voice channel (leave empty for your current channel)")
    async def vc_kick(self, interaction: discord.Interaction, member: discord.Member, channel: discord.VoiceChannel = None):
        """Kick member from voice channel (owner or admin only)"""
        # Get channel - use provided channel or user's current channel
        if channel is None:
            if not interaction.user.voice or not interaction.user.voice.channel:
                embed = discord.Embed(
                    title="❌ No Channel Specified",
                    description="You must be in a voice channel or specify a channel",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            channel = interaction.user.voice.channel
        
        # Check permissions (owner or admin)
        is_owner = self.is_channel_owner(interaction.user.id, channel.id)
        is_admin = interaction.user.guild_permissions.administrator
        
        if not (is_owner or is_admin):
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only channel owner or server admin can kick members",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if target is in same channel
        if member.voice is None or member.voice.channel != channel:
            embed = discord.Embed(
                title="❌ Not in Channel",
                description=f"**{member.name}** is not in this voice channel",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await member.move_to(None)
            
            embed = discord.Embed(
                title="✅ Member Kicked",
                description=f"**{member.name}** has been kicked from {channel.name}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to kick member: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @vc_group.command(name="mute", description="Mute members in voice channel")
    @app_commands.describe(action="Action: mute or unmute", member="Member to mute/unmute (leave empty for all)", channel="Target voice channel (leave empty for your current channel)")
    async def vc_mute(self, interaction: discord.Interaction, action: str, member: discord.Member = None, channel: discord.VoiceChannel = None):
        """Mute/unmute members in voice channel (owner or admin only)"""
        # Validate action
        if action.lower() not in ["mute", "unmute"]:
            embed = discord.Embed(
                title="❌ Invalid Action",
                description="Use 'mute' or 'unmute'",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get channel - use provided channel or user's current channel
        if channel is None:
            if not interaction.user.voice or not interaction.user.voice.channel:
                embed = discord.Embed(
                    title="❌ No Channel Specified",
                    description="You must be in a voice channel or specify a channel",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            channel = interaction.user.voice.channel
        
        # Check permissions (owner or admin)
        is_owner = self.is_channel_owner(interaction.user.id, channel.id)
        is_admin = interaction.user.guild_permissions.administrator
        
        if not (is_owner or is_admin):
            embed = discord.Embed(
                title="❌ No Permission",
                description="Only channel owner or server admin can mute members",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            is_muting = action.lower() == "mute"
            
            # If specific member provided, mute only that member
            if member:
                # Check if member is in same channel
                if member.voice is None or member.voice.channel != channel:
                    embed = discord.Embed(
                        title="❌ Not in Channel",
                        description=f"**{member.name}** is not in this voice channel",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                await member.edit(mute=is_muting)
                action_text = "muted" if is_muting else "unmuted"
                
                embed = discord.Embed(
                    title=f"✅ Member {action_text.capitalize()}",
                    description=f"**{member.name}** has been {action_text}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Channel", value=f"**{channel.name}**", inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # Mute/unmute all members
                count = 0
                
                for target_member in channel.members:
                    try:
                        await target_member.edit(mute=is_muting)
                        count += 1
                    except:
                        pass
                
                action_text = "muted" if is_muting else "unmuted"
                embed = discord.Embed(
                    title=f"✅ Members {action_text.capitalize()}",
                    description=f"**{count}** member(s) have been {action_text}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Channel", value=f"**{channel.name}**", inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to mute member: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(VoiceChannelManager(bot))
