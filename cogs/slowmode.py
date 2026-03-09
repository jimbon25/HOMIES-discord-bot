import discord
from discord import app_commands
from discord.ext import commands

class SlowMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="slowmode", description="Set slowmode in channel")
    @app_commands.describe(channel="Channel to set slowmode in", seconds="Slowmode duration in seconds (0-21600)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, channel: discord.TextChannel, seconds: int):
        """Set slowmode di channel terpilih"""
        
        # Validate seconds
        if not 0 <= seconds <= 21600:
            await interaction.response.send_message(
                "❌ Durasi slowmode harus antara 0-21600 detik (6 jam)",
                ephemeral=True
            )
            return
        
        try:
            await channel.edit(slowmode_delay=seconds)
            
            if seconds == 0:
                embed = discord.Embed(
                    title="✅ Slowmode Disabled",
                    description=f"Slowmode di {channel.mention} sudah di-nonaktifkan",
                    color=discord.Color.green()
                )
            else:
                minutes = seconds // 60
                secs = seconds % 60
                time_str = f"{minutes}m {secs}s" if minutes > 0 else f"{secs}s"
                
                embed = discord.Embed(
                    title="✅ Slowmode Enabled",
                    description=f"Slowmode di {channel.mention} di-set ke **{time_str}**",
                    color=discord.Color.green()
                )
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(SlowMode(bot))
