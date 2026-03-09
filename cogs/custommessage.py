"""Custom Message Management - Create custom prefix commands"""
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
import json
import os
from datetime import datetime
from pathlib import Path

class CustomMessageModal(Modal, title="Create Custom Message"):
    """Modal for creating custom messages"""
    
    trigger = TextInput(
        label="Prefix Trigger",
        placeholder="Example: guide, rules, faq",
        required=True,
        max_length=50
    )
    
    message_content = TextInput(
        label="Message Content",
        placeholder="Enter your custom message here",
        required=True,
        max_length=2000,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            trigger = self.trigger.value.lower().strip()
            message_content = self.message_content.value.strip()
            
            # Validate trigger (alphanumeric only)
            if not trigger.isalnum():
                await interaction.response.send_message(
                    "❌ Trigger must be alphanumeric only (no spaces or special characters)",
                    ephemeral=True
                )
                return
            
            # Save custom message
            self.cog.save_custom_message(
                interaction.guild.id,
                trigger,
                message_content,
                interaction.user.id
            )
            
            embed = discord.Embed(
                title="✅ Custom Message Created",
                description=f"Successfully created custom prefix command: `?{trigger}`",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Preview",
                value=message_content[:500],  # Show first 500 chars
                inline=False
            )
            embed.add_field(
                name="Usage",
                value=f"Type `?{trigger}` to trigger this message",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error creating custom message: {str(e)}",
                ephemeral=True
            )


class CustomMessageManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.custom_msg_dir = "data/custom_messages"
        self.ensure_dir()
    
    def ensure_dir(self):
        """Ensure custom messages directory exists"""
        Path(self.custom_msg_dir).mkdir(parents=True, exist_ok=True)
    
    def get_custom_message_file(self, guild_id: int) -> str:
        """Get custom messages file path for guild"""
        return f"{self.custom_msg_dir}/custom_messages_{guild_id}.json"
    
    def load_custom_messages(self, guild_id: int) -> dict:
        """Load custom messages for guild"""
        filepath = self.get_custom_message_file(guild_id)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_custom_messages(self, guild_id: int, messages: dict):
        """Save custom messages for guild"""
        self.ensure_dir()
        filepath = self.get_custom_message_file(guild_id)
        with open(filepath, 'w') as f:
            json.dump(messages, f, indent=2)
    
    def save_custom_message(self, guild_id: int, trigger: str, message: str, user_id: int):
        """Save single custom message"""
        messages = self.load_custom_messages(guild_id)
        messages[trigger] = {
            "message": message,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
            "created_by": user_id
        }
        self.save_custom_messages(guild_id, messages)
    
    def get_custom_message(self, guild_id: int, trigger: str):
        """Get custom message if exists and enabled"""
        messages = self.load_custom_messages(guild_id)
        if trigger in messages:
            msg_data = messages[trigger]
            if msg_data.get("enabled", True):
                return msg_data.get("message")
        return None
    
    custommessage_group = app_commands.Group(
        name="custommessage",
        description="Manage custom prefix commands"
    )
    
    @custommessage_group.command(name="create", description="Create a custom prefix command")
    @app_commands.checks.has_permissions(administrator=True)
    async def custommessage_create(self, interaction: discord.Interaction):
        """Open modal to create custom message"""
        try:
            modal = CustomMessageModal(self)
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error opening modal: {str(e)}",
                ephemeral=True
            )
    
    @custommessage_group.command(name="list", description="List all custom prefix commands")
    async def custommessage_list(self, interaction: discord.Interaction):
        """List all custom messages"""
        messages = self.load_custom_messages(interaction.guild.id)
        
        if not messages:
            await interaction.response.send_message(
                "❌ No custom messages created yet",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="Custom Prefix Commands",
            description=f"Total: {len(messages)} custom command(s)",
            color=discord.Color.blue()
        )
        
        for trigger, data in messages.items():
            status = "✅ Enabled" if data.get("enabled", True) else "❌ Disabled"
            preview = data.get("message", "")[:100]
            embed.add_field(
                name=f"?{trigger}",
                value=f"{status}\n*{preview}...*",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @custommessage_group.command(name="delete", description="Delete a custom prefix command")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(trigger="Prefix trigger to delete (without ?)")
    async def custommessage_delete(self, interaction: discord.Interaction, trigger: str):
        """Delete custom message"""
        trigger = trigger.lower().strip()
        messages = self.load_custom_messages(interaction.guild.id)
        
        if trigger not in messages:
            await interaction.response.send_message(
                f"❌ Custom message `?{trigger}` not found",
                ephemeral=True
            )
            return
        
        del messages[trigger]
        self.save_custom_messages(interaction.guild.id, messages)
        
        await interaction.response.send_message(
            f"✅ Deleted custom message `?{trigger}`",
            ephemeral=True
        )
    
    @custommessage_group.command(name="disable", description="Disable a custom prefix command")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(trigger="Prefix trigger to disable (without ?)")
    async def custommessage_disable(self, interaction: discord.Interaction, trigger: str):
        """Disable custom message"""
        trigger = trigger.lower().strip()
        messages = self.load_custom_messages(interaction.guild.id)
        
        if trigger not in messages:
            await interaction.response.send_message(
                f"❌ Custom message `?{trigger}` not found",
                ephemeral=True
            )
            return
        
        messages[trigger]["enabled"] = False
        self.save_custom_messages(interaction.guild.id, messages)
        
        await interaction.response.send_message(
            f"✅ Disabled custom message `?{trigger}`",
            ephemeral=True
        )
    
    @custommessage_group.command(name="enable", description="Enable a custom prefix command")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(trigger="Prefix trigger to enable (without ?)")
    async def custommessage_enable(self, interaction: discord.Interaction, trigger: str):
        """Enable custom message"""
        trigger = trigger.lower().strip()
        messages = self.load_custom_messages(interaction.guild.id)
        
        if trigger not in messages:
            await interaction.response.send_message(
                f"❌ Custom message `?{trigger}` not found",
                ephemeral=True
            )
            return
        
        messages[trigger]["enabled"] = True
        self.save_custom_messages(interaction.guild.id, messages)
        
        await interaction.response.send_message(
            f"✅ Enabled custom message `?{trigger}`",
            ephemeral=True
        )
    
    @custommessage_create.error
    @custommessage_delete.error
    @custommessage_disable.error
    @custommessage_enable.error
    async def custommessage_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler"""
        try:
            if isinstance(error, app_commands.MissingPermissions):
                await interaction.response.send_message(
                    "❌ Only administrators can manage custom messages",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ Error: {str(error)}",
                    ephemeral=True
                )
        except discord.errors.NotFound:
            # Interaction expired/invalid, silently ignore
            pass
        except Exception as e:
            # Log other unexpected errors
            import logging
            logging.error(f"Error in custommessage_error handler: {e}")

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(CustomMessageManager(bot))
