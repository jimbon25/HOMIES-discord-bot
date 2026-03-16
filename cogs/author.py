import discord
from discord import app_commands
from discord.ext import commands
import os

class Author(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bot", description="Show bot and author information")
    async def show_bot_info(self, interaction: discord.Interaction):
        """Menampilkan informasi bot dan author dengan owner clickable."""
        embed = discord.Embed(
            title="Bot Information",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Bot Name",
            value=f"{self.bot.user.name}",
            inline=False
        )
        
        # Fetch owner dari OWNER_ID
        try:
            owner_id = int(os.getenv("OWNER_ID"))
            owner = await self.bot.fetch_user(owner_id)
            owner_mention = owner.mention
        except:
            owner_mention = "@nikdi99"
        
        embed.add_field(
            name="Author",
            value=owner_mention,
            inline=False
        )
        
        embed.add_field(
            name="📊 Total Servers",
            value="5,247+ servers",
            inline=False
        )
        
        embed.add_field(
            name="Community Server",
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
