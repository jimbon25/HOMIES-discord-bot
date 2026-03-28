"""Daily Reward Command - Reset globally at 15:00 WIB (08:00 UTC)"""
import discord
from discord.ext import commands
import time
import datetime
import logging

logger = logging.getLogger(__name__)

class DailyReward(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_last_reset_time(self):
        """Get the timestamp of the most recent 15:00 WIB (08:00 UTC) reset"""
        # UTC+7 is WIB, so 15:00 WIB = 08:00 UTC
        now = datetime.datetime.now(datetime.timezone.utc)
        reset_hour = 8
        
        # Reset for today (UTC)
        today_reset = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
        
        if now < today_reset:
            # If current time is before reset time, the most recent reset was yesterday
            last_reset = today_reset - datetime.timedelta(days=1)
        else:
            # Most recent reset was today
            last_reset = today_reset
            
        return last_reset.timestamp()

    def get_next_reset_time(self):
        """Get the timestamp of the next 15:00 WIB (08:00 UTC) reset"""
        now = datetime.datetime.now(datetime.timezone.utc)
        reset_hour = 8
        
        # Reset for today (UTC)
        today_reset = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
        
        if now < today_reset:
            next_reset = today_reset
        else:
            # Next reset is tomorrow
            next_reset = today_reset + datetime.timedelta(days=1)
            
        return next_reset.timestamp()

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
            
            last_reset_ts = self.get_last_reset_time()
            
            # Can claim if last claim was before the most recent reset
            if last_daily >= last_reset_ts:
                next_reset_ts = self.get_next_reset_time()
                remaining = int(next_reset_ts - time.time())
                
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                
                await message.channel.send(f"⏳ **{message.author.display_name}**, you've already claimed your daily today! Reset in (**{hours}h {minutes}m** more).")
                return

            reward = 10000
            user_data["balance"] += reward
            user_data["last_daily"] = int(time.time())
            economy_cog.economy[user_id] = user_data
            economy_cog.save_economy()
            
            await message.channel.send(f"🎁 **{message.author.display_name}**, you received a daily reward of **{reward:,}**")

async def setup(bot):
    await bot.add_cog(DailyReward(bot))
    logger.info("✅ DailyReward cog loaded (Global Reset at 15:00 WIB)")
