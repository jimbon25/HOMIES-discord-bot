import discord
from discord.ext import commands, tasks
import logging
from datetime import datetime
import queue
import asyncio

# Create logger for this module
logger = logging.getLogger(__name__)

class DiscordLogHandler(logging.Handler):
    """Custom logging handler that sends logs to Discord via queue"""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        """Called by logging system when a message is logged"""
        try:
            msg = self.format(record)
            # Add to thread-safe queue
            self.log_queue.put(msg, block=False)
        except queue.Full:
            # Queue is full, skip this log
            pass
        except Exception as e:
            self.handleError(record)

class DiscordLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Create thread-safe queue for logs
        self.log_queue = queue.Queue(maxsize=100)
        self.discord_handler = DiscordLogHandler(self.log_queue)
        self.log_channel = None
        self.owner_guild = None
        self.setup_complete = False  # Flag to prevent duplicate setup
        # Don't start task yet - will start in on_ready
        self.send_logs_started = False
    
    @tasks.loop(seconds=3)
    async def send_logs(self):
        """Background task that sends accumulated logs to Discord"""
        if not self.log_channel:
            return
        
        batch = []
        try:
            # Collect logs from queue
            while len(batch) < 10:
                try:
                    msg = self.log_queue.get_nowait()
                    batch.append(msg)
                except queue.Empty:
                    break
            
            if batch:
                log_text = "\n".join(batch)
                print(f"[DEBUG] Sending {len(batch)} logs to Discord: {log_text[:100]}...")
                
                # Split if too long
                if len(log_text) > 1900:
                    parts = [log_text[i:i+1850] for i in range(0, len(log_text), 1850)]
                    for part in parts:
                        try:
                            await self.log_channel.send(f"```\n{part}\n```")
                        except Exception as e:
                            logger.error(f"Error sending log batch: {e}")
                        await asyncio.sleep(0.5)
                else:
                    try:
                        await self.log_channel.send(f"```\n{log_text}\n```")
                    except Exception as e:
                        logger.error(f"Error sending log: {e}")
        except Exception as e:
            logger.error(f"Error in send_logs task: {e}")
    
    @send_logs.before_loop
    async def before_send_logs(self):
        """Wait until bot is ready before starting send_logs task"""
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Setup logging when bot is ready"""
        # Use flag to prevent multiple setups
        if self.setup_complete:
            return
        
        try:
            logger.info("🔄 DiscordLogger: Starting setup...")
            
            # Get owner guild (bot owner's server)
            app_info = await self.bot.application_info()
            owner_id = app_info.owner.id
            
            # Find owner's server
            owner_guild = None
            for guild in self.bot.guilds:
                # Check if guild owner is the app owner
                if guild.owner_id == owner_id:
                    owner_guild = guild
                    break
            
            if not owner_guild:
                logger.warning("⚠️  DiscordLogger: Could not find owner guild. Logging disabled.")
                return
            
            self.owner_guild = owner_guild
            logger.info(f"✅ DiscordLogger: Owner guild found: {owner_guild.name} (ID: {owner_guild.id})")
            
            # Find existing #bot-logs channel - case insensitive search
            log_channel = None
            for channel in owner_guild.text_channels:
                if channel.name.lower() == "bot-logs":
                    log_channel = channel
                    logger.info(f"✅ DiscordLogger: Found existing #bot-logs channel (ID: {channel.id})")
                    break
            
            if not log_channel:
                # Create the channel only if it doesn't exist
                try:
                    log_channel = await owner_guild.create_text_channel(
                        name="bot-logs",
                        topic="Live bot logs and events",
                        reason="Discord logging system initialization"
                    )
                    logger.info(f"✅ DiscordLogger: Created new #bot-logs channel (ID: {log_channel.id})")
                except Exception as e:
                    logger.error(f"❌ DiscordLogger: Failed to create #bot-logs channel: {e}")
                    return
            
            self.log_channel = log_channel
            
            # Add handler to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(self.discord_handler)
            
            # Setup formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            self.discord_handler.setFormatter(formatter)
            self.discord_handler.setLevel(logging.INFO)
            
            # Start the send_logs task if not already started
            if not self.send_logs_started:
                self.send_logs.start()
                self.send_logs_started = True
            
            # Mark setup as complete
            self.setup_complete = True
            
            logger.info(f"✅ DiscordLogger: Logging active in #{log_channel.name}")
            
            # Send startup message
            embed = discord.Embed(
                title="🤖 Bot Logging Started",
                description=f"Logging system initialized at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.green()
            )
            embed.add_field(name="Guild", value=owner_guild.name, inline=True)
            embed.add_field(name="Channel", value=f"#{log_channel.name}", inline=True)
            embed.add_field(name="Status", value="✅ Live logging active", inline=False)
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ DiscordLogger: Error in on_ready setup: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Test log message to verify system is working
            logger.info("🧪 DISCORD LOGGER TEST: System verification log sent to #bot-logs")
            
        except Exception as e:
            logger.error(f"❌ Error setting up Discord logging: {type(e).__name__}: {e}")

async def setup(bot):
    await bot.add_cog(DiscordLogger(bot))
    logger.info("✅ DiscordLogger cog loaded")
