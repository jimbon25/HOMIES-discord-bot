"""Global Leaderboard System - Dummy data with fake users to encourage gameplay"""
import discord
from discord.ext import commands
import random
import json
import os
from pathlib import Path
from utils import safe_save_json
import logging

logger = logging.getLogger(__name__)

class LeaderboardView(discord.ui.View):
    """Pagination view for leaderboard - displays top 50 only"""
    
    def __init__(self, all_players, current_page=0, total_active=0):
        super().__init__(timeout=120)
        self.all_players = sorted(all_players, key=lambda x: x['balance'], reverse=True)[:50]  # ONLY TOP 50
        self.current_page = current_page
        self.per_page = 10
        self.total_active = total_active  # For display purposes
        self.max_pages = (len(self.all_players) + self.per_page - 1) // self.per_page
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.next_page.disabled = self.current_page >= self.max_pages - 1
        self.prev_page.disabled = self.current_page <= 0

    def censor_username(self, username: str) -> str:
        """Censor username to hide real identity - show first and last char"""
        if len(username) <= 3:
            return "*" * len(username)
        # Show first char, hide middle, show last 2 chars
        return username[0] + "*" * (len(username) - 3) + username[-2:]

    def get_page_embed(self) -> discord.Embed:
        """Generate embed for current page"""
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_players = self.all_players[start:end]
        
        embed = discord.Embed(
            title="🏆 Global Leaderboard",
            description=f"Top Players by Balance | Page {self.current_page + 1}/{self.max_pages}",
            color=discord.Color.gold()
        )
        
        players_text = ""
        for idx, player in enumerate(page_players, start=start + 1):
            censored = self.censor_username(player['username'])
            balance = player['balance']
            rank_emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "░"
            players_text += f"{rank_emoji} **#{idx}** | `{censored}` | **{balance:,}** MC\n"
        
        embed.add_field(
            name="Players",
            value=players_text if players_text else "No players on this page",
            inline=False
        )
        
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages}")
        return embed

    @discord.ui.button(label="◀", style=discord.ButtonStyle.grey, emoji="⬅️")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="▶", style=discord.ButtonStyle.grey, emoji="➡️")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
        else:
            await interaction.response.defer()


class GlobalLeaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leaderboard_file = "data/leaderboard_dummy.json"
        self.dummy_usernames = [
            "Dragon", "Phoenix", "Shadow", "Mystic", "Storm", "Blaze", "Frost", "Echo",
            "Viper", "Raven", "Tiger", "Wolf", "Sage", "Archer", "Knight", "Mage",
            "Ranger", "Paladin", "Warrior", "Rogue", "Monk", "Priest", "Sorcerer", "Summoner",
            "Necro", "Druid", "Bard", "Cleric", "Assassin", "Gladiator", "Berserker", "Crusader",
            "Explorer", "Hunter", "Scout", "Sentinel", "Guardian", "Enforcer", "Defender", "Protector",
            "Avenger", "Champion", "Hero", "Legend", "Titan", "Celestial", "Divine", "Spirit",
            "Phantom", "Ghost", "Specter", "Wraith", "Demon", "Angel", "Fallen", "Eternal"
        ]
        self.ensure_files()
        self.dummy_players = self.load_or_generate_dummy()

    def ensure_files(self):
        Path("data").mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.leaderboard_file):
            safe_save_json([], self.leaderboard_file)

    def load_or_generate_dummy(self):
        """Load dummy players or generate new ones"""
        try:
            with open(self.leaderboard_file, 'r') as f:
                players = json.load(f)
                if players and len(players) >= 50:
                    return players
        except:
            pass
        
        # Generate new dummy players - ONLY 50 to keep JSON small
        players = []
        used_names = set()
        
        for i in range(50):
            # Generate unique username (lowercase)
            while True:
                first = random.choice(self.dummy_usernames)
                second = random.choice(self.dummy_usernames)
                username = f"{first}{second}#{random.randint(1000, 9999)}".lower()
                if username not in used_names:
                    used_names.add(username)
                    break
            
            # Generate balance (higher for top players)
            if i < 5:
                balance = random.randint(50000000, 100000000)  # 50M - 100M for top 5
            elif i < 15:
                balance = random.randint(20000000, 50000000)   # 20M - 50M for top 15
            elif i < 30:
                balance = random.randint(1000000, 10000000)    # 1M - 10M for top 30
            else:
                balance = random.randint(100000, 1000000)      # 100K - 1M for rest
            
            players.append({
                "rank": i + 1,
                "username": username,
                "balance": balance
            })
        
        # Sort by balance descending
        players = sorted(players, key=lambda x: x['balance'], reverse=True)
        
        # Save to file
        safe_save_json(players, self.leaderboard_file)
        return players

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        coinflip_cog = self.bot.get_cog("CoinFlip")
        if not coinflip_cog:
            return

        current_prefix = coinflip_cog.get_guild_prefix(str(message.guild.id))
        content = message.content.lower().strip()

        # Command: <prefix>leaderboard or <prefix>lb
        if content == f"{current_prefix}leaderboard" or content == f"{current_prefix}lb":
            # Mix real players with dummy
            real_players = []
            coinflip_cog = self.bot.get_cog("CoinFlip")
            if coinflip_cog:
                for user_id, user_data in coinflip_cog.economy.items():
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        username = f"{user.name}#{user.discriminator}"
                        real_players.append({
                            "username": username,
                            "balance": user_data.get("balance", 0) if isinstance(user_data, dict) else user_data,
                            "is_real": True
                        })
                    except:
                        pass
            
            # Combine real + dummy players (but only display top 50)
            all_players = real_players + self.dummy_players
            total_all = len(all_players)  # Count total for reference
            
            # Create view AND it will slice to top 50
            view = LeaderboardView(all_players, current_page=0, total_active=total_all)
            embed = view.get_page_embed()
            
            await message.channel.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(GlobalLeaderboard(bot))
    logger.info("✅ GlobalLeaderboard cog loaded")
