"""Coin Flip Game - Prefix-based game with economy system"""
import discord
from discord.ext import commands
import json
import os
import random
import time
from pathlib import Path
from utils import safe_save_json
import logging

logger = logging.getLogger(__name__)

class ConfirmationView(discord.ui.View):
    def __init__(self, initiator, target, amount, action_type, cog):
        super().__init__(timeout=30)
        self.initiator = initiator
        self.target = target
        self.amount = amount
        self.action_type = action_type # 'pay' or 'givecash'
        self.cog = cog
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
            await interaction.response.send_message("❌ Hanya pengirim yang bisa mengonfirmasi!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        
        # Get existing embed to modify it
        embed = interaction.message.embeds[0]
        
        # Execute the transaction
        if self.action_type == 'pay':
            sender_balance = self.cog.get_user_balance(str(self.initiator.id))
            if self.amount > sender_balance:
                embed.title = "❌ Transaksi Gagal"
                embed.description = f"Saldo {self.initiator.mention} tidak mencukupi."
                embed.color = discord.Color.red()
                await interaction.response.edit_message(embed=embed, view=self)
                return
            
            self.cog.update_balance(str(self.initiator.id), -self.amount)
            self.cog.update_balance(str(self.target.id), self.amount)
            
            embed.title = "✅ Pembayaran Berhasil"
            embed.description = f"**{self.amount:,}** cash telah dikirim ke {self.target.mention}."
            embed.color = discord.Color.green()
            embed.set_footer(text=f"Status: Sukses | ID: {interaction.id}")
            
            await interaction.response.edit_message(embed=embed, view=self)
        
        elif self.action_type == 'givecash':
            self.cog.update_balance(str(self.target.id), self.amount)
            
            embed.title = "✅ Owner Bypass Berhasil"
            embed.description = f"**{self.amount:,}** cash gratis telah di-generate untuk {self.target.mention}."
            embed.color = discord.Color.green()
            embed.set_footer(text="Status: Owner Authorized")
            
            await interaction.response.edit_message(embed=embed, view=self)
        
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.initiator.id:
            await interaction.response.send_message("❌ Hanya pengirim yang bisa membatalkan!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.title = "❌ Transaksi Dibatalkan"
        embed.color = discord.Color.red()
        embed.description = "Permintaan transaksi telah dibatalkan oleh pengirim."
        embed.set_footer(text="Status: Dibatalkan")
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

class CoinFlip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.economy_file = "data/economy.json"
        self.prefix_file = "data/game_prefixes.json"
        self.ensure_files()
        self.economy = self.load_data(self.economy_file)
        self.prefixes = self.load_data(self.prefix_file)
        # Default starting balance
        self.starting_balance = 5000 
        # Volatile cooldowns (reset on bot restart)
        self.cf_cooldowns = {}
        self.work_cooldowns = {}

    def ensure_files(self):
        """Ensure necessary files and directories exist"""
        Path("data").mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.economy_file):
            safe_save_json({}, self.economy_file)
        if not os.path.exists(self.prefix_file):
            safe_save_json({}, self.prefix_file)

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
        """Manual prefix and game command handler"""
        if message.author.bot or not message.guild:
            return

        content = message.content.lower().strip()
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        
        # 1. Handle "mahoraga prefix <char>"
        if content.startswith("mahoraga prefix"):
            parts = content.split()
            if len(parts) >= 3:
                new_prefix = parts[2][:1] # Limit to 1 char
                self.prefixes[guild_id] = new_prefix
                self.save_prefixes()
                await message.channel.send(f"✅ Prefix untuk game telah diatur menjadi: `{new_prefix}`")
                return
            else:
                current_prefix = self.get_guild_prefix(guild_id)
                await message.channel.send(f"Prefix saat ini adalah: `{current_prefix}`. Gunakan `mahoraga prefix <char>` untuk mengubahnya.")
                return

        # 2. Handle game commands with prefix
        current_prefix = self.get_guild_prefix(guild_id)
        
        # Format: <prefix>cf <amount>
        if content.startswith(f"{current_prefix}cf"):
            # Cooldown check (10 seconds)
            current_time = time.time()
            last_cf = self.cf_cooldowns.get(user_id, 0)
            if current_time - last_cf < 10:
                remaining = int(10 - (current_time - last_cf))
                await message.channel.send(f"⏱️ {message.author.mention}, jangan terburu-buru! Tunggu **{remaining} detik** lagi untuk main lagi.", delete_after=5)
                return

            # Extract amount
            try:
                # Remove prefix + 'cf' and strip
                amount_str = content[len(current_prefix) + 2:].strip()
                if not amount_str:
                    await message.channel.send(f"⚠️ Gunakan format: `{current_prefix}cf <nominal>`")
                    return
                
                if amount_str == "all":
                    amount = self.get_user_balance(user_id)
                else:
                    amount = int(amount_str)

                if amount <= 0:
                    await message.channel.send("❌ Nominal harus lebih dari 0!")
                    return

                balance = self.get_user_balance(user_id)
                if amount > balance:
                    await message.channel.send(f"❌ Cash kamu tidak cukup! (Sisa: {balance:,} cash)")
                    return

                # After successful amount extraction and balance check:
                self.cf_cooldowns[user_id] = current_time # Update cooldown
                
                # Animation Logic
                msg = await message.channel.send(f"🪙 | **Melambungkan {amount:,} cash...**")
                import asyncio
                
                await asyncio.sleep(0.7)
                await msg.edit(content=f"🔄 | **Koin {amount:,} cash memutar di udara...**")
                await asyncio.sleep(0.7)

                # Game Logic
                win = random.random() < 0.5
                if win:
                    winnings = amount
                    self.update_balance(user_id, winnings)
                    
                    total_win = amount * 2
                    await msg.edit(content=f"🎉 | **MENANG!** Total kemenangan: **{total_win:,}** cash.")
                else:
                    self.update_balance(user_id, -amount)
                    
                    await msg.edit(content=f"💸 | **KALAH.** Kamu kehilangan **{amount:,}** cash.")

            except ValueError:
                await message.channel.send(f"⚠️ Nominal harus berupa angka! Contoh: `{current_prefix}cf 1000`")
            except Exception as e:
                logger.error(f"Error in coinflip game: {e}")

        # 3. Handle cash check command
        elif content == f"{current_prefix}cash":
            balance = self.get_user_balance(user_id)
            embed = discord.Embed(
                title="💰 Wallet",
                description=f"Cash {message.author.mention}: **{balance:,}**",
                color=discord.Color.gold()
            )
            await message.channel.send(embed=embed)

        # 3a. Handle daily command
        elif content == f"{current_prefix}daily":
            user_data = self.get_user_data(user_id)
            last_daily = user_data.get("last_daily", 0)
            current_time = int(time.time())
            
            # 24 hours in seconds
            cooldown = 24 * 60 * 60
            
            if current_time - last_daily < cooldown:
                remaining = cooldown - (current_time - last_daily)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                await message.channel.send(f"⏳ {message.author.mention}, kamu sudah mengambil daily hari ini! Tunggu **{hours} jam {minutes} menit** lagi.")
                return

            reward = 10000
            user_data["balance"] += reward
            user_data["last_daily"] = current_time
            self.economy[user_id] = user_data
            self.save_economy()
            
            await message.channel.send(f"🎁 {message.author.mention}, kamu mendapatkan daily reward sebesar **{reward:,}** cash!")

        # 3b. Handle work command
        elif content == f"{current_prefix}work":
            # Cooldown check (30 seconds)
            current_time = time.time()
            last_work = self.work_cooldowns.get(user_id, 0)
            if current_time - last_work < 30:
                remaining = int(30 - (current_time - last_work))
                await message.channel.send(f"👷 {message.author.mention}, kamu capek! Istirahat dulu selama **{remaining} detik**.", delete_after=5)
                return

            self.work_cooldowns[user_id] = current_time
            reward = random.randint(100, 1000)
            jobs = ["Bantu Mak Lampir", "Jualan Es Cendol", "Jadi Kuli Jawa", "Ngelas Kapal", "Nariking Becak"]
            job = random.choice(jobs)
            self.update_balance(user_id, reward)
            await message.channel.send(f"👷 {message.author.mention}, kamu bekerja sebagai **{job}** dan dibayar **{reward:,}** cash!")

        # 3c. Handle pay command (Transfer/Transaction for everyone)
        elif content.startswith(f"{current_prefix}pay"):
            parts = content.split()
            if len(parts) >= 3 and message.mentions:
                try:
                    target_user = message.mentions[0]
                    if target_user.bot:
                        await message.channel.send("❌ Kamu tidak bisa mengirim uang ke bot!")
                        return
                    if target_user.id == message.author.id:
                        await message.channel.send("❌ Kamu tidak bisa mengirim uang ke diri sendiri!")
                        return

                    # Find the amount in parts
                    amount = None
                    for part in parts:
                        if part.isdigit():
                            amount = int(part)
                            break
                    
                    if amount is None or amount <= 0:
                        await message.channel.send("❌ Nominal harus berupa angka positif!")
                        return

                    sender_balance = self.get_user_balance(user_id)
                    if amount > sender_balance:
                        await message.channel.send(f"❌ Saldo kamu tidak cukup! (Sisa: {sender_balance:,} cash)")
                        return

                    # Confirmation logic
                    embed = discord.Embed(
                        title="📜 Konfirmasi Pembayaran",
                        description=f"Apakah kamu yakin ingin mengirim **{amount:,}** cash kepada {target_user.mention}?",
                        color=discord.Color.yellow()
                    )
                    embed.add_field(name="Penerima", value=target_user.name, inline=True)
                    embed.add_field(name="Jumlah", value=f"{amount:,} cash", inline=True)
                    
                    view = ConfirmationView(message.author, target_user, amount, 'pay', self)
                    view.message = await message.channel.send(embed=embed, view=view)
                    
                except Exception as e:
                    logger.error(f"Error in pay command: {e}")
                    await message.channel.send("⚠️ Format salah! Gunakan: `<prefix>pay @user <nominal>`")

        # 4. Handle give cash command (Owner only - Spawn money from air)
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
                        description=f"Generate **{amount:,}** cash gratis untuk {target_user.mention}?",
                        color=discord.Color.purple()
                    )
                    view = ConfirmationView(message.author, target_user, amount, 'givecash', self)
                    view.message = await message.channel.send(embed=embed, view=view)
                except:
                    pass

async def setup(bot):
    await bot.add_cog(CoinFlip(bot))
