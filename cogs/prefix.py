"""Prefix Commands Management - Enable/Disable prefix commands per guild"""
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime
from pathlib import Path

class PrefixManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prefix_dir = "data/prefix"
        self.ensure_prefix_dir()
    
    def ensure_prefix_dir(self):
        """Ensure prefix data directory exists"""
        Path(self.prefix_dir).mkdir(parents=True, exist_ok=True)
    
    def get_prefix_file(self, guild_id: int) -> str:
        """Get prefix settings file path for guild"""
        return f"{self.prefix_dir}/prefix_settings_{guild_id}.json"
    
    def load_prefix_settings(self, guild_id: int) -> dict:
        """Load prefix settings for guild"""
        filepath = self.get_prefix_file(guild_id)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                return self.get_default_settings()
        return self.get_default_settings()
    
    def get_default_settings(self) -> dict:
        """Get default prefix settings"""
        return {
            "enabled": True,  # Default: prefix commands enabled
            "prefix_char": "?",
            "created_at": datetime.now().isoformat()
        }
    
    def save_prefix_settings(self, guild_id: int, settings: dict):
        """Save prefix settings for guild"""
        self.ensure_prefix_dir()
        filepath = self.get_prefix_file(guild_id)
        settings["last_updated"] = datetime.now().isoformat()
        with open(filepath, 'w') as f:
            json.dump(settings, f, indent=2)
    
    def is_prefix_enabled(self, guild_id: int) -> bool:
        """Check if prefix commands are enabled for guild"""
        settings = self.load_prefix_settings(guild_id)
        return settings.get("enabled", True)
    
    prefix_group = app_commands.Group(name="prefix", description="Manage prefix commands settings")
    
    @prefix_group.command(name="enable", description="Enable prefix commands on this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def prefix_enable(self, interaction: discord.Interaction):
        """Enable prefix commands"""
        guild_id = interaction.guild.id
        settings = self.load_prefix_settings(guild_id)
        settings["enabled"] = True
        self.save_prefix_settings(guild_id, settings)
        
        embed = discord.Embed(
            title="✅ Prefix Commands Enabled",
            description=f"Prefix commands are now **enabled** on this server\nPrefix character: `{settings['prefix_char']}`",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Example",
            value=f"`{settings['prefix_char']}afk I'm away`",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @prefix_group.command(name="disable", description="Disable prefix commands on this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def prefix_disable(self, interaction: discord.Interaction):
        """Disable prefix commands"""
        guild_id = interaction.guild.id
        settings = self.load_prefix_settings(guild_id)
        settings["enabled"] = False
        self.save_prefix_settings(guild_id, settings)
        
        embed = discord.Embed(
            title="❌ Prefix Commands Disabled",
            description="Prefix commands are now **disabled** on this server\nOnly slash commands (`/command`) will work",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Note",
            value="Use slash commands (`/help`) to see available commands",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @prefix_group.command(name="view", description="View current prefix settings")
    async def prefix_view(self, interaction: discord.Interaction):
        """View prefix settings"""
        guild_id = interaction.guild.id
        settings = self.load_prefix_settings(guild_id)
        
        status = "✅ **Enabled**" if settings["enabled"] else "❌ **Disabled**"
        
        embed = discord.Embed(
            title="Prefix Settings",
            description=f"Current prefix settings for {interaction.guild.name}",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Status",
            value=status,
            inline=False
        )
        embed.add_field(
            name="Prefix Character",
            value=f"`{settings['prefix_char']}`",
            inline=False
        )
        embed.add_field(
            name="Example Usage",
            value=f"`{settings['prefix_char']}afk Away for 30 mins`",
            inline=False
        )
        embed.add_field(
            name="Note",
            value="Slash commands (`/command`) always work regardless of prefix status",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @prefix_enable.error
    @prefix_disable.error
    async def prefix_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler for prefix commands"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Only administrators can manage prefix settings",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Error: {str(error)}",
                ephemeral=True
            )

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(PrefixManager(bot))
