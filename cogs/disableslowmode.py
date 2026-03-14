import discord
from discord import app_commands
from discord.ext import commands

class DisableSlowmode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="disableslowmode", description="Disable slowmode in channel")
    @app_commands.describe(channel="Channel to disable slowmode in")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def disableslowmode(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Disable slowmode in a channel"""
        
        try:
            await channel.edit(slowmode_delay=0)
            
            embed = discord.Embed(
                title="✅ Slowmode Disabled",
                description=f"Slowmode in {channel.mention} has been disabled",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(DisableSlowmode(bot))
