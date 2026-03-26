"""Dice Roll Game - Guess the sum of 2 dice (2-12)"""
import discord
from discord.ext import commands
import random
import time
import logging

logger = logging.getLogger(__name__)


class DiceRollGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        
        # Payouts based on difficulty (inverse probability)
        # Lower chance = higher payout
        self.payouts = {
            2: 20.0,   # 1/36 = 2.8%
            3: 10.0,   # 2/36 = 5.6%
            4: 7.0,    # 3/36 = 8.3%
            5: 5.0,    # 4/36 = 11.1%
            6: 4.0,    # 5/36 = 13.9%
            7: 2.0,    # 6/36 = 16.7% (most common)
            8: 4.0,    # 5/36 = 13.9%
            9: 5.0,    # 4/36 = 11.1%
            10: 7.0,   # 3/36 = 8.3%
            11: 10.0,  # 2/36 = 5.6%
            12: 20.0,  # 1/36 = 2.8% (hardest)
        }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        coinflip_cog = self.bot.get_cog("CoinFlip")
        if not coinflip_cog:
            return

        current_prefix = coinflip_cog.get_guild_prefix(str(message.guild.id))
        content = message.content.lower().strip()
        user_id = str(message.author.id)

        # Command: <prefix>dice <guess> <amount> or <prefix>roll <guess> <amount>
        if not (content.startswith(f"{current_prefix}dice ") or content.startswith(f"{current_prefix}roll ")):
            return

        try:
            # Parse command
            parts = content.split()
            if len(parts) < 3:
                await message.channel.send(f"❌ Usage: `{current_prefix}dice <2-12> <amount>` or `all`")
                return

            # Get guess and amount
            try:
                guess = int(parts[1])
                amount_str = parts[2]
            except (ValueError, IndexError):
                await message.channel.send(f"❌ Usage: `{current_prefix}dice <2-12> <amount>`")
                return

            # Validate guess
            if guess < 2 or guess > 12:
                await message.channel.send("❌ Must guess between **2-12**")
                return

            # Get balance
            balance = coinflip_cog.get_user_balance(user_id)

            # Parse amount
            if amount_str.lower() == "all":
                amount = balance
            else:
                try:
                    amount = int(amount_str)
                except ValueError:
                    await message.channel.send(f"❌ Invalid amount")
                    return

            # Validate amount
            if amount <= 0:
                await message.channel.send("❌ Bet must be positive")
                return

            if amount > balance:
                await message.channel.send(f"❌ Insufficient balance! (Have: {balance:,})")
                return

            # Cooldown check (18 seconds)
            current_time = time.time()
            if user_id in self.cooldowns and current_time - self.cooldowns[user_id] < 18:
                remaining = int(18 - (current_time - self.cooldowns[user_id]))
                await message.channel.send(f"⏱️ {message.author.mention}, wait **{remaining}s** before next roll!", delete_after=5)
                return

            # Start game
            self.cooldowns[user_id] = current_time

            # Deduct bet
            coinflip_cog.update_balance(user_id, -amount)

            # Roll 2 dice
            die1 = random.randint(1, 6)
            die2 = random.randint(1, 6)
            total = die1 + die2

            # Create initial message
            msg = await message.channel.send(
                content=f"🎲 | **{message.author.name}** rolled the dice!\n"
                       f"Prediction: **{guess}** | Bet: 💶 **{amount:,}** MC\n"
                       f"Rolling... 🎲"
            )

            # Animate dice roll
            import asyncio
            for _ in range(6):
                await asyncio.sleep(0.3)
                d1 = random.randint(1, 6)
                d2 = random.randint(1, 6)
                await msg.edit(content=f"🎲 | **{message.author.name}** rolled the dice!\n"
                                      f"Prediction: **{guess}** | Bet: 💶 **{amount:,}** MC\n"
                                      f"Rolling... [{d1}] [{d2}]")

            # Show final result
            result_emoji = ""
            win = False
            
            if total == guess:
                # CORRECT GUESS - WIN!
                payout = self.payouts[guess]
                winnings = int(amount * payout)
                profit = winnings - amount
                result_emoji = "🎉"
                win = True
                result_text = f"🎯 **YOU WON!** Guessed correct! **{payout}x** multiplier!"
            else:
                # WRONG GUESS - LOSS
                winnings = 0
                profit = -amount
                result_emoji = "💔"
                result_text = f"❌ **YOU LOST!** Wrong number (got {total})"

            # Add EXP regardless
            exp_gain = random.randint(8, 20)
            leveling_cog = self.bot.get_cog("GameLeveling")
            level_msg = ""
            if leveling_cog:
                leveled, new_lvl, reward = leveling_cog.add_exp(user_id, exp_gain)
                if leveled:
                    level_msg = f"\n⭐ **LEVEL UP!** You're now Level **{new_lvl}** and got **{reward:,}** bonus!"

            # Update balance
            if win:
                coinflip_cog.update_balance(user_id, winnings)

            # Create result embed
            embed_color = discord.Color.green() if win else discord.Color.red()
            embed = discord.Embed(
                title=result_text,
                color=embed_color
            )

            embed.add_field(name="Prediction", value=f"**{guess}**", inline=True)
            embed.add_field(name="Result", value=f"**{die1}** + **{die2}** = **{total}**", inline=True)
            embed.add_field(name="Bet", value=f"**{amount:,}** 💶 MC", inline=True)

            if win:
                embed.add_field(name="Payout", value=f"**{self.payouts[guess]}x**", inline=True)
                embed.add_field(name="Winnings", value=f"**{winnings:,}** 💶 MC", inline=True)
                embed.add_field(name="Profit", value=f"**+{profit:,}** 💶", inline=True)
            else:
                embed.add_field(name="Winnings", value=f"**0** 💶 MC", inline=True)
                embed.add_field(name="Lost", value=f"**-{amount:,}** 💶", inline=True)

            embed.add_field(name="EXP Gained", value=f"**+{exp_gain}** EXP", inline=False)
            if level_msg:
                embed.description = level_msg


            await msg.edit(content=f"{result_emoji} | **{message.author.name}** rolled!", embed=embed)

        except Exception as e:
            logger.error(f"Dice roll error: {e}")
            await message.channel.send(f"❌ Error in dice roll: {str(e)}")


async def setup(bot):
    await bot.add_cog(DiceRollGame(bot))
    logger.info("✅ DiceRoll cog loaded")
