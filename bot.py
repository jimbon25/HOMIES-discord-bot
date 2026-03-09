import os
import discord
from discord import app_commands
from discord.ext import commands
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
                content_after_prefix = message.content[len(self.command_prefix):].split()[0].lower()
                
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
    
    # Set status teks di profile bot - Edit text dibawah:
    # Format: Playing, Listening, Watching, Streaming
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="W nikdi99 /help for commands"  # <- Edit text ini
        )
    )

@bot.tree.command(name="announce", description="Send announcement to a specific channel")
@app_commands.describe(message="Announcement message content", channel="Target channel for announcement", title="Announcement title (optional)", show_sender="Show sender name in footer (default: no)", role="Role to mention (optional)", format="Message format: embed or plain (default: embed)", text_size="Text size for plain format: normal, medium, large (default: normal)")
@app_commands.checks.has_permissions(administrator=True)
async def announce(interaction: discord.Interaction, message: str, channel: discord.TextChannel, title: str = "ANNOUNCEMENT", show_sender: bool = False, role: discord.Role = None, format: str = "embed", text_size: str = "normal"):
    """Send an announcement to a specific channel."""
    
    if format not in ["embed", "plain"]:
        await interaction.response.send_message(
            "❌ Invalid format. Use 'embed' or 'plain'",
            ephemeral=True
        )
        return
    
    if text_size not in ["normal", "medium", "large"]:
        await interaction.response.send_message(
            "❌ Invalid text size. Use 'normal', 'medium', or 'large'",
            ephemeral=True
        )
        return
    
    await interaction.response.send_message(f"Sending to {channel.mention}...", ephemeral=True)
    
    content = ""
    if role:
        # Debug logging for @everyone detection
        print(f"DEBUG: Role selected: {role.name}, ID: {role.id}, is_default: {role.is_default()}, guild.id: {interaction.guild.id}")
        
        # Special handling for @everyone role to prevent double mention
        # Check multiple ways to detect @everyone role
        is_everyone = role.is_default() or role.name == "@everyone" or role.id == interaction.guild.id
        
        print(f"DEBUG: is_everyone result: {is_everyone}")
        
        if is_everyone:
            # For @everyone, use plain text mention
            content = "@everyone "
        else:
            # For other roles, use proper mention format
            content = role.mention + " "
    
    if format == "embed":
        embed = discord.Embed(
            title=f"{title}",
            description=message,
            color=discord.Color.blue()
        )
        if show_sender:
            embed.set_footer(text=f"Sent by: {interaction.user.name}")
        
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
        
        await channel.send(content=content + plain_message)
    
    await interaction.edit_original_response(content=f"✅ Announcement successfully sent to {channel.mention}")

@announce.error
async def announce_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission (Admin) to use this command.", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
