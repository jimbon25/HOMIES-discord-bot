"""Coin Flip Game - Prefix-based game"""
import discord
from discord.ext import commands
import random
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

class CoinFlipGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Volatile cooldowns (reset on bot restart)
        self.cf_cooldowns = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Manual prefix and game command handler"""
        if message.author.bot or not message.guild:
            return

        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            return

        current_prefix = economy_cog.get_guild_prefix(str(message.guild.id))
        content = message.content.lower().strip()
        user_id = str(message.author.id)
        
        # Format: <prefix>cf <amount>
        if content.startswith(f"{current_prefix}cf"):
            # Cooldown check (15 seconds)
            current_time = time.time()
            last_cf = self.cf_cooldowns.get(user_id, 0)
            if current_time - last_cf < 15:
                remaining = int(15 - (current_time - last_cf))
                await message.channel.send(f"⏱️ {message.author.mention}, don't rush! Wait **{remaining} seconds** more to play again.", delete_after=5)
                return

            # Extract amount
            try:
                # Remove prefix + 'cf' and strip
                amount_str = content[len(current_prefix) + 2:].strip()
                if not amount_str:
                    await message.channel.send(f"⚠️ Use format: `{current_prefix}cf <amount>`")
                    return
                
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

                # After successful amount extraction and balance check:
                self.cf_cooldowns[user_id] = current_time # Update cooldown
                
                # Base text that stays static
                base_text = f"**{message.author.display_name}** Spent 💶 **{amount:,}** coin flips (Heads)"
                
                # Animation Logic
                msg = await message.channel.send(f"🪙 | {base_text}")
                
                # Visual Spinning Effect (3-5 cycles)
                spin_icons = ["🪙", "🟡", "🪙", "🟡"]
                spin_cycles = random.randint(3, 5)
                
                for cycle in range(spin_cycles):
                    await asyncio.sleep(0.7)
                    icon = random.choice(spin_icons)
                    await msg.edit(content=f"{icon} | {base_text}")

                await asyncio.sleep(0.5)

                # Game Logic
                win = random.random() < 0.5
                
                # EXP Gain regardless of win/loss
                exp_gain = random.randint(10, 30)
                leveling_cog = self.bot.get_cog("GameLeveling")
                level_msg = ""
                if leveling_cog:
                    leveled, new_lvl, reward = leveling_cog.add_exp(user_id, exp_gain)
                    if leveled:
                        level_msg = f"\n⭐ **LEVEL UP!** You are now Level **{new_lvl}** and received a **{reward:,}** bonus!"

                if win:
                    winnings = amount
                    economy_cog.update_balance(user_id, winnings)
                    
                    total_win = amount * 2
                    await msg.edit(content=f"🪙 | {base_text}\n:D | **and YOU WON 💶!** Total winnings: **{total_win:,}**.{level_msg}")
                else:
                    economy_cog.update_balance(user_id, -amount)
                    
                    await msg.edit(content=f"🪙 | {base_text}\n:c | **and YOU LOST all.** You lost :c **{amount:,}**.{level_msg}")

            except ValueError:
                await message.channel.send(f"⚠️ Amount must be a number! Example: `{current_prefix}cf 1000`")
            except Exception as e:
                logger.error(f"Error in coinflip game: {e}")

async def setup(bot):
    await bot.add_cog(CoinFlipGame(bot))
    logger.info("✅ CoinFlipGame cog loaded")
