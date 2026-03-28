"""Cash Check Command"""
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class Cash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            return

        current_prefix = economy_cog.get_guild_prefix(str(message.guild.id))
        content = message.content.lower().strip()
        user_id = str(message.author.id)

        # Handle cash check command
        if content == f"{current_prefix}cash":
            balance = economy_cog.get_user_balance(user_id)
            embed = discord.Embed(
                title="Wallet",
                description=f"💶 | **{message.author.display_name}**, you currently have **{balance:,}** Mahocoin!",
                color=discord.Color.gold()
            )
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Cash(bot))
    logger.info("✅ Cash cog loaded")
