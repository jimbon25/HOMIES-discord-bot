"""Transaction Commands - Pay and GiveCash"""
import discord
from discord.ext import commands
import os
import logging

logger = logging.getLogger(__name__)

class ConfirmationView(discord.ui.View):
    def __init__(self, initiator, target, amount, action_type, economy_cog):
        super().__init__(timeout=30)
        self.initiator = initiator
        self.target = target
        self.amount = amount
        self.action_type = action_type # 'pay' or 'givecash'
        self.economy_cog = economy_cog
        self.message = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.initiator.id:
            await interaction.response.send_message("❌ Only the sender can confirm!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        
        # Get existing embed to modify it
        embed = interaction.message.embeds[0]
        
        # Execute the transaction
        if self.action_type == 'pay':
            sender_balance = self.economy_cog.get_user_balance(str(self.initiator.id))
            if self.amount > sender_balance:
                embed.title = "❌ Transaction Failed"
                embed.description = "Insufficient balance to complete this transaction."
                embed.clear_fields()
                embed.add_field(name="Required", value=f"💶 **{self.amount:,}** Mahocoin", inline=True)
                embed.add_field(name="Available", value=f"💶 **{sender_balance:,}** Mahocoin", inline=True)
                embed.add_field(name="Shortfall", value=f"💶 **{self.amount - sender_balance:,}** Mahocoin", inline=False)
                embed.color = discord.Color.red()
                embed.set_footer(text="Insufficient Funds")
                await interaction.response.edit_message(embed=embed, view=self)
                return
            
            self.economy_cog.update_balance(str(self.initiator.id), -self.amount)
            self.economy_cog.update_balance(str(self.target.id), self.amount)
            
            embed.title = "✅ Transaction Completed"
            embed.description = "Your in-game currency transfer has been processed successfully."
            embed.clear_fields()
            embed.add_field(name="Sender", value=f"{self.initiator.mention}", inline=True)
            embed.add_field(name="Recipient", value=f"{self.target.mention}", inline=True)
            embed.add_field(name="Amount Transferred", value=f"💶 **{self.amount:,}** Mahocoin", inline=False)
            embed.add_field(name="Legal Reminder", value="Real Money Trading (RMT) is strictly prohibited and will result in permanent suspension.", inline=False)
            embed.color = discord.Color.green()
            embed.set_footer(text=f"Transaction ID: {interaction.id} | Status: Completed")
            
            await interaction.response.edit_message(embed=embed, view=self)
        
        elif self.action_type == 'givecash':
            self.economy_cog.update_balance(str(self.target.id), self.amount)
            
            embed.title = "✅ Owner Bypass Successful"
            embed.description = f"**{self.amount:,}** free cash has been generated for {self.target.mention}."
            embed.color = discord.Color.green()
            embed.set_footer(text="Status: Owner Authorized")
            
            await interaction.response.edit_message(embed=embed, view=self)
        
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.initiator.id:
            await interaction.response.send_message("❌ Only the sender can cancel!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.title = "❌ Transaction Canceled"
        embed.color = discord.Color.red()
        embed.description = "Transaction request has been canceled by the sender."
        embed.set_footer(text="Status: Canceled")
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

class Transactions(commands.Cog):
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

        # Handle pay command (Transfer/Transaction for everyone)
        if content.startswith(f"{current_prefix}pay"):
            parts = content.split()
            if len(parts) >= 3 and message.mentions:
                try:
                    target_user = message.mentions[0]
                    if target_user.bot:
                        await message.channel.send("❌ You cannot send money to bots!")
                        return
                    if target_user.id == message.author.id:
                        await message.channel.send("❌ You cannot send money to yourself!")
                        return

                    # Find the amount in parts
                    amount = None
                    for part in parts:
                        if part.isdigit():
                            amount = int(part)
                            break
                    
                    if amount is None or amount <= 0:
                        await message.channel.send("❌ Amount must be a positive number!")
                        return

                    sender_balance = economy_cog.get_user_balance(user_id)
                    if amount > sender_balance:
                        await message.channel.send(f"❌ Insufficient balance! (Balance: {sender_balance:,})")
                        return

                    # Confirmation logic - Professional Transaction Embed
                    embed = discord.Embed(
                        title="💶 Transaction Confirmation",
                        description="Please review the transaction details before confirming:",
                        color=discord.Color.gold()
                    )
                    embed.add_field(name="Sender", value=f"{message.author.mention} ({message.author.name})", inline=False)
                    embed.add_field(name="Recipient", value=f"{target_user.mention} ({target_user.name})", inline=False)
                    embed.add_field(name="Amount", value=f"💶 **{amount:,}** Mahocoin", inline=False)
                    embed.add_field(name="⚠️ Legal Notice", value="This is an IN-GAME transaction only. Real Money Trading (RMT) is **strictly prohibited** and will result in permanent account suspension.", inline=False)
                    embed.set_footer(text=f"Timestamp: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Confirm to proceed")
                    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3143/3143615.png")
                    
                    view = ConfirmationView(message.author, target_user, amount, 'pay', economy_cog)
                    view.message = await message.channel.send(embed=embed, view=view)
                    
                except Exception as e:
                    logger.error(f"Error in pay command: {e}")
                    await message.channel.send("⚠️ Invalid format! Use: `<prefix>pay @user <amount>`")

        # Handle give cash command (Owner only - Spawn money from air)
        elif content.startswith(f"{current_prefix}givecash"):
            # Check if user is owner from .env
            owner_id = os.getenv('OWNER_ID')
            if str(message.author.id) != owner_id:
                # If not owner, don't even respond to keep it a "secret" bypass
                return

            parts = content.split()
            if len(parts) >= 3 and message.mentions:
                try:
                    target_user = message.mentions[0]
                    amount = None
                    for part in parts:
                        if part.isdigit():
                            amount = int(part)
                            break

                    if amount is None: return

                    # Confirmation logic for owner
                    embed = discord.Embed(
                        title="💎 Owner Bypass Confirmation",
                        description=f"Generate **{amount:,}** free cash for {target_user.mention}?",
                        color=discord.Color.purple()
                    )
                    view = ConfirmationView(message.author, target_user, amount, 'givecash', economy_cog)
                    view.message = await message.channel.send(embed=embed, view=view)
                except:
                    pass

async def setup(bot):
    await bot.add_cog(Transactions(bot))
    logger.info("✅ Transactions cog loaded")
