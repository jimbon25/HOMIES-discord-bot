import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
import logging
import json
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load token dari file .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class AnnouncerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="?", intents=intents)
        self.whitelist_user_ids = self._load_whitelist()

    def _load_whitelist(self):
        """Load whitelist user IDs from .env"""
        whitelist_str = os.getenv('WHITELIST_USER_IDS', '')
        if whitelist_str:
            try:
                return [int(uid.strip()) for uid in whitelist_str.split(',') if uid.strip()]
            except ValueError:
                logger.warning("Warning: Invalid WHITELIST_USER_IDS in .env")
                return []
        return []
    
    def is_user_whitelisted(self, user_id: int) -> bool:
        """Check if user is whitelisted for admin command access"""
        return user_id in self.whitelist_user_ids

    def get_prefix_file(self, guild_id: int) -> str:
        """Get prefix settings file path for guild"""
        return f"data/prefix/prefix_settings_{guild_id}.json"
    
    def is_prefix_enabled(self, guild_id: int) -> bool:
        """Check if prefix commands are enabled for guild"""
        if not guild_id:
            return True  # DMs always allow prefix
        
        filepath = self.get_prefix_file(guild_id)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    settings = json.load(f)
                    return settings.get("enabled", True)
            except:
                return True  # Default to enabled if error
        return True  # Default to enabled
    
    async def on_message(self, message: discord.Message):
        """Process messages and check prefix status + custom messages"""
        if message.author.bot:
            return
        
        # Check if message starts with prefix
        if message.content.startswith(self.command_prefix):
            if message.guild:
                # Check if prefix is enabled for guild
                if not self.is_prefix_enabled(message.guild.id):
                    # Prefix is disabled, ignore the message
                    return
                
                # Check for custom messages
                content_after_prefix = message.content[len(self.command_prefix):].strip()
                words = content_after_prefix.split()
                
                # Validate that there's at least a command
                if not words:
                    return
                    
                command = words[0].lower()
                
                # Get custom message cog
                custom_msg_cog = self.get_cog('CustomMessageManager')
                if custom_msg_cog:
                    custom_message = custom_msg_cog.get_custom_message(message.guild.id, content_after_prefix)
                    if custom_message:
                        # Send custom message as embed (no title, just description)
                        embed = discord.Embed(
                            description=custom_message,
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text=f"Triggered by: ?{content_after_prefix}")
                        try:
                            await message.channel.send(embed=embed)
                        except Exception as e:
                            logger.error(f"Error sending custom message: {e}")
                        return  # Don't process normal commands
        
        # Process commands normally
        await self.process_commands(message)

    @tasks.loop(seconds=300)  # Flush cache every 5 minutes
    async def flush_activity_cache(self):
        """Periodically flush activity tracker cache to disk"""
        try:
            from dashboard.tracker import activity_tracker
            await activity_tracker.flush_cache()
        except Exception as e:
            logger.error(f"Error flushing activity cache: {e}")
    
    @flush_activity_cache.before_loop
    async def before_flush(self):
        await self.wait_until_ready()

    async def setup_hook(self):
        # Critical cogs that must load
        critical_cogs = ['mute', 'voicechannel', 'dashboard', 'stayafk']
        loaded_cogs = []
        failed_cogs = []
        
        # Load cogs dari folder cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                cog_name = filename[:-3]
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f"✅ Loaded cog: {filename}")
                    loaded_cogs.append(cog_name)
                except Exception as e:
                    logger.error(f"❌ Failed to load cog {filename}: {type(e).__name__}: {e}")
                    failed_cogs.append(cog_name)
        
        # Load cogs dari subfolder (e.g., cogs/moderation/)
        for subfolder in os.listdir('./cogs'):
            subfolder_path = os.path.join('./cogs', subfolder)
            if os.path.isdir(subfolder_path) and not subfolder.startswith('__'):
                for filename in os.listdir(subfolder_path):
                    if filename.endswith('.py') and not filename.startswith('__'):
                        cog_name = filename[:-3]
                        try:
                            await self.load_extension(f'cogs.{subfolder}.{cog_name}')
                            logger.info(f"✅ Loaded cog: {subfolder}/{filename}")
                            loaded_cogs.append(cog_name)
                        except Exception as e:
                            logger.error(f"❌ Failed to load cog {subfolder}/{filename}: {type(e).__name__}: {e}")
                            failed_cogs.append(cog_name)
        
        # Check if critical cogs failed
        failed_critical = [cog for cog in critical_cogs if cog in failed_cogs]
        if failed_critical:
            logger.critical(f"⚠️ CRITICAL: Failed to load essential cogs: {', '.join(failed_critical)}")
        
        # Sinkronisasi slash commands ke global
        await self.tree.sync()
        logger.info(f"Synced slash commands for {self.user}")
        
        # Start periodic cache flush task
        if not self.flush_activity_cache.is_running():
            self.flush_activity_cache.start()

