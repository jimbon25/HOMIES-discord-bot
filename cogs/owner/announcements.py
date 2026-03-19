"""Global Announcements - Send announcements to all servers"""
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import json
import os
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional
from utils import safe_save_json

logger = logging.getLogger(__name__)

class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "data/announce_channels.json"
        self.settings_file = "data/announce_settings.json"
        self.member_count = "2,785"  # Default fallback
        self.load_config()
        self.load_settings()
    
    def load_config(self):
        """Load announcement channel configuration"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.announce_channels = json.load(f)
        else:
            self.announce_channels = {}
    
    def load_settings(self):
        """Load announcement settings (member count, etc)"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.member_count = settings.get("member_count", "2,785")
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
                self.member_count = "2,785"
        else:
            self.member_count = "2,785"
    
    def save_config(self):
        """Save announcement channel configuration"""
        safe_save_json(self.announce_channels, self.config_file)
    
    def get_announce_channel(self, guild_id: int) -> int:
        """Get announcement channel ID for guild"""
        return self.announce_channels.get(str(guild_id))
    
    @app_commands.command(name="getupdates", description="Set channel to receive bot update announcements")
    @app_commands.describe(channel="Channel where bot updates will be sent")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_updates_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Configure channel for bot updates"""
        
        guild_id = str(interaction.guild.id)
        self.announce_channels[guild_id] = channel.id
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Updates Channel Configured",
            description=f"Bot updates will now be sent to {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="broadcastannounce", description="Send global announcement to all servers")
    @app_commands.describe(
        message="Announcement message",
        test="Test mode - only send to current server (yes/no)",
        mention="Mention @everyone or @here (none/everyone/here)",
        title="Custom title for announcement (optional)",
        image="Image file to attach to announcement (optional)"
    )
    async def broadcast_announce(self, interaction: discord.Interaction, message: str, test: str = "no", mention: str = "none", title: str = "", image: Optional[discord.Attachment] = None):
        """Send global announcement"""
        
        # Convert escaped newlines to actual newlines
        message = message.replace('\\n', '\n')
        
        # Validate image if provided
        if image:
            valid_formats = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
            if image.filename.lower().endswith(valid_formats):
                try:
                    # Download image data
                    image_data = await image.read()
                except Exception as e:
                    embed = discord.Embed(
                        title="❌ Error",
                        description=f"Failed to download image: {str(e)}",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
            else:
                embed = discord.Embed(
                    title="❌ Invalid Image Format",
                    description="Only PNG, JPG, GIF, and WebP are supported",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        # Check if user is owner
        owner_id = int(os.getenv('OWNER_ID'))
        additional_owners = os.getenv('ADDITIONAL_OWNER_IDS', '').split(',')
        additional_owners = [int(oid.strip()) for oid in additional_owners if oid.strip()]
        
        if interaction.user.id != owner_id and interaction.user.id not in additional_owners:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only bot owner can use this command!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Defer response (might take time)
        await interaction.response.defer(ephemeral=True)
        
        sent_count = 0
        failed_count = 0
        skipped_count = 0
        error_details = []
        is_test = test.lower() in ["yes", "true", "1"]
        
        # Determine which guilds to send to
        target_guilds = [interaction.guild] if is_test else self.bot.guilds
        
        # Send to all guilds
        for guild in target_guilds:
            channel_id = self.get_announce_channel(guild.id)
            
            # Only send if channel configured for this guild
            if not channel_id:
                skipped_count += 1
                continue
            
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception as e:
                error_msg = f"Channel {channel_id} fetch failed: {e}"
                logger.error(error_msg)
                error_details.append(error_msg)
                failed_count += 1
                continue
            
            try:
                # Create announcement embed
                embed_title = title if title else "📢"
                embed = discord.Embed(
                    title=embed_title,
                    description=message,
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                
                # Add image to embed if provided
                if image:
                    embed.set_image(url=f"attachment://{image.filename}")
                
                # Load current member count from settings
                self.load_settings()
                
                embed.add_field(
                    name="Server",
                    value=f"Homies Hub | Members {self.member_count}",
                    inline=True
                )
                
                # Add community server link (removed - will use button instead)
                embed.set_footer(text="Announcements")
                
                # Create button for community server join
                view = View()
                join_button = Button(
                    label="Join Community Server",
                    url="https://discord.gg/C5xz4RZ7",
                    style=discord.ButtonStyle.primary
                )
                view.add_item(join_button)
                
                # Prepare mention text
                mention_text = ""
                if mention.lower() in ["everyone", "@everyone"]:
                    mention_text = "@everyone\n"
                elif mention.lower() in ["here", "@here"]:
                    mention_text = "@here\n"
                
                # Prepare file if image provided
                if image:
                    file = await image.to_file()
                    await channel.send(content=mention_text, embed=embed, view=view, file=file, allowed_mentions=discord.AllowedMentions(everyone=True))
                else:
                    await channel.send(content=mention_text, embed=embed, view=view, allowed_mentions=discord.AllowedMentions(everyone=True))
                sent_count += 1
                
            except Exception as e:
                error_msg = f"{guild.name}: {str(e)}"
                logger.error(f"Error sending announcement to {error_msg}")
                error_details.append(error_msg)
                failed_count += 1
        
        # Send summary
        summary_title = "📨 Test Announcement" if is_test else "📨 Global Announcement Sent"
        summary_desc = "Announcement tested in this server" if is_test else "Announcement dispatched to all configured servers"
        
        summary = discord.Embed(
            title=summary_title,
            description=summary_desc,
            color=discord.Color.gold() if is_test else discord.Color.green()
        )
        summary.add_field(name="✅ Sent", value=sent_count, inline=True)
        summary.add_field(name="❌ Failed", value=failed_count, inline=True)
        summary.add_field(name="⏭️ Skipped", value=skipped_count, inline=True)
        
        # Show mention setting
        mention_display = "none"
        if mention.lower() in ["everyone", "@everyone"]:
            mention_display = "@everyone"
        elif mention.lower() in ["here", "@here"]:
            mention_display = "@here"
        summary.add_field(name="📢 Mention", value=mention_display, inline=True)
        
        # Show image info if attached
        if image:
            summary.add_field(name="🖼️ Image", value=f"✅ {image.filename}", inline=True)
        
        # Add error details if any
        if error_details:
            error_text = "\n".join(error_details[:5])  # Show first 5 errors
            if len(error_details) > 5:
                error_text += f"\n... and {len(error_details) - 5} more"
            summary.add_field(
                name="🔴 Error Details",
                value=f"```\n{error_text}\n```",
                inline=False
            )
        
        if is_test and sent_count == 0 and skipped_count > 0:
            summary.add_field(
                name="⚠️ Note",
                value=f"This server is not configured for announcements. Use `/getupdates #channel` to enable it first.",
                inline=False
            )
        
        if is_test:
            summary.add_field(
                name="Test Mode",
                value="✅ Testing completed. Use `/broadcastannounce message no` to broadcast globally",
                inline=False
            )
        
        await interaction.followup.send(embed=summary, ephemeral=True)

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(Announcements(bot))
