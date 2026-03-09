import discord
from discord import app_commands
from discord.ext import commands

class Author(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="author", description="Show bot and author information")
    async def author_info(self, interaction: discord.Interaction):
        """Menampilkan informasi bot dan author."""
        embed = discord.Embed(
            title="Bot Information",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Bot Name",
            value=f"{self.bot.user.name}",
            inline=False
        )
        
        embed.add_field(
            name="Author",
            value="@nikdi99",
            inline=False
        )
        
        embed.add_field(
            name="Community Server (BACKUP)",
            value="[Join Server](https://discord.gg/C5xz4RZ7)",
            inline=False
        )
        
        embed.add_field(
            name="Social Media",
            value="[Facebook](https://facebook.com/iv.dimas) | [Instagram](https://instagram.com/dimasladty)",
            inline=False
        )
        
        embed.set_footer(text=f"Bot ID: {self.bot.user.id}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Author(bot))