bot = AnnouncerBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    
    # Auto-leave dari guild tertentu saat restart (untuk testing/cleanup)
    autoleave_guild_id = os.getenv('AUTOLEAVE_GUILD_ID')
    if autoleave_guild_id:
        try:
            guild_id = int(autoleave_guild_id)
            guild = bot.get_guild(guild_id)
            if guild:
                await guild.leave()
                logger.info(f"✅ Bot auto-left guild: {guild.name} (ID: {guild_id})")
        except Exception as e:
            logger.error(f"❌ Error auto-leaving guild: {e}")
    
    # Set status teks di profile bot - Fetch owner name dari OWNER_ID
    # Format: Playing, Listening, Watching, Streaming
    try:
        owner_id = int(os.getenv("OWNER_ID"))
        owner = await bot.fetch_user(owner_id)
        owner_name = owner.name
    except:
        owner_name = "nikdi99"  # Fallback jika fetch gagal
    
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=f"Author: {owner_name} | /help"  # <- Owner name di-fetch otomatis
        )
    )

@bot.tree.command(name="announce", description="Send announcement to a specific channel")
@app_commands.describe(message="Announcement message content", channel="Target channel for announcement", title="Announcement title (optional)", show_sender="Show sender name in footer (default: no)", role="Role to mention (optional)", user="User to mention (optional)", format="Message format: embed or plain (default: embed)", text_size="Text size for plain format: normal, medium, large (default: normal)", image="Image file to attach to announcement (optional)")
async def announce(interaction: discord.Interaction, message: str, channel: discord.TextChannel, title: str = "", show_sender: bool = False, role: discord.Role = None, user: discord.User = None, format: str = "embed", text_size: str = "normal", image: discord.Attachment = None):
    """Send an announcement to a specific channel."""
    
    # Check permission: admin OR whitelisted user
    is_admin = interaction.user.guild_permissions.administrator
    is_whitelisted = interaction.client.is_user_whitelisted(interaction.user.id)
    
    if not (is_admin or is_whitelisted):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command. (Admin only)",
            ephemeral=True
        )
        return
    
    # Defer immediately to prevent timeout
    await interaction.response.defer(ephemeral=True)
    
    try:
        if format not in ["embed", "plain"]:
            await interaction.followup.send("❌ Invalid format. Use 'embed' or 'plain'", ephemeral=True)
            return
        
        if text_size not in ["normal", "medium", "large"]:
            await interaction.followup.send("❌ Invalid text size. Use 'normal', 'medium', or 'large'", ephemeral=True)
            return
        
        # Validate image if provided
        image_file = None
        if image:
            valid_formats = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
            if image.filename.lower().endswith(valid_formats):
                try:
                    # Download image data
                    image_data = await image.read()
                    image_file = await image.to_file()
                except Exception as e:
                    await interaction.followup.send(f"❌ Failed to download image: {str(e)}", ephemeral=True)
                    return
            else:
                await interaction.followup.send(
                    "❌ Invalid image format. Only PNG, JPG, GIF, and WebP are supported",
                    ephemeral=True
                )
                return
        
        content = ""
        if user:
            # Mention specific user
            content = user.mention + " "
        elif role:
            # Special handling for @everyone role to prevent double mention
            is_everyone = role.is_default() or role.name == "@everyone" or role.id == interaction.guild.id
            
            if is_everyone:
                # For @everyone, use plain text mention
                content = "@everyone "
            else:
                # For other roles, use proper mention format
                content = role.mention + " "
        
        if format == "embed":
            embed = discord.Embed(
                title=title if title else None,
                description=message,
                color=discord.Color.blue()
            )
            
            # Add image to embed if provided
            if image:
                embed.set_image(url=f"attachment://{image.filename}")
            
            if show_sender:
                embed.set_footer(text=f"Sent by: {interaction.user.name}")
            
            # Send with image file if any
            if image_file:
                await channel.send(content=content, embed=embed, file=image_file)
            else:
                await channel.send(content=content, embed=embed)
        else:  # plain format
            # Apply text size
            if text_size == "large":
                plain_message = f"# {message}"
            elif text_size == "medium":
                plain_message = f"## {message}"
            else:  # normal
                plain_message = message
            
            if show_sender:
                plain_message += f"\n\n*Sent by: {interaction.user.name}*"
            
            # Send with image file if any
            if image_file:
                await channel.send(content=content + plain_message, file=image_file)
            else:
                await channel.send(content=content + plain_message)
        
        # Send confirmation with image info
        confirm_msg = f"✅ Announcement successfully sent to {channel.mention}"
        if image:
            confirm_msg += f" with image"
        
        await interaction.followup.send(confirm_msg, ephemeral=True)
        
        # Log to modlog
        modlog_cog = bot.get_cog('ModerationLog')
        if modlog_cog:
            log_reason = f"Sent announcement to {channel.mention}: {message[:100]}"
            if role:
                log_reason += f" (with @{role.name})"
            if user:
                log_reason += f" (with @{user.name})"
            if image:
                log_reason += " (with image)"
            await modlog_cog.log_action(
                interaction.guild,
                "announce",
                interaction.user,
                interaction.user,
                log_reason
            )
    
    except discord.Forbidden:
        await interaction.followup.send("❌ Bot doesn't have permission to send messages in that channel", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Failed to send announcement: {str(e)}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)

