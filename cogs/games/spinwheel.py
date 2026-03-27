"""Spin the Wheel Game - Random multiplier with visual animation"""
import discord
from discord.ext import commands
import random
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class SpinWheelGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        
        # Wheel segments with multipliers - HARDER distribution
        self.wheel_segments = [
            # LOSS SEGMENTS (10 segments = 59%)
            0.0,   # LOSE ALL - RIP
            0.1,   # Lose 90%
            0.2,   # Lose 80%
            0.3,   # Lose 70%
            0.4,   # Lose 60%
            0.5,   # Lose 50%
            0.6,   # Lose 40%
            0.7,   # Lose 30%
            0.8,   # Lose 20%
            0.9,   # Lose 10%
            
            # BREAK EVEN (1 segment = 6%)
            1.0,   # Break even
            
            # WIN SEGMENTS (6 segments = 35%)
            1.2,   # Win 20%
            1.5,   # Win 50%
            2.0,   # Double
            3.0,   # Triple
            5.0,   # 5x
            10.0,  # 10x (Jackpot!)
        ]

    def get_multiplier_emoji(self, multiplier: float) -> str:
        """Get emoji based on multiplier"""
        if multiplier == 10.0:
            return "🎊"  # Jackpot
        elif multiplier >= 3.0:
            return "🟢"  # Great win
        elif multiplier >= 1.5:
            return "🟡"  # Good win
        elif multiplier >= 1.0:
            return "🟣"  # Break even / small win
        elif multiplier >= 0.5:
            return "🔵"  # Moderate loss
        elif multiplier > 0.0:
            return "🔴"  # Big loss
        else:
            return "💀"  # Lost everything!

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

        # Command: <prefix>spin <amount>
        if content.startswith(f"{current_prefix}spin "):
            # Cooldown check (22 seconds)
            current_time = time.time()
            if user_id in self.cooldowns and current_time - self.cooldowns[user_id] < 22:
                remaining = int(22 - (current_time - self.cooldowns[user_id]))
                await message.channel.send(f"⏱️ {message.author.mention}, wait **{remaining}s** before next spin!", delete_after=5)
                return

            try:
                # Parse amount
                amount_str = content[len(current_prefix) + 5:].strip()
                if not amount_str:
                    await message.channel.send(f"⚠️ Use: `{current_prefix}spin <amount>` or `{current_prefix}spin all`")
                    return

                if amount_str == "all":
                    amount = economy_cog.get_user_balance(user_id)
                else:
                    amount = int(amount_str)

                # Validate amount
                if amount <= 0:
                    await message.channel.send("❌ Bet must be > 0!")
                    return

                balance = economy_cog.get_user_balance(user_id)
                if amount > balance:
                    await message.channel.send(f"❌ Insufficient balance! (Have: {balance:,})")
                    return

                # Start game
                self.cooldowns[user_id] = current_time
                
                # Deduct bet
                economy_cog.update_balance(user_id, -amount)
                
                # Choose random multiplier
                multiplier = random.choice(self.wheel_segments)
                
                # Create initial message
                msg = await message.channel.send(
                    content=f"🎡 | **{message.author.name}** spun the wheel! Bet: 💶 **{amount:,}** Mahocoin\n"
                           f"Spinning... 🌀"
                )
                
                # Spinning animation (spinning wheel emoji)
                wheel_icons = ["🎡", "🌀", "💫", "✨", "🎪"]
                for _ in range(8):
                    await asyncio.sleep(0.4)
                    icon = random.choice(wheel_icons)
                    await msg.edit(content=f"{icon} | **{message.author.name}** spun the wheel! Bet: 💶 **{amount:,}** Mahocoin\n"
                                          f"Spinning... 🌀")
                
                # Show result
                emoji = self.get_multiplier_emoji(multiplier)
                
                # Calculate winnings
                winnings = int(amount * multiplier)
                profit = winnings - amount
                
                # Add EXP regardless of outcome
                exp_gain = random.randint(10, 25)
                leveling_cog = self.bot.get_cog("GameLeveling")
                level_msg = ""
                if leveling_cog:
                    leveled, new_lvl, reward = leveling_cog.add_exp(user_id, exp_gain)
                    if leveled:
                        level_msg = f"\n⭐ **LEVEL UP!** You're now Level **{new_lvl}** and got **{reward:,}** bonus!"
                
                # Determine result message
                if multiplier == 10.0:
                    # Jackpot!
                    result_msg = f"{emoji} | **JACKPOT 💶!!!** You hit the 10x multiplier!"
                    emoji_result = "🎊"
                elif multiplier > 1.0:
                    result_msg = f"{emoji} | **YOU WON 💶!** {multiplier}x multiplier!"
                    emoji_result = "✨"
                elif multiplier == 1.0:
                    result_msg = f"{emoji} | **BREAK EVEN!** Got your bet back."
                    emoji_result = "🤝"
                elif multiplier == 0.0:
                    result_msg = f"{emoji} | **LOST EVERYTHING!** You lost your entire bet!"
                    emoji_result = "💀"
                else:
                    loss_percent = int((1 - multiplier) * 100)
                    result_msg = f"{emoji} | **LOSS!** You lost {loss_percent}% of your bet ({multiplier}x)."
                    emoji_result = "💔"
                
                # Update balance with winnings
                economy_cog.update_balance(user_id, winnings)
                
                # Final embed
                if multiplier == 10.0:
                    embed_color = discord.Color.gold()
                elif multiplier > 1.0:
                    embed_color = discord.Color.green()
                elif multiplier == 1.0:
                    embed_color = discord.Color.orange()
                else:
                    embed_color = discord.Color.red()
                
                embed = discord.Embed(
                    title=result_msg,
                    color=embed_color
                )
                embed.add_field(name="Multiplier", value=f"**{multiplier}x**", inline=True)
                embed.add_field(name="Bet", value=f"**{amount:,}** 💶 MC", inline=True)
                embed.add_field(name="Winnings", value=f"**{winnings:,}** 💶 MC", inline=False)
                
                if profit > 0:
                    embed.add_field(name="Profit", value=f"+**{profit:,}** 💶 MC ✅", inline=False)
                elif profit < 0:
                    embed.add_field(name="Loss", value=f"-**{abs(profit):,}** 💶 MC ❌", inline=False)
                else:
                    embed.add_field(name="Result", value="**Break Even** 🤝", inline=False)
                
                embed.add_field(name="Experience", value=f"+**{exp_gain}** EXP{level_msg}", inline=False)
                
                await msg.edit(content=f"{emoji_result} | **{message.author.name}** - Spin Complete!", embed=embed)

            except ValueError:
                await message.channel.send(f"⚠️ Invalid amount! Use: `{current_prefix}spin 1000`")
            except Exception as e:
                logger.error(f"Spin wheel error: {type(e).__name__}: {e}")
                await message.channel.send(f"❌ Error: {str(e)[:100]}", delete_after=5)


async def setup(bot):
    await bot.add_cog(SpinWheelGame(bot))
    logger.info("✅ SpinWheel cog loaded")
