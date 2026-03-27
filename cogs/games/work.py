"""Work and Mystery Box Commands"""
import discord
from discord.ext import commands
import random
import time
import logging

logger = logging.getLogger(__name__)

class Work(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Volatile cooldowns (reset on bot restart)
        self.work_cooldowns = {}

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

        # Handle work command
        if content == f"{current_prefix}work":
            # Cooldown check (5 seconds)
            current_time = time.time()
            last_work = self.work_cooldowns.get(user_id, 0)
            if current_time - last_work < 5:
                remaining = int(5 - (current_time - last_work))
                await message.channel.send(f"👷 **{message.author.display_name}**, you're tired! Rest for **{remaining} seconds**.", delete_after=5)
                return

            self.work_cooldowns[user_id] = current_time
            reward = random.randint(100, 1000)
            jobs = ["Helper", "Vendor", "Worker", "Welder", "Driver", "Penjual Seblak", "Penjaga Toko", "Petani", "Pekerja Pabrik", "Kurir", "Barista", "Kasir", "Tukang Kebun", "Pembersih", "Pekerja Konstruksi", "Penjaga Keamanan", "Pekerja Restoran", "Pekerja Gudang", "Pekerja Bangunan", "Pekerja Pembersih", "Pekerja Toko", "Pekerja Kafe", "Pekerja Supermarket", "Pekerja Mall", "Pekerja Pasar", "Pekerja Pabrik", "Pekerja Pertanian", "Pekerja Perikanan", "Pekerja Peternakan", "Pekerja Transportasi", "Pekerja Logistik"]
            job = random.choice(jobs)
            economy_cog.update_balance(user_id, reward)

            # Rare Mystery Box drop from work (5% chance)
            user_data = economy_cog.get_user_data(user_id)
            drop_box = random.random() < 0.05
            if drop_box:
                user_data["box_boxes"] = user_data.get("box_boxes", 0) + 1
                economy_cog.economy[user_id] = user_data
                economy_cog.save_economy()
                await message.channel.send(f"👷 **{message.author.display_name}**, you worked as a **{job}** and were paid 💶 **{reward:,}** mahocoin!\n🎁 Lucky drop! You found a mystery box. Use `{current_prefix}box open` to open it.")
            else:
                await message.channel.send(f"👷 **{message.author.display_name}**, you worked as a **{job}** and were paid 💶 **{reward:,}** mahocoin!")

        # Handle box open command
        elif content == f"{current_prefix}box open":
            user_data = economy_cog.get_user_data(user_id)
            boxes = user_data.get("box_boxes", 0)
            if boxes <= 0:
                await message.channel.send(f"📦 {message.author.mention}, you have no mystery boxes. Try `{current_prefix}work` for a rare drop!")
                return

            # Consume one box
            user_data["box_boxes"] = boxes - 1
            economy_cog.economy[user_id] = user_data
            economy_cog.save_economy()

            # Determine reward rarity
            roll = random.randint(1, 100)
            if roll <= 80:
                rarity = "Common"
                prize = random.randint(100, 300)
            elif roll <= 95:
                rarity = "Uncommon"
                prize = random.randint(400, 700)
            elif roll <= 99:
                rarity = "Rare"
                prize = random.randint(800, 1200)
            else:
                rarity = "Legendary"
                prize = random.randint(1500, 3000)

            economy_cog.update_balance(user_id, prize)
            await message.channel.send(f"📦 {message.author.mention}, you opened a mystery box! Rarity: **{rarity}** and got 💶 **{prize:,}** mahocoin!")

        elif content == f"{current_prefix}box":
            user_data = economy_cog.get_user_data(user_id)
            boxes = user_data.get("box_boxes", 0)
            await message.channel.send(f"📦 {message.author.mention}, you have **{boxes}** mystery box(es). Use `{current_prefix}box open` to open.")

async def setup(bot):
    await bot.add_cog(Work(bot))
    logger.info("✅ Work cog loaded")
