import discord
from discord import app_commands
from discord.ext import commands

class Avatar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="View user's avatar")
    @app_commands.describe(user="User to view avatar")
    async def avatar(self, interaction: discord.Interaction, user: discord.User):
        """Menampilkan avatar user dalam embed"""
        embed = discord.Embed(
            title=f"Avatar {user.name}",
            color=discord.Color.blue()
        )
        
        # Set embed image ke avatar user
        embed.set_image(url=user.avatar.url)
        
        # Add field dengan link download
        embed.add_field(
            name="Link Avatar",
            value=f"[Download Avatar]({user.avatar.url})",
            inline=False
        )
        
        embed.set_footer(text=f"User ID: {user.id}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Avatar(bot))
