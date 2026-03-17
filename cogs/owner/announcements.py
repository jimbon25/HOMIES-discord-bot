"""Global Announcements - Send announcements to all servers"""
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from pathlib import Path
from datetime import datetime

class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "data/announce_channels.json"
        self.load_config()
    
    def load_config(self):
        """Load announcement channel configuration"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.announce_channels = json.load(f)
        else:
            self.announce_channels = {}
    
    def save_config(self):
        """Save announcement channel configuration"""
        Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.announce_channels, f, indent=2)
    
    def get_announce_channel(self, guild_id: int) -> int:
        """Get announcement channel ID for guild"""
        return self.announce_channels.get(str(guild_id))
    
    @app_commands.command(name="setannouncechannel", description="Set announcement channel for this server")
    @app_commands.describe(channel="Channel where announcements will be sent")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_announce_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set announcement channel"""
        
        guild_id = str(interaction.guild.id)
        self.announce_channels[guild_id] = channel.id
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Announcement Channel Set",
            description=f"Announcements will now be sent to {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="broadcastannounce", description="Send global announcement to all servers")
    @app_commands.describe(message="Announcement message")
    async def broadcast_announce(self, interaction: discord.Interaction, message: str):
        """Send global announcement"""
        
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
        
        # Send to all guilds
        for guild in self.bot.guilds:
            try:
                channel_id = self.get_announce_channel(guild.id)
                
                # Only send if channel configured for this guild
                if not channel_id:
                    continue
                
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except:
                    failed_count += 1
                    continue
                
                # Create announcement embed
                embed = discord.Embed(
                    title="📢 ANNOUNCEMENT",
                    description=message,
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                
                # Add server info
                member_count = guild.member_count or 0
                embed.add_field(
                    name="Server",
                    value=guild.name,
                    inline=True
                )
                embed.add_field(
                    name="Members",
                    value=f"{member_count}",
                    inline=True
                )
                
                embed.set_footer(text=f"From Bot Owner • Server: {guild.name}")
                
                await channel.send(embed=embed)
                sent_count += 1
            
            except Exception as e:
                print(f"Error sending announcement to {guild.name}: {e}")
                failed_count += 1
        
        # Send summary
        summary = discord.Embed(
            title="📨 Announcement Sent",
            description=f"Announcement dispatched to servers",
            color=discord.Color.green()
        )
        summary.add_field(name="✅ Sent", value=sent_count, inline=True)
        summary.add_field(name="❌ Failed", value=failed_count, inline=True)
        summary.add_field(name="⏭️ Skipped", value=len(self.bot.guilds) - sent_count - failed_count, inline=True)
        
        await interaction.followup.send(embed=summary, ephemeral=True)

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(Announcements(bot))
