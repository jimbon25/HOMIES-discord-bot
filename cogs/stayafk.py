"""Stay AFK - Bot joins voice channel and stays AFK"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class StayAFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # Track bot's voice connections per guild
        self.stay_afk_mode = {}  # Track which guilds are in stay_afk mode
        self.alone_since = {}  # Track when bot became alone (guild_id -> datetime)
        self.alone_threshold = 180  # Auto-disconnect after 3 minutes alone (180 seconds)
        self.check_alone.start()  # Start background task
    
    @tasks.loop(minutes=1)
    async def check_alone(self):
        """Check if bot is alone in voice channel and auto-disconnect after timeout"""
        for guild_id in list(self.voice_clients.keys()):
            try:
                voice_client = self.voice_clients[guild_id]
                
                # Check if voice connection is still valid
                if not voice_client or not voice_client.is_connected():
                    if guild_id in self.alone_since:
                        del self.alone_since[guild_id]
                    continue
                
                channel = voice_client.channel
                # Count human members (exclude bots)
                member_count = len([m for m in channel.members if not m.bot])
                
                if member_count == 0:
                    # Bot is alone - track time
                    if guild_id not in self.alone_since:
                        self.alone_since[guild_id] = datetime.now()
                        logger.info(f"⏰ Bot became alone in {channel.name}")
                    else:
                        # Check if timeout reached
                        alone_duration = (datetime.now() - self.alone_since[guild_id]).total_seconds()
                        
                        if alone_duration >= self.alone_threshold:
                            # Time to disconnect
                            logger.info(f"⏱️ Timeout reached! Auto-disconnecting from {channel.name} (alone for {alone_duration:.0f}s)")
                            try:
                                await voice_client.disconnect(force=True)
                                guild = self.bot.get_guild(guild_id)
                                logger.info(f"✅ Auto-disconnected from {channel.name} in {guild.name}")
                            except Exception as e:
                                logger.error(f"Error auto-disconnecting: {e}")
                            finally:
                                # Cleanup tracking
                                self.voice_clients.pop(guild_id, None)
                                self.alone_since.pop(guild_id, None)
                                self.stay_afk_mode.pop(guild_id, None)
                else:
                    # Bot is not alone - reset timer
                    if guild_id in self.alone_since:
                        del self.alone_since[guild_id]
                        logger.info(f"🔄 Reset alone timer in {channel.name} ({member_count} members present)")
            
            except Exception as e:
                logger.error(f"Error checking alone status for guild {guild_id}: {e}")
    
    @check_alone.before_loop
    async def before_check_alone(self):
        """Wait until bot is ready before starting check"""
        await self.bot.wait_until_ready()
    
    stayafk_group = app_commands.Group(name="stayafk", description="Bot stay AFK in voice channel")
    
    @stayafk_group.command(name="join", description="Bot joins your voice channel and stays AFK")
    async def join(self, interaction: discord.Interaction):
        """Bot joins user's voice channel"""
        
        # Check if user is in voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ You must be in a voice channel first",
                ephemeral=True
            )
            return
        
        channel = interaction.user.voice.channel
        guild = interaction.guild
        
        # Check if bot already in channel
        if guild.id in self.voice_clients:
            existing_vc = self.voice_clients[guild.id]
            if existing_vc and existing_vc.is_connected():
                await interaction.response.send_message(
                    f"❌ Bot is already in {existing_vc.channel.mention}",
                    ephemeral=True
                )
                return
        
        try:
            # Bot join voice channel
            voice_client = await channel.connect()
            self.voice_clients[guild.id] = voice_client
            
            # Deafen bot (mute incoming audio)
            try:
                await guild.me.edit(deafen=True)
            except Exception as e:
                logger.debug(f"Deafen error: {e}")
            
            # Mark as in stay_afk mode
            self.stay_afk_mode[guild.id] = True
            
            embed = discord.Embed(
                title="🎤 Bot Joined Voice Channel",
                description=f"Bot is now AFK in {channel.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Channel", value=channel.name, inline=True)
            embed.add_field(name="Status", value="🟢 Stay AFK Mode (Deafened)", inline=True)
            embed.add_field(name="Auto-disconnect", value="After 3 minutes alone", inline=True)
            embed.add_field(name="Stop with", value="`/stayafk leave`", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            # Cleanup on error
            self.voice_clients.pop(guild.id, None)
            logger.error(f"Error joining voice channel: {e}")
            await interaction.response.send_message(
                f"❌ Error joining voice channel: {str(e)}",
                ephemeral=True
            )
    
    @stayafk_group.command(name="leave", description="Bot leaves voice channel")
    async def leave(self, interaction: discord.Interaction):
        """Bot leaves voice channel"""
        guild = interaction.guild
        
        # Check if bot in voice
        if guild.id not in self.voice_clients:
            await interaction.response.send_message(
                "❌ Bot is not in any voice channel",
                ephemeral=True
            )
            return
        
        voice_client = self.voice_clients[guild.id]
        
        try:
            if not voice_client or not voice_client.is_connected():
                await interaction.response.send_message(
                    "❌ Bot is not connected to voice",
                    ephemeral=True
                )
                return
            
            channel_name = voice_client.channel.name if voice_client.channel else "Unknown Channel"
            
            # Disconnect bot
            await voice_client.disconnect(force=True)
            
            # Cleanup tracking
            self.voice_clients.pop(guild.id, None)
            self.stay_afk_mode.pop(guild.id, None)
            self.alone_since.pop(guild.id, None)
            
            embed = discord.Embed(
                title="👋 Bot Left Voice Channel",
                description=f"Bot disconnected from **{channel_name}**",
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            # Cleanup on error
            self.voice_clients.pop(guild.id, None)
            self.stay_afk_mode.pop(guild.id, None)
            self.alone_since.pop(guild.id, None)
            
            logger.error(f"Leave command error: {e}")
            await interaction.response.send_message(
                f"✅ Bot has been disconnected from voice",
                ephemeral=True
            )
    
    @stayafk_group.command(name="status", description="Check bot voice status")
    async def status(self, interaction: discord.Interaction):
        """Check bot's voice connection status"""
        
        guild = interaction.guild
        
        embed = discord.Embed(
            title="📊 Bot Voice Status",
            color=discord.Color.blue()
        )
        
        if guild.id in self.voice_clients:
            voice_client = self.voice_clients[guild.id]
            if voice_client and voice_client.is_connected():
                embed.add_field(
                    name="Status",
                    value="🟢 **Connected**",
                    inline=False
                )
                embed.add_field(
                    name="Channel",
                    value=voice_client.channel.mention,
                    inline=True
                )
                embed.add_field(
                    name="Members",
                    value=str(len(voice_client.channel.members)),
                    inline=True
                )
                embed.add_field(
                    name="Leave with",
                    value="`/stayafk leave`",
                    inline=True
                )
            else:
                embed.add_field(
                    name="Status",
                    value="🔴 **Disconnected/Temp Channel Deleted**",
                    inline=False
                )
                embed.add_field(
                    name="Action",
                    value="Try `/stayafk join` to rejoin\nor `/stayafk clearcache` to reset",
                    inline=False
                )
        else:
            embed.add_field(
                name="Status",
                value="🔴 **Not Connected**",
                inline=False
            )
            embed.add_field(
                name="Join with",
                value="`/stayafk join`",
                inline=False
            )
        
        embed.set_footer(text="💡 Temporary channels auto-delete when last person leaves")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @stayafk_group.command(name="clearcache", description="Clear bot voice cache (for troubleshooting)")
    async def clearcache(self, interaction: discord.Interaction):
        """Clear voice client cache and disconnect"""
        guild = interaction.guild
        
        try:
            # Kill any existing connection
            if guild.id in self.voice_clients:
                voice_client = self.voice_clients[guild.id]
                if voice_client and voice_client.is_connected():
                    try:
                        await voice_client.disconnect(force=True)
                    except Exception as e:
                        logger.debug(f"Disconnect error during cache clear: {e}")
            
            # Clear all tracking for this guild
            self.voice_clients.pop(guild.id, None)
            self.stay_afk_mode.pop(guild.id, None)
            self.alone_since.pop(guild.id, None)
            
            embed = discord.Embed(
                title="🧹 Cache Cleared",
                description="Bot voice cache has been cleared",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Next step",
                value="Use `/stayafk join` to reconnect",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            await interaction.response.send_message(
                f"❌ Error clearing cache: {str(e)}",
                ephemeral=True
            )
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state changes - track when bot disconnects or when members join/leave"""
        guild_id = member.guild.id
        
        if member.id == self.bot.user.id:
            # Bot voice state changed
            if before.channel and not after.channel:
                # Bot was disconnected
                logger.info(f"Bot disconnected from voice in {member.guild.name}")
                self.voice_clients.pop(guild_id, None)
                self.alone_since.pop(guild_id, None)
        else:
            # Another member's voice state changed - reset alone timer if bot is in voice
            if guild_id in self.voice_clients:
                voice_client = self.voice_clients[guild_id]
                if voice_client and voice_client.is_connected():
                    # Reset timer when user state changes (join/leave)
                    if guild_id in self.alone_since:
                        del self.alone_since[guild_id]

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(StayAFK(bot))
