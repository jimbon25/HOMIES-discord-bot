"""Leveling System for Games - Centralized EXP and Level management"""
import discord
from discord.ext import commands
import json
import os
from pathlib import Path
from utils import safe_save_json
import logging

logger = logging.getLogger(__name__)

class GameLeveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.level_file = "data/levels.json"
        self.ensure_files()
        self.levels = self.load_data()
        # Formula: EXP needed = Level * 1000
        self.exp_per_level = 1000

    def ensure_files(self):
        Path("data").mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.level_file):
            safe_save_json({}, self.level_file)

    def load_data(self):
        try:
            with open(self.level_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def save_data(self):
        safe_save_json(self.levels, self.level_file)

    def get_user_data(self, user_id: str) -> dict:
        if user_id not in self.levels:
            self.levels[user_id] = {"level": 1, "exp": 0, "total_played": 0}
            self.save_data()
        return self.levels[user_id]

    def add_exp(self, user_id: str, amount: int):
        """Add EXP and check for level up. Returns (level_up_bool, new_level, reward)"""
        data = self.get_user_data(user_id)
        data["exp"] += amount
        data["total_played"] += 1
        
        leveled_up = False
        new_level = data["level"]
        reward = 0
        
        # Check level up
        req_exp = data["level"] * self.exp_per_level
        if data["exp"] >= req_exp:
            data["exp"] -= req_exp
            data["level"] += 1
            new_level = data["level"]
            leveled_up = True
            # Reward: Level * 5000 cash (adjust as needed)
            reward = new_level * 5000
            
            # Add reward to economy
            coinflip_cog = self.bot.get_cog("CoinFlip")
            if coinflip_cog:
                coinflip_cog.update_balance(user_id, reward)
        
        self.levels[user_id] = data
        self.save_data()
        return leveled_up, new_level, reward

    # Global level check command using current prefix
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Get prefix from CoinFlip cog (or shared source)
        coinflip_cog = self.bot.get_cog("CoinFlip")
        if not coinflip_cog: return
        
        current_prefix = coinflip_cog.get_guild_prefix(str(message.guild.id))
        content = message.content.lower().strip()

        if content == f"{current_prefix}level":
            user_id = str(message.author.id)
            data = self.get_user_data(user_id)
            
            req_exp = data["level"] * self.exp_per_level
            progress = (data["exp"] / req_exp) * 100
            
            # Simple bar
            bar_length = 10
            filled = int(progress / 10)
            bar = "🟩" * filled + "⬜" * (bar_length - filled)

            embed = discord.Embed(
                title=f"Level {data['level']}",
                description=f"{bar} **{progress:.1f}%**\n`({data['exp']}/{req_exp} EXP)`",
                color=discord.Color.blue()
            )
            embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
            
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GameLeveling(bot))
