"""Hidden Bot Restart - Disguised as hi command"""
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


async def is_owner_check(interaction: discord.Interaction) -> bool:
    """Check if user is bot owner"""
    try:
        app_info = await interaction.client.application_info()
        is_owner = interaction.user.id == app_info.owner.id
        
        if not is_owner:
            await interaction.response.send_message(
                "❌ You don't have permission to use this",
                ephemeral=True
            )
        
        return is_owner
    except Exception as e:
        logger.error(f"Error checking owner: {e}")
        return False


class RestartConfirmationView(View):
    """Confirmation buttons for restart"""
    
    def __init__(self, owner_id: int):
        super().__init__(timeout=30)
        self.owner_id = owner_id
    
    @discord.ui.button(label="✅ Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: discord.Interaction, button: Button):
        """Confirm action"""
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Only the command issuer can confirm",
                ephemeral=True
            )
            return
        
        for child in self.children:
            child.disabled = True
        
        # Show processing embed
        embed = discord.Embed(
            title="⏳ Processing...",
            description="System update in progress.",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        logger.warning(f"🔄 Bot maintenance initiated by {interaction.user.name} ({interaction.user.id})")
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Edit message to complete
        complete_embed = discord.Embed(
            title="✅ Complete",
            description="System update completed successfully.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        
        await interaction.edit_original_response(embed=complete_embed, view=self)
        
        # Small delay before closing
        await asyncio.sleep(0.5)
        await interaction.client.close()
    
    @discord.ui.button(label="❌ No", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        """Cancel action"""
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Only the command issuer can confirm",
                ephemeral=True
            )
            return
        
        for child in self.children:
            child.disabled = True
        
        embed = discord.Embed(
            title="❌ Cancelled",
            description="Action cancelled.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        logger.info(f"Action cancelled by {interaction.user.name} ({interaction.user.id})")


class HiBot(commands.Cog):
    """Hi bot system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="hibot", description="Hi bot!")
    @app_commands.check(is_owner_check)
    async def hi_bot(self, interaction: discord.Interaction):
        """Say hi to bot"""
        
        embed = discord.Embed(
            title="👋 Hi!",
            description="Perform system update?",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="User", value=f"{interaction.user.mention}", inline=False)
        embed.add_field(name="Timeout", value="30 seconds", inline=False)
        
        view = RestartConfirmationView(owner_id=interaction.user.id)
        
        await interaction.response.send_message(embed=embed, view=view)
        
        logger.info(f"Hi bot command from {interaction.user.name}")


async def setup(bot):
    """Setup cog"""
    await bot.add_cog(HiBot(bot))
    logger.info("✅ HiBot cog loaded")
