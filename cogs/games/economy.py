"""Economy Management Cog - Handles data persistence and shared economy logic"""
import discord
from discord.ext import commands
import json
import os
from pathlib import Path
from utils import safe_save_json
import logging

logger = logging.getLogger(__name__)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.economy_file = "data/economy.json"
        self.prefix_file = "data/game_prefixes.json"
        self.tax_file = "data/server_taxes.json"
        self.ensure_files()
        self.economy = self.load_data(self.economy_file)
        self.prefixes = self.load_data(self.prefix_file)
        self.taxes = self.load_data(self.tax_file)
        # Default starting balance
        self.starting_balance = 5000 

    def ensure_files(self):
        """Ensure necessary files and directories exist"""
        Path("data").mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.economy_file):
            safe_save_json({}, self.economy_file)
        if not os.path.exists(self.prefix_file):
            safe_save_json({}, self.prefix_file)
        if not os.path.exists(self.tax_file):
            safe_save_json({}, self.tax_file)

    def load_data(self, file_path):
        """Load data from JSON file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return {}

    def save_economy(self):
        """Save economy data to JSON"""
        safe_save_json(self.economy, self.economy_file)

    def save_prefixes(self):
        """Save prefixes data to JSON"""
        safe_save_json(self.prefixes, self.prefix_file)

    def save_taxes(self):
        """Save tax data to JSON"""
        safe_save_json(self.taxes, self.tax_file)

    def get_server_tax(self, guild_id: str) -> int:
        """Get total collected tax for a server"""
        return self.taxes.get(guild_id, 0)

    def update_server_tax(self, guild_id: str, amount: int):
        """Add amount to server tax pool"""
        current_tax = self.get_server_tax(guild_id)
        self.taxes[guild_id] = current_tax + amount
        self.save_taxes()

    def get_user_data(self, user_id: str) -> dict:
        """Get full user data, initialize if not exists"""
        if user_id not in self.economy:
            self.economy[user_id] = {"balance": self.starting_balance, "last_daily": 0}
            self.save_economy()
        
        # Handle legacy format (if it was just an int)
        if isinstance(self.economy[user_id], int):
            self.economy[user_id] = {"balance": self.economy[user_id], "last_daily": 0}
            self.save_economy()
            
        return self.economy[user_id]

    def get_user_balance(self, user_id: str) -> int:
        """Get balance for a user"""
        return self.get_user_data(user_id)["balance"]

    def update_balance(self, user_id: str, amount: int):
        """Update user balance"""
        user_data = self.get_user_data(user_id)
        user_data["balance"] += amount
        self.economy[user_id] = user_data
        self.save_economy()

    def get_guild_prefix(self, guild_id: str) -> str:
        """Get prefix for a guild, default to 'h' as per user request"""
        return self.prefixes.get(guild_id, "h")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle economy-related configuration commands"""
        if message.author.bot or not message.guild:
            return

        content = message.content.lower().strip()
        guild_id = str(message.guild.id)
        
        # Handle "mahoraga prefix <char>"
        if content.startswith("mahoraga prefix"):
            parts = content.split()
            if len(parts) >= 3:
                new_prefix = parts[2][:1] # Limit to 1 char
                self.prefixes[guild_id] = new_prefix
                self.save_prefixes()
                await message.channel.send(f"✅ Game prefix has been set to: `{new_prefix}`")
                return
            else:
                current_prefix = self.get_guild_prefix(guild_id)
                await message.channel.send(f"Current prefix is: `{current_prefix}`. Use `mahoraga prefix <char>` to change it.")
                return

        # Handle "<prefix>tax" command
        current_prefix = self.get_guild_prefix(guild_id)
        if content == f"{current_prefix}tax":
            # Check if user is administrator
            if not message.author.guild_permissions.administrator:
                return

            total_tax = self.get_server_tax(guild_id)
            embed = discord.Embed(
                title="🏛️ Server Tax Vault",
                description=f"Total collected Mahocoin from transactions:\n```💶 {total_tax:,} MC```",
                color=discord.Color.dark_gold()
            )
            embed.set_footer(text=f"Server ID: {guild_id}")
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
    logger.info("✅ Economy cog loaded")
