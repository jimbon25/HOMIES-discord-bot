"""Rock Paper Scissors Game - PvE with Buttons"""
import discord
from discord.ext import commands
import random
import asyncio
import time
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RPSView(discord.ui.View):
    def __init__(self, author, amount, economy_cog, leveling_cog):
        super().__init__(timeout=60)
        self.author = author
        self.amount = amount
        self.economy_cog = economy_cog
        self.leveling_cog = leveling_cog
        self.choices = {
            "rock": {"emoji": "🪨", "beats": "scissors"},
            "paper": {"emoji": "📄", "beats": "rock"},
            "scissors": {"emoji": "✂️", "beats": "paper"}
        }

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

    async def process_game(self, interaction, user_choice):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        
        bot_choice = random.choice(list(self.choices.keys()))
        
        # Determine Winner
        if user_choice == bot_choice:
            result = "draw"
        elif self.choices[user_choice]["beats"] == bot_choice:
            result = "win"
        else:
            result = "lose"

        # Payout and EXP
        exp_gain = random.randint(10, 25)
        level_msg = ""
        if self.leveling_cog:
            leveled, new_lvl, reward = self.leveling_cog.add_exp(str(self.author.id), exp_gain)
            if leveled:
                level_msg = f"\n⭐ **LEVEL UP!** You're now Level **{new_lvl}** and got **{reward:,}** bonus!"

        # Create Result Embed
        user_emoji = self.choices[user_choice]["emoji"]
        bot_emoji = self.choices[bot_choice]["emoji"]
        
        embed = discord.Embed(title="🪨 Rock Paper Scissors", color=discord.Color.gold())
        
        if result == "win":
            winnings = self.amount * 2
            self.economy_cog.update_balance(str(self.author.id), winnings)
            embed.title = "🎯 YOU WON!"
            embed.color = discord.Color.green()
            embed.description = (
                f"**You:** {user_emoji} {user_choice.capitalize()}  **vs**  **Bot:** {bot_emoji} {bot_choice.capitalize()}\n"
                f"```🎯 Payout: 💶 {winnings:,} Mahocoin```\n"
                f"Experience: +**{exp_gain}** EXP{level_msg}"
            )
        elif result == "draw":
            self.economy_cog.update_balance(str(self.author.id), self.amount)
            embed.title = "🤝 DRAW!"
            embed.color = discord.Color.light_grey()
            embed.description = (
                f"**You:** {user_emoji} {user_choice.capitalize()}  **vs**  **Bot:** {bot_emoji} {bot_choice.capitalize()}\n"
                f"```🤝 Returned: 💶 {self.amount:,} Mahocoin```\n"
                f"Experience: +**{exp_gain}** EXP{level_msg}"
            )
        else:
            embed.title = "❌ YOU LOST!"
            embed.color = discord.Color.red()
            embed.description = (
                f"**You:** {user_emoji} {user_choice.capitalize()}  **vs**  **Bot:** {bot_emoji} {bot_choice.capitalize()}\n"
                f"```❌ Lost: 💶 {self.amount:,} Mahocoin```\n"
                f"Experience: +**{exp_gain}** EXP{level_msg}"
            )
        
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Rock", style=discord.ButtonStyle.primary, emoji="🪨")
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_game(interaction, "rock")

    @discord.ui.button(label="Paper", style=discord.ButtonStyle.primary, emoji="📄")
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_game(interaction, "paper")

    @discord.ui.button(label="Scissors", style=discord.ButtonStyle.primary, emoji="✂️")
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_game(interaction, "scissors")

class RockPaperScissors(commands.Cog):
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

        # Command: <prefix>rps <amount>
        if content.startswith(f"{current_prefix}rps "):
            # Cooldown check (15 seconds)
            current_time = time.time()
            if user_id in self.cooldowns and current_time - self.cooldowns[user_id] < 15:
                remaining = int(15 - (current_time - self.cooldowns[user_id]))
                await message.channel.send(f"⏱️ {message.author.mention}, wait **{remaining}s** before next match!", delete_after=5)
                return

            try:
                # Parse amount
                amount_str = content[len(current_prefix) + 4:].strip()
                if not amount_str:
                    await message.channel.send(f"⚠️ Use: `{current_prefix}rps <amount>` or `{current_prefix}rps all`")
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

                # Deduct bet
                economy_cog.update_balance(user_id, -amount)
                self.cooldowns[user_id] = current_time
                
                # Start Game
                leveling_cog = self.bot.get_cog("GameLeveling")
                view = RPSView(message.author, amount, economy_cog, leveling_cog)
                
                embed = discord.Embed(
                    title="🪨 Rock Paper Scissors",
                    description=(
                        f"**{message.author.display_name}** vs **Bot**\n"
                        f"Bet: `💶 {amount:,} Mahocoin`\n\n"
                        "Choose your weapon to challenge Mahoraga!"
                    ),
                    color=discord.Color.gold()
                )
                
                msg = await message.channel.send(embed=embed, view=view)
                view.message = msg

            except ValueError:
                await message.channel.send(f"⚠️ Invalid amount! Example: `{current_prefix}rps 1000`")
            except Exception as e:
                logger.error(f"RPS Error: {e}")

async def setup(bot):
    await bot.add_cog(RockPaperScissors(bot))
    logger.info("✅ RPS cog loaded")
