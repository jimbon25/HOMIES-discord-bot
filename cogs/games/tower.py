"""Maho-Tower Game - Vertical Climbing Gambling"""
import discord
from discord.ext import commands
import random
import asyncio
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def calculate_tower_multiplier(floor):
    """
    Calculate tower multiplier based on 1/3 trap probability per floor.
    Using 15% House Edge for economy balance.
    Formula: (0.85) / ( (2/3) ^ floor )
    """
    if floor <= 0:
        return 1.0
    prob = (2/3) ** floor
    multiplier = 0.85 / prob
    return round(multiplier, 2)

class TowerButton(discord.ui.Button):
    def __init__(self, index):
        # index 0, 1, 2 for the three choices on each floor
        super().__init__(style=discord.ButtonStyle.secondary, label="❓", row=0)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: TowerView = self.view
        if interaction.user.id != view.author.id:
            return await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
        
        await view.process_choice(interaction, self.index)

class TowerView(discord.ui.View):
    def __init__(self, author, amount, economy_cog, leveling_cog):
        super().__init__(timeout=120)
        self.author = author
        self.amount = amount
        self.economy_cog = economy_cog
        self.leveling_cog = leveling_cog
        self.current_floor = 0 # 0 means game just started, Floor 1 is next
        self.max_floors = 8
        self.game_over = False
        
        # Current floor trap position (0, 1, or 2)
        self.trap_pos = random.randint(0, 2)
        
        # Add the 3 choice buttons
        for i in range(3):
            self.add_item(TowerButton(i))
            
        # Add Cashout button in a separate row
        self.cashout_button = discord.ui.Button(label="Cashout (1.0x)", style=discord.ButtonStyle.success, row=1, disabled=True)
        self.cashout_button.callback = self.cashout_callback
        self.add_item(self.cashout_button)

    async def cashout_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
        
        await self.end_game(interaction, won=True)

    async def process_choice(self, interaction: discord.Interaction, choice_index):
        if self.game_over:
            return

        if choice_index == self.trap_pos:
            # Hit trap
            await self.end_game(interaction, won=False, choice_made=choice_index)
        else:
            # Safe!
            self.current_floor += 1
            
            if self.current_floor == self.max_floors:
                # Reached the top!
                await self.end_game(interaction, won=True)
            else:
                # Progress to next floor
                self.trap_pos = random.randint(0, 2)
                current_mult = calculate_tower_multiplier(self.current_floor)
                next_mult = calculate_tower_multiplier(self.current_floor + 1)
                
                self.cashout_button.label = f"Cashout ({current_mult}x)"
                self.cashout_button.disabled = False
                
                embed = self.create_embed(current_mult, next_mult)
                await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self, current_mult, next_mult=None):
        tower_visual = ""
        for i in range(self.max_floors, 0, -1):
            if i == self.current_floor + 1:
                tower_visual += f"➡️ **Floor {i}** (Current)\n"
            elif i <= self.current_floor:
                tower_visual += f"✅ Floor {i}\n"
            else:
                tower_visual += f"⬛ Floor {i}\n"
        
        profit = int(self.amount * current_mult) - self.amount
        desc = (
            f"👤 **Climber:** {self.author.mention}\n"
            f"💶 **Bet:** `{self.amount:,} Mahocoin`\n\n"
            f"{tower_visual}\n"
            f"```📈 Current Mult: {current_mult}x\n"
            f"💰 Potential Profit: +{profit:,} MC```"
        )
        if next_mult and not self.game_over:
            desc += f"\nNext floor multiplier: **{next_mult}x**"
            
        embed = discord.Embed(title="🏰 Maho-Tower", description=desc, color=discord.Color.gold())
        return embed

    async def end_game(self, interaction, won, choice_made=None):
        self.game_over = True
        current_mult = calculate_tower_multiplier(self.current_floor)
        
        # Disable all items
        for child in self.children:
            child.disabled = True
            if isinstance(child, TowerButton) and choice_made is not None:
                if child.index == self.trap_pos:
                    child.emoji = "💥"
                    child.style = discord.ButtonStyle.danger
                elif child.index == choice_made:
                    child.emoji = "✅"
                    child.style = discord.ButtonStyle.success

        exp_gain = random.randint(15, 45)
        level_msg = ""
        if self.leveling_cog:
            leveled, new_lvl, reward = self.leveling_cog.add_exp(str(self.author.id), exp_gain)
            if leveled:
                level_msg = f"\n⭐ **LEVEL UP!** Now Level **{new_lvl}** (+{reward:,} bonus!)"

        embed = discord.Embed(title="🏰 Maho-Tower Result")
        
        if won:
            winnings = int(self.amount * current_mult)
            self.economy_cog.update_balance(str(self.author.id), winnings)
            embed.color = discord.Color.green()
            embed.title = "🏆 TOWER CONQUERED!"
            embed.description = (
                f"**You cashed out at Floor {self.current_floor}!**\n"
                f"```🎯 Total Win: 💶 {winnings:,} Mahocoin ({current_mult}x)```\n"
                f"Experience: +**{exp_gain}** EXP{level_msg}"
            )
        else:
            embed.color = discord.Color.red()
            embed.title = "💀 YOU FELL!"
            embed.description = (
                f"**You hit a trap on Floor {self.current_floor + 1}!**\n"
                f"```❌ Lost: 💶 {self.amount:,} Mahocoin```\n"
                f"Experience: +**{exp_gain}** EXP{level_msg}"
            )

        if interaction.response.is_done():
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

class Tower(commands.Cog):
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

        cmd_name = f"{current_prefix}tower"
        if not content.startswith(cmd_name):
            return

        # Cooldown check (20 seconds)
        current_time = time.time()
        if user_id in self.cooldowns and current_time - self.cooldowns[user_id] < 20:
            remaining = int(20 - (current_time - self.cooldowns[user_id]))
            await message.channel.send(f"⏱️ {message.author.mention}, wait **{remaining}s** before climbing again!", delete_after=5)
            return

        try:
            args_content = content[len(cmd_name):].strip()
            if not args_content:
                await message.channel.send(f"⚠️ Use: `{current_prefix}tower <amount>`")
                return

            # Parse amount
            raw_amount = args_content.split()[0].replace(",", "").replace(".", "")
            if raw_amount == "all":
                amount = economy_cog.get_user_balance(user_id)
            elif raw_amount.isdigit():
                amount = int(raw_amount)
            else:
                await message.channel.send(f"⚠️ Invalid amount. Use numbers only.")
                return

            # Balance check
            if amount <= 0:
                await message.channel.send("❌ Bet must be > 0!")
                return

            balance = economy_cog.get_user_balance(user_id)
            if amount > balance:
                await message.channel.send(f"❌ Insufficient balance! ({balance:,})")
                return

            # Deduct bet and set cooldown
            economy_cog.update_balance(user_id, -amount)
            self.cooldowns[user_id] = current_time
            
            # Start Game
            leveling_cog = self.bot.get_cog("GameLeveling")
            view = TowerView(message.author, amount, economy_cog, leveling_cog)
            
            initial_mult = calculate_tower_multiplier(1)
            embed = view.create_embed(1.0, initial_mult)
            
            msg = await message.channel.send(embed=embed, view=view)
            view.message = msg

        except Exception as e:
            logger.error(f"Tower Error: {e}")
            await message.channel.send(f"❌ Error: {str(e)[:100]}")

async def setup(bot):
    await bot.add_cog(Tower(bot))
    logger.info("✅ Tower cog loaded")
