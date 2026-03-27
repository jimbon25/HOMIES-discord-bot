"""Blackjack Game - Prefix-based game with interactive buttons"""
import discord
from discord.ext import commands
import random
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class BlackjackGameView(discord.ui.View):
    """View for blackjack game buttons"""
    
    def __init__(self, game_data, author, msg_obj, bot):
        super().__init__(timeout=120)
        self.game_data = game_data
        self.author = author
        self.msg = msg_obj
        self.bot = bot
        self.game_over = False

    def create_embed(self, hide_dealer_hole=True):
        """Create embed showing current game state"""
        player_hand = self.game_data["player_hand"]
        dealer_hand = self.game_data["dealer_hand"]
        
        player_value = self.calculate_value(player_hand)
        dealer_value = self.calculate_value(dealer_hand) if not hide_dealer_hole else None
        
        embed = discord.Embed(
            title="🃏 Blackjack Game",
            color=discord.Color.dark_gold()
        )
        
        # Player hand
        player_cards_str = " ".join([f"{c['rank']}{c['suit']}" for c in player_hand])
        embed.add_field(
            name=f"👤 Your Hand",
            value=f"{player_cards_str}\n**Value: {player_value}**",
            inline=False
        )
        
        # Dealer hand
        if hide_dealer_hole:
            dealer_cards_str = f"🎴 {dealer_hand[1]['rank']}{dealer_hand[1]['suit']}"
            embed.add_field(
                name="🤖 Dealer's Hand",
                value=f"{dealer_cards_str}\n**Value: ?**",
                inline=False
            )
        else:
            dealer_cards_str = " ".join([f"{c['rank']}{c['suit']}" for c in dealer_hand])
            embed.add_field(
                name="🤖 Dealer's Hand",
                value=f"{dealer_cards_str}\n**Value: {dealer_value}**",
                inline=False
            )
        
        embed.set_footer(text=f"Bet: {self.game_data['bet']:,} Mahocoin")
        return embed

    def calculate_value(self, hand):
        """Calculate hand value (handles Aces)"""
        value = 0
        aces = 0
        
        for card in hand:
            if card['rank'] in ['J', 'Q', 'K']:
                value += 10
            elif card['rank'] == 'A':
                aces += 1
                value += 11
            else:
                value += int(card['rank'])
        
        # Adjust for Aces if over 21
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value

    async def dealer_turn(self, economy_cog, user_id):
        """Execute dealer's turn"""
        while self.calculate_value(self.game_data["dealer_hand"]) < 17:
            self.game_data["dealer_hand"].append(self.draw_card())
            await asyncio.sleep(0.5)
            await self.msg.edit(embed=self.create_embed(hide_dealer_hole=False))

    def draw_card(self):
        """Draw a random card"""
        suits = ['♠️', '♥️', '♦️', '♣️']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        return {
            'rank': random.choice(ranks),
            'suit': random.choice(suits)
        }

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="➕")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Game is already over!", ephemeral=True)
            return
        
        self.game_data["player_hand"].append(self.draw_card())
        player_value = self.calculate_value(self.game_data["player_hand"])
        
        if player_value > 21:
            # Bust
            self.game_over = True
            for item in self.children:
                item.disabled = True
            
            user_id = str(self.author.id)
            exp_gain = random.randint(15, 40)
            level_msg = ""
            
            # Add EXP on bust
            leveling_cog = self.bot.get_cog("GameLeveling")
            if leveling_cog:
                leveled, new_lvl, reward = leveling_cog.add_exp(user_id, exp_gain)
                if leveled:
                    level_msg = f"\n⭐ **LEVEL UP!** You're now Level **{new_lvl}** and got **{reward:,}** bonus!"
            
            embed = self.create_embed(hide_dealer_hole=False)
            embed.title = "❌ BUST! You Lost!"
            embed.color = discord.Color.red()
            embed.add_field(name="Lost", value=f"-**{self.game_data['bet']:,}** Mahocoin", inline=False)
            embed.add_field(name="Experience", value=f"+**{exp_gain}** EXP{level_msg}", inline=False)
            
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary, emoji="🛑")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Game is already over!", ephemeral=True)
            return
        
        self.game_over = True
        for item in self.children:
            item.disabled = True
        
        # Dealer's turn
        await interaction.response.defer()
        await self.dealer_turn(None, None)
        
        # Calculate results
        player_value = self.calculate_value(self.game_data["player_hand"])
        dealer_value = self.calculate_value(self.game_data["dealer_hand"])
        
        embed = self.create_embed(hide_dealer_hole=False)
        
        # Calculate result and get user_id
        user_id = str(self.author.id)
        exp_gain = random.randint(15, 40)
        level_msg = ""
        
        # Add EXP regardless of outcome
        leveling_cog = self.bot.get_cog("GameLeveling")
        if leveling_cog:
            leveled, new_lvl, reward = leveling_cog.add_exp(user_id, exp_gain)
            if leveled:
                level_msg = f"\n⭐ **LEVEL UP!** You're now Level **{new_lvl}** and got **{reward:,}** bonus!"
        
        economy_cog = self.bot.get_cog("Economy")
        
        if dealer_value > 21:
            result = "win"
            embed.title = "🏆 YOU WIN! Dealer Busted!"
            embed.color = discord.Color.green()
            # Payout: 2x the bet
            if economy_cog:
                winnings = self.game_data["bet"] * 2
                economy_cog.update_balance(user_id, winnings)
            embed.add_field(name="Payout", value=f"+**{self.game_data['bet'] * 2:,}** Mahocoin", inline=False)
        elif player_value > dealer_value:
            result = "win"
            embed.title = "🏆 YOU WIN!"
            embed.color = discord.Color.green()
            # Payout: 2x the bet
            if economy_cog:
                winnings = self.game_data["bet"] * 2
                economy_cog.update_balance(user_id, winnings)
            embed.add_field(name="Payout", value=f"+**{self.game_data['bet'] * 2:,}** Mahocoin", inline=False)
        elif player_value < dealer_value:
            result = "lose"
            embed.title = "❌ YOU LOST!"
            embed.color = discord.Color.red()
            embed.add_field(name="Lost", value=f"-**{self.game_data['bet']:,}** Mahocoin", inline=False)
        else:
            result = "push"
            embed.title = "🤝 PUSH (Draw)"
            embed.color = discord.Color.light_grey()
            # Return the bet on push
            if economy_cog:
                economy_cog.update_balance(user_id, self.game_data["bet"])
            embed.add_field(name="Returned", value=f"**{self.game_data['bet']:,}** Mahocoin (Draw)", inline=False)
        
        embed.add_field(name="Experience", value=f"+**{exp_gain}** EXP{level_msg}", inline=False)
        
        await self.msg.edit(embed=embed, view=self)


