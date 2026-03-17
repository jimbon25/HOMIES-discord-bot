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
        self.voice_clients = {}  # Track bot's voice connections
        self.stay_afk_mode = {}  # Track which channels are in stay_afk mode
        self.alone_since = {}  # Track when bot started being alone (guild_id -> datetime)
        self.alone_threshold = 60  # Auto-disconnect after 1 minute alone (60 seconds) - FOR TESTING, change to 600 for production
        logger.info("✅ StayAFK cog initialized - starting auto-disconnect checker")
        self.check_alone.start()  # Start background task
    
    @tasks.loop(minutes=1)
    async def check_alone(self):
        """Check if bot is alone in voice channel and auto-disconnect after timeout"""
        logger.info(f"🔄 Checking voice status: {len(self.voice_clients)} voice connections tracked")
        
        for guild_id in list(self.voice_clients.keys()):
            try:
                voice_client = self.voice_clients[guild_id]
                
                if not voice_client or not voice_client.is_connected():
                    # Cleanup if disconnected
                    if guild_id in self.alone_since:
                        del self.alone_since[guild_id]
                    logger.debug(f"Guild {guild_id}: voice_client not connected, skipping")
                    continue
                
                channel = voice_client.channel
                # Count members excluding the bot itself
                member_count = len([m for m in channel.members if not m.bot])
                
                logger.info(f"Guild {guild_id} - Channel {channel.name}: {member_count} human members, {len(channel.members)} total")
                
                if member_count == 0:
                    # Bot is alone
                    if guild_id not in self.alone_since:
                        # Just became alone
                        self.alone_since[guild_id] = datetime.now()
                        logger.info(f"⏰ Bot became alone in {channel.name}")
                    else:
                        # Check if alone for too long
                        alone_duration = (datetime.now() - self.alone_since[guild_id]).total_seconds()
                        logger.info(f"⏳ Bot alone for {alone_duration:.0f}s / threshold {self.alone_threshold}s in {channel.name}")
                        
                        if alone_duration >= self.alone_threshold:
                            # Auto-disconnect
                            try:
                                guild = self.bot.get_guild(guild_id)
                                logger.warning(f"⏱️ Timeout reached! Disconnecting bot from {channel.name}")
                                await voice_client.disconnect(force=True)
                                
                                # Cleanup tracking
                                if guild_id in self.voice_clients:
                                    del self.voice_clients[guild_id]
                                if guild_id in self.alone_since:
                                    del self.alone_since[guild_id]
                                if guild_id in self.stay_afk_mode:
                                    del self.stay_afk_mode[guild_id]
                                
                                logger.info(f"✅ Bot auto-disconnected from {channel.name} in {guild.name} (was alone for {alone_duration//60} minutes)")
                            except Exception as e:
                                logger.error(f"Error auto-disconnecting bot: {e}")
                else:
                    # Bot is not alone anymore - reset timer
                    if guild_id in self.alone_since:
                        del self.alone_since[guild_id]
                        logger.info(f"🔄 Reset alone timer for {channel.name} ({member_count} members present)")
                        del self.alone_since[guild_id]
            
            except Exception as e:
                logger.error(f"Error checking alone status for guild {guild_id}: {e}")
    
    @check_alone.before_loop
    async def before_check_alone(self):
        """Wait until bot is ready before starting check"""
        await self.bot.wait_until_ready()
        logger.info("✅ Auto-disconnect checker started - bot is ready")
    
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
            except Exception as deafen_error:
                logger.warning(f"Deafen error: {deafen_error}")
            
            embed = discord.Embed(
                title="🎤 Bot Joined Voice Channel",
                description=f"Bot is now AFK in {channel.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Channel", value=channel.name, inline=True)
            embed.add_field(name="Status", value="🟢 Stay AFK Mode (Deafened)", inline=True)
            embed.add_field(name="Stop with", value="`/stayafk leave`", inline=True)
            
            # Mark this guild as in stay_afk mode
            self.stay_afk_mode[guild.id] = True
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            # Cleanup on error
            if guild.id in self.voice_clients:
                del self.voice_clients[guild.id]
            
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
        
        try:
            voice_client = self.voice_clients[guild.id]
            
            if not voice_client or not voice_client.is_connected():
                # Remove from tracking even if already disconnected
                del self.voice_clients[guild.id]
                await interaction.response.send_message(
                    "❌ Bot is not connected to voice",
                    ephemeral=True
                )
                return
            
            try:
                channel_name = voice_client.channel.name
            except:
                channel_name = "Unknown Channel"
            
            # Disconnect bot
            try:
                await voice_client.disconnect(force=True)
            except Exception as disconnect_error:
                logger.warning(f"Disconnect error: {disconnect_error}")
            
            # Remove from tracking
            if guild.id in self.voice_clients:
                del self.voice_clients[guild.id]
            
            # Remove from stay_afk mode
            if guild.id in self.stay_afk_mode:
                del self.stay_afk_mode[guild.id]
            
            # Reset alone timer
            if guild.id in self.alone_since:
                del self.alone_since[guild.id]
            
            embed = discord.Embed(
                title="👋 Bot Left Voice Channel",
                description=f"Bot disconnected from **{channel_name}**",
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            # Cleanup on error
            if guild.id in self.voice_clients:
                try:
                    del self.voice_clients[guild.id]
                except:
                    pass
            
            if guild.id in self.stay_afk_mode:
                try:
                    del self.stay_afk_mode[guild.id]
                except:
                    pass
            
            # Reset alone timer
            if guild.id in self.alone_since:
                try:
                    del self.alone_since[guild.id]
                except:
                    pass
            
            logger.error(f"Leave command error: {e}")
            await interaction.response.send_message(
                f"✅ Bot has been disconnected from voice (error: {type(e).__name__})",
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
        """Clear voice client cache"""
        
        guild = interaction.guild
        
        try:
            # Kill any existing connection
            if guild.id in self.voice_clients:
                voice_client = self.voice_clients[guild.id]
                if voice_client and voice_client.is_connected():
                    try:
                        await voice_client.disconnect(force=True)
                    except:
                        pass
                del self.voice_clients[guild.id]
            
            # Clear stay_afk mode
            if guild.id in self.stay_afk_mode:
                del self.stay_afk_mode[guild.id]
            
            # Reset alone timer
            if guild.id in self.alone_since:
                del self.alone_since[guild.id]
            
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
            await interaction.response.send_message(
                f"❌ Error clearing cache: {str(e)}",
                ephemeral=True
            )
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle when bot gets disconnected or kicked"""
        if member.id == self.bot.user.id:
            # Bot disconnected
            if before.channel and not after.channel:
                guild = member.guild
                logger.info(f"Bot disconnected from voice in guild {guild.id}")
                
                # Only cleanup if not in stay_afk mode
                # (allow bot to reconnect if channel was temp deleted)
                if guild.id in self.voice_clients:
                    del self.voice_clients[guild.id]
                
                # Reset alone timer
                if guild.id in self.alone_since:
                    del self.alone_since[guild.id]
                
                # Keep stay_afk_mode flag so we can attempt reconnect if needed
                logger.debug(f"Cleaned up voice connection for guild {guild.id}")
        else:
            # Someone else joined/left - reset alone timer if bot is in voice
            guild = member.guild
            if guild.id in self.voice_clients:
                voice_client = self.voice_clients[guild.id]
                if voice_client and voice_client.is_connected():
                    # Reset alone timer since user state changed
                    if guild.id in self.alone_since:
                        del self.alone_since[guild.id]

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(StayAFK(bot))
