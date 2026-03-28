"""Maho-Mines Game - 4x5 Grid Minesweeper Gambling"""
import discord
from discord.ext import commands
import random
import asyncio
import time
import math
import logging

logger = logging.getLogger(__name__)

def calculate_multiplier(bombs, gems, total_tiles=20):
    """Calculate mines multiplier based on probability theory with 5% House Edge"""
    if gems <= 0:
        return 1.0
    if gems > (total_tiles - bombs):
        return 0.0

    def nCr(n, r):
        if r < 0 or r > n:
            return 0
        if r == 0 or r == n:
            return 1
        if r > n // 2:
            r = n - r
        f = math.factorial
        try:
            return f(n) // (f(r) * f(n - r))
        except (ValueError, OverflowError):
            return 0

    try:
        num_safe = total_tiles - bombs
        total_combos = nCr(total_tiles, gems)
        safe_combos = nCr(num_safe, gems)
        
        if total_combos == 0 or safe_combos == 0:
            return 0.0
            
        prob = safe_combos / total_combos
        multiplier = 0.85 / prob # 15% House Edge (Significantly nerfed for long-term economy balance)
        return round(multiplier, 2)
    except (ZeroDivisionError, ValueError):
        return 0.0
    except Exception:
        return 1.0

class MinesButton(discord.ui.Button):
    """Individual tile button for the Mines grid"""
    def __init__(self, x, y):
        # Secondary style is grey
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: MinesView = self.view
        if interaction.user.id != view.author.id:
            return await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
        await view.process_click(interaction, self)

class MinesView(discord.ui.View):
    """Main View for the Mines game handling grid and logic"""
    def __init__(self, author, amount, bombs_count, economy_cog, leveling_cog):
        super().__init__(timeout=120)
        self.author = author
        self.amount = amount
        self.bombs_count = bombs_count
        self.economy_cog = economy_cog
        self.leveling_cog = leveling_cog
        self.gems_found = 0
        self.game_over = False
        
        # Grid Configuration: 4 rows x 5 columns = 20 tiles
        self.rows = 4
        self.cols = 5
        self.total_tiles = self.rows * self.cols
        
        # Initialize grid data (True = Bomb)
        self.grid = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        bomb_positions = random.sample(range(self.total_tiles), self.bombs_count)
        for pos in bomb_positions:
            self.grid[pos // self.cols][pos % self.cols] = True
            
        # Add grid buttons to rows 0-3
        for y in range(self.rows):
            for x in range(self.cols):
                self.add_item(MinesButton(x, y))
        
        # Add Cashout button to row 4 (bottom)
        self.cashout_button = discord.ui.Button(
            label=f"Cashout (1.0x)", 
            style=discord.ButtonStyle.success, 
            row=4
        )
        self.cashout_button.callback = self.cashout_callback
        self.add_item(self.cashout_button)

    async def cashout_callback(self, interaction: discord.Interaction):
        """Handle cashout request"""
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
        
        if self.gems_found == 0:
            return await interaction.response.send_message("❌ Find at least one gem to cashout!", ephemeral=True)
            
        await self.end_game(interaction, won=True)

    async def process_click(self, interaction: discord.Interaction, button: MinesButton):
        """Handle tile click logic"""
        if self.game_over:
            return

        # Check if user hit a bomb
        if self.grid[button.y][button.x]:
            button.style = discord.ButtonStyle.danger
            button.emoji = "💣"
            button.label = None
            await self.end_game(interaction, won=False)
        else:
            self.gems_found += 1
            button.style = discord.ButtonStyle.success
            button.emoji = "💎"
            button.label = None
            button.disabled = True
            
            # Update multiplier UI
            current_mult = calculate_multiplier(self.bombs_count, self.gems_found, self.total_tiles)
            next_mult = calculate_multiplier(self.bombs_count, self.gems_found + 1, self.total_tiles)
            
            self.cashout_button.label = f"Cashout ({current_mult}x)"
            
            # Win if all gems found
            if self.gems_found == (self.total_tiles - self.bombs_count):
                await self.end_game(interaction, won=True)
            else:
                embed = self.create_embed(current_mult, next_mult)
                await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self, current_mult, next_mult=None):
        """Create game status embed with Bomb count"""
        profit = int(self.amount * current_mult) - self.amount
        desc = (
            f"👤 **Player:** {self.author.mention}\n"
            f"💶 **Bet:** `{self.amount:,} Mahocoin`\n"
            f"💣 **Bombs:** `{self.bombs_count}`\n"
            f"```💎 Gems: {self.gems_found}\n"
            f"📈 Mult: {current_mult}x\n"
            f"💰 Profit: +{profit:,} MC```"
        )
        if next_mult and not self.game_over:
            desc += f"\n*Multiplier akan terus naik setiap ubin aman!*"
            
        embed = discord.Embed(title="💎 Maho-Mines", description=desc, color=discord.Color.blue())
        return embed

    async def end_game(self, interaction, won):
        """Handle end of game state"""
        self.game_over = True
        current_mult = calculate_multiplier(self.bombs_count, self.gems_found, self.total_tiles)
        
        # Reveal all tiles and ensure they are perfectly aligned
        for child in self.children:
            if isinstance(child, MinesButton):
                child.disabled = True
                child.label = None
                
                if self.grid[child.y][child.x]:
                    child.emoji = "💣"
                    child.style = discord.ButtonStyle.danger
                else:
                    child.emoji = "💎"
                    if child.style != discord.ButtonStyle.success:
                        child.style = discord.ButtonStyle.secondary
            else:
                child.disabled = True

        # EXP Reward
        exp_gain = random.randint(25, 60)
        level_msg = ""
        if self.leveling_cog:
            leveled, new_lvl, reward = self.leveling_cog.add_exp(str(self.author.id), exp_gain)
            if leveled:
                level_msg = f"\n⭐ **LEVEL UP!** Now Level **{new_lvl}** (+{reward:,} bonus!)"

        embed = discord.Embed(title="💎 Maho-Mines Result")
        
        if won:
            winnings = int(self.amount * current_mult)
            self.economy_cog.update_balance(str(self.author.id), winnings)
            embed.color = discord.Color.green()
            embed.title = "🎯 MISSION SUCCESS!"
            embed.description = (
                f"**You escaped with the loot!**\n"
                f"```🎯 Win: 💶 {winnings:,} Mahocoin ({current_mult}x)```\n"
                f"Experience: +**{exp_gain}** EXP{level_msg}"
            )
        else:
            embed.color = discord.Color.red()
            embed.title = "💥 MISSION FAILED!"
            embed.description = (
                f"**You hit a bomb!** Better luck next time.\n"
                f"```❌ Loss: 💶 {self.amount:,} Mahocoin```\n"
                f"Experience: +**{exp_gain}** EXP{level_msg}"
            )

        if interaction.response.is_done():
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

