"""Slots Game - Prefix-based game with random multipliers and EXP"""
import discord
from discord.ext import commands
import random
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Reduced to 3 symbols for much better winning probability (~11%)
        self.symbols = ["🍒", "💎", "7️⃣"]
        self.cooldowns = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog: return

        current_prefix = economy_cog.get_guild_prefix(str(message.guild.id))
        content = message.content.lower().strip()
        user_id = str(message.author.id)

        # Command: <prefix>s <amount>
        if content.startswith(f"{current_prefix}s "):
            # Cooldown 25s for slots
            current_time = time.time()
            if user_id in self.cooldowns and current_time - self.cooldowns[user_id] < 25:
                remaining = int(25 - (current_time - self.cooldowns[user_id]))
                await message.channel.send(f"⏱️ {message.author.mention}, slot machine is hot! Wait **{remaining}s**.", delete_after=5)
                return

            try:
                amount_str = content[len(current_prefix) + 2:].strip()
                if amount_str == "all":
                    amount = economy_cog.get_user_balance(user_id)
                else:
                    amount = int(amount_str)

                if amount <= 0:
                    await message.channel.send("❌ Amount must be greater than 0!")
                    return

                balance = economy_cog.get_user_balance(user_id)
                if amount > balance:
                    await message.channel.send(f"❌ Insufficient cash! (Balance: {balance:,})")
                    return

                self.cooldowns[user_id] = current_time
                
                # Deduct money
                economy_cog.update_balance(user_id, -amount)

                # 1. Determine final roll at the start for consistency
                final_roll = [random.choice(self.symbols) for _ in range(3)]

                # 2. Animation (Realistic Rolling)
                msg = await message.channel.send(f"🎰 | **{message.author.name}** Spent **{amount:,}**... (slots)\n[ ❓ | ❓ | ❓ ]")

                import asyncio
                for i in range(3):
                    # Spinning effect (2-4 cycles per reel)
                    spin_cycles = random.randint(2, 4)
                    for _ in range(spin_cycles):
                        await asyncio.sleep(0.6)
                        current_view = []
                        for j in range(3):
                            if j < i: # Stopped reels
                                current_view.append(final_roll[j])
                            else: # Spinning reels
                                current_view.append(random.choice(self.symbols))

                        display = " | ".join(current_view)
                        await msg.edit(content=f"🎰 | **{message.author.name}** Spent **{amount:,}**... (slots)\n[ {display} ]")

                    # Lock symbol for reel i
                    await asyncio.sleep(0.5)
                    current_view = []
                    for j in range(3):
                        if j <= i:
                            current_view.append(final_roll[j])
                        else:
                            current_view.append(random.choice(self.symbols))

                    display = " | ".join(current_view)
                    await msg.edit(content=f"🎰 | **{message.author.name}** Spent **{amount:,}**... (slots)\n[ {display} ]")

                # 3. Payout Logic
                display = " | ".join(final_roll)
                multiplier = 0
                if final_roll[0] == final_roll[1] == final_roll[2]:
                    # Triple Match Only
                    symbol = final_roll[0]
                    if symbol == "7️⃣": multiplier = 7 
                    elif symbol == "💎": multiplier = 5
                    else: multiplier = 3 # 🍒
                
                # EXP Gain
                exp_gain = random.randint(30, 60)
                leveling_cog = self.bot.get_cog("GameLeveling")
                level_msg = ""
                if leveling_cog:
                    leveled, new_lvl, reward = leveling_cog.add_exp(user_id, exp_gain)
                    if leveled:
                        level_msg = f"\n⭐ **LEVEL UP!** You are now Level **{new_lvl}** and received a **{reward:,}** bonus!"

                if multiplier > 0:
                    win_amount = int(amount * multiplier)
                    economy_cog.update_balance(user_id, win_amount)
                    await msg.edit(content=f"🎰 | **{message.author.name}** Spent **{amount:,}**... (slots)\n[ {display} ]\n\n:D | **and YOU WON 💶!** You won **{win_amount:,}**! (x{multiplier}){level_msg}")
                else:
                    await msg.edit(content=f"🎰 | **{message.author.name}** Spent **{amount:,}**... (slots)\n[ {display} ]\n\n:c | **and YOU LOST all!** Try again later.{level_msg}")

            except ValueError:
                await message.channel.send(f"⚠️ Use format: `{current_prefix}s <amount>`")
            except Exception as e:
                logger.error(f"Error in slots: {e}")

async def setup(bot):
    await bot.add_cog(Slots(bot))