@announce.error
async def announce_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission (Admin) to use this command.", ephemeral=True)

# Global error handler for all app commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for all slash commands"""
    
    # Skip if already responded
    if interaction.response.is_done():
        return
    
    error_msg = "❌ An error occurred while processing your command."
    
    # Handle specific error types
    if isinstance(error, app_commands.MissingPermissions):
        error_msg = "❌ You don't have permission to use this command."
    elif isinstance(error, app_commands.MissingRole):
        error_msg = "❌ You don't have the required role to use this command."
    elif isinstance(error, app_commands.BotMissingPermissions):
        error_msg = "❌ I don't have permission to perform this action."
    elif isinstance(error, app_commands.CommandOnCooldown):
        error_msg = f"⏱️ This command is on cooldown. Try again in {error.retry_after:.1f}s"
    elif isinstance(error, app_commands.NoPrivateMessage):
        error_msg = "❌ This command can only be used in servers, not in DMs."
    elif isinstance(error, app_commands.CheckFailure):
        error_msg = "❌ You don't meet the requirements to use this command."
    elif isinstance(error, discord.Forbidden):
        error_msg = "❌ I don't have permission to complete this action."
    elif isinstance(error, discord.NotFound):
        error_msg = "❌ The target was not found."
    
    try:
        await interaction.response.send_message(error_msg, ephemeral=True)
    except discord.InteractionResponded:
        try:
            await interaction.followup.send(error_msg, ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    
    # Log the error for debugging
    logger.error(f"App command error in {interaction.command.name}: {type(error).__name__}: {error}")

if __name__ == "__main__":
    bot.run(TOKEN)