class Mines(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

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

        # Command detection
        cmd_name = f"{current_prefix}mines"
        if not content.startswith(cmd_name):
            return

        # Cooldown check
        current_time = time.time()
        if user_id in self.cooldowns and current_time - self.cooldowns[user_id] < 20:
            remaining = int(20 - (current_time - self.cooldowns[user_id]))
            await message.channel.send(f"⏱️ {message.author.mention}, wait **{remaining}s**!", delete_after=5)
            return

        try:
            # Parse arguments
            args_content = content[len(cmd_name):].strip()
            if not args_content:
                await message.channel.send(f"⚠️ Use: `{current_prefix}mines <amount>`")
                return

            parts = args_content.split()
            
            # Amount parsing
            raw_amount = parts[0].replace(",", "").replace(".", "")
            if raw_amount == "all":
                amount = economy_cog.get_user_balance(user_id)
            elif raw_amount.isdigit():
                amount = int(raw_amount)
            else:
                await message.channel.send(f"⚠️ Invalid amount: `{parts[0]}`.")
                return

            # Balance check
            if amount <= 0:
                await message.channel.send("❌ Bet must be > 0!")
                return

            balance = economy_cog.get_user_balance(user_id)
            if amount > balance:
                await message.channel.send(f"❌ Insufficient balance! ({balance:,})")
                return

            # Randomize Bombs (Balanced Range: 2 - 15 bombs)
            bombs = random.randint(2, 15)

            # Execute
            economy_cog.update_balance(user_id, -amount)
            self.cooldowns[user_id] = current_time
            
            leveling_cog = self.bot.get_cog("GameLeveling")
            view = MinesView(message.author, amount, bombs, economy_cog, leveling_cog)
            
            initial_mult = calculate_multiplier(bombs, 1)
            embed = view.create_embed(1.0, initial_mult)
            
            msg = await message.channel.send(embed=embed, view=view)
            view.message = msg

        except Exception as e:
            logger.error(f"Mines Error: {e}")
            await message.channel.send(f"❌ Error: {str(e)[:100]}")

async def setup(bot):
    await bot.add_cog(Mines(bot))
    logger.info("✅ Mines cog loaded")
