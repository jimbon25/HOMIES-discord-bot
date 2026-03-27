"""Daily Reward Command"""
import discord
from discord.ext import commands
import time
import logging

logger = logging.getLogger(__name__)

class DailyReward(commands.Cog):
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

        # Handle daily command
        if content == f"{current_prefix}daily":
            user_data = economy_cog.get_user_data(user_id)
            last_daily = user_data.get("last_daily", 0)
            current_time = int(time.time())
            
            # 24 hours in seconds
            cooldown = 24 * 60 * 60
            
            if current_time - last_daily < cooldown:
                remaining = cooldown - (current_time - last_daily)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                await message.channel.send(f"⏳ {message.author.mention}, you've already claimed your daily today! Wait **{hours} hours {minutes} minutes** more.")
                return

            reward = 10000
            user_data["balance"] += reward
            user_data["last_daily"] = current_time
            economy_cog.economy[user_id] = user_data
            economy_cog.save_economy()
            
            await message.channel.send(f"🎁 {message.author.mention}, you received a daily reward of **{reward:,}**!")

async def setup(bot):
    await bot.add_cog(DailyReward(bot))
    logger.info("✅ DailyReward cog loaded")
