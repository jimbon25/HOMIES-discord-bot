"""Games Help System - Show available games and commands"""
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)


class GamesHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        coinflip_cog = self.bot.get_cog("CoinFlip")
        if not coinflip_cog:
            return

        current_prefix = coinflip_cog.get_guild_prefix(str(message.guild.id))
        content = message.content.lower().strip()

        # Command: <prefix>help
        if content == f"{current_prefix}help":
            embed = discord.Embed(
                title="Games & Economy Commands",
                description="Complete guide to all available commands",
                color=discord.Color.blurple()
            )

            # Games section
            embed.add_field(
                name="Games",
                value=(
                    f"`{current_prefix}cf <amount>` - Coin flip (50/50 chance, x2 if win)\n"
                    f"`{current_prefix}s <amount>` - Slots (triple match for x3-7 payout)\n"
                    f"`{current_prefix}bj <amount>` - Blackjack (hit/stand vs dealer)\n"
                    f"`{current_prefix}spin <amount>` - Spin the wheel (0.0x-10x multiplier, HIGH RISK)\n"
                    f"\nUse `all` instead of amount to bet all your cash"
                ),
                inline=False
            )

            # Earning Money section
            embed.add_field(
                name="Earn Money",
                value=(
                    f"`{current_prefix}cash` - Check your balance\n"
                    f"`{current_prefix}daily` - Daily 10k reward (24h cooldown)\n"
                    f"`{current_prefix}work` - Earn 100-1000 (30s cooldown)\n"
                    f"`{current_prefix}pay @user <amount>` - Send money to user"
                ),
                inline=False
            )

            # Leveling section
            embed.add_field(
                name="Leveling",
                value=(
                    f"`{current_prefix}level` or `{current_prefix}xp` - Check your level & EXP\n"
                    f"Gain EXP by playing games\n"
                    f"Level up = bonus reward!\n"
                ),
                inline=False
            )

            # Leaderboard section
            embed.add_field(
                name="Leaderboard",
                value=(
                    f"`{current_prefix}leaderboard` or `{current_prefix}lb` - View global top players\n"
                    f"Sorted by current balance\n"
                ),
                inline=False
            )

            # Details section
            embed.add_field(
                name="Game Details",
                value=(
                    "Coin Flip: 10-30 EXP per play\n"
                    "Slots: 30-60 EXP per play\n"
                    "Blackjack: 15-40 EXP per play\n"
                    "Spin Wheel: 10-25 EXP per play (59% loss, 6% break even, 35% win)\n"
                    "Each game has cooldown"
                ),
                inline=False
            )

            # Admin section
            embed.add_field(
                name="Admin",
                value=f"`mahoraga prefix <char>` - Change prefix (default: `{current_prefix}`)",
                inline=False
            )

            embed.set_footer(text=f"Current Prefix: {current_prefix}")

            await message.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GamesHelp(bot))
    logger.info("✅ GamesHelp cog loaded")
