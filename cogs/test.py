import discord
from discord import app_commands
from discord.ext import commands

class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test", description="Test command")
    async def test(self, interaction: discord.Interaction):
        """Test command - bot merespons dengan miaw"""
        await interaction.response.send_message("miaw 🐱")

async def setup(bot):
    await bot.add_cog(Test(bot))
