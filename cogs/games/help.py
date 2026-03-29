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

        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            return

        current_prefix = economy_cog.get_guild_prefix(str(message.guild.id))
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
                    f"`{current_prefix}dice <2-12> <amount>` - Dice roll (guess sum of 2 dice)\n"
                    f"`{current_prefix}rps <amount>` - Rock Paper Scissors (vs Bot)\n"
                    f"`{current_prefix}mines <amount>` - Mines Game (Random bombs 2-15)\n"
                    f"`{current_prefix}tower <amount>` - Tower Game (Climb floors, avoid traps)\n"
                    f"`{current_prefix}work` - Work for 100-1000 cash (chance for rare mystery box)\n"
                    f"`{current_prefix}box` - See your mystery box stock\n"
                    f"`{current_prefix}box open` - Open a mystery box (if you have one)\n"
                    f"\nUse `all` instead of amount to bet all your cash"
                ),
                inline=False
            )

            # Earning Money section
            embed.add_field(
                name="Earn Money",
                value=(
                    f"`{current_prefix}cash` - Check your balance\n"
                    f"`{current_prefix}daily` - Daily 10k reward (Reset 15:00 WIB)\n"
                    f"`{current_prefix}work` - Earn 100-1000 (30s cooldown)\n"
                    f"`{current_prefix}pay @user <amount>` - Send money to user\n"
                    f"`{current_prefix}crypto` - View crypto market prices\n"
                    f"`{current_prefix}buy <coin> <amount>` - Buy crypto with MC\n"
                    f"`{current_prefix}sell <coin> <amount>` - Sell crypto for MC\n"
                    f"`{current_prefix}pf` - View your crypto portfolio\n"
                    f"`{current_prefix}bank` - View your bank balance & deposits\n"
                    f"`{current_prefix}dep <amount> [plan_id]` - Deposit money (Plan 1-3)\n"
                    f"`{current_prefix}wit <amount> [index]` - Withdraw money from bank"
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
                    "Dice Roll: 8-20 EXP per play (2x-20x payout based on guess)\n"
                    "Mystery Box: 12-28 EXP per open (rarity depends on box tier, 6 tiers available)\n"
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