class Blackjack(commands.Cog):
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

        # Command: <prefix>bj <amount>
        if content.startswith(f"{current_prefix}bj "):
            # Cooldown
            current_time = time.time()
            if user_id in self.cooldowns and current_time - self.cooldowns[user_id] < 30:
                remaining = int(30 - (current_time - self.cooldowns[user_id]))
                await message.channel.send(f"⏱️ {message.author.mention}, wait **{remaining}s** before next game!", delete_after=5)
                return

            try:
                # Parse amount
                amount_str = content[len(current_prefix) + 3:].strip()
                if not amount_str:
                    await message.channel.send(f"⚠️ Use: `{current_prefix}bj <amount>` or `{current_prefix}bj all`")
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

                # Start game
                self.cooldowns[user_id] = current_time
                
                # Deduct bet
                economy_cog.update_balance(user_id, -amount)
                
                # Create initial hands
                deck_suits = ['♠️', '♥️', '♦️', '♣️']
                deck_ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
                
                def get_card():
                    return {
                        'rank': random.choice(deck_ranks),
                        'suit': random.choice(deck_suits)
                    }
                
                player_hand = [get_card(), get_card()]
                dealer_hand = [get_card(), get_card()]
                
                game_data = {
                    "player_hand": player_hand,
                    "dealer_hand": dealer_hand,
                    "bet": amount
                }
                
                # Create initial embed
                view = BlackjackGameView(game_data, message.author, None, self.bot)
                embed = view.create_embed(hide_dealer_hole=True)
                
                # Send game message
                msg = await message.channel.send(
                    content=f"🃏 | **{message.author.name}** bet **{amount:,}** Mahocoin",
                    embed=embed,
                    view=view
                )
                view.msg = msg

            except ValueError:
                await message.channel.send(f"⚠️ Invalid amount! Use: `{current_prefix}bj 1000`")
            except Exception as e:
                logger.error(f"Blackjack error: {type(e).__name__}: {e}")
                await message.channel.send(f"❌ Error: {str(e)[:100]}", delete_after=5)


async def setup(bot):
    await bot.add_cog(Blackjack(bot))
    logger.info("✅ Blackjack cog loaded")
