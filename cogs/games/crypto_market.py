"""Maho-Crypto Market Simulation - Complex trading with market trends and events"""
import discord
from discord.ext import commands, tasks
import random
import json
import os
import time
from pathlib import Path
from utils import safe_save_json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CryptoMarket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.market_file = "data/crypto_market.json"
        self.user_crypto_file = "data/user_crypto.json"
        
        # Initial coin definitions
        self.coins = {
            "maho": {"name": "$MAHO", "volatility": 0.05, "base_price": 50000, "emoji": "🔵"},
            "zen": {"name": "$ZEN", "volatility": 0.15, "base_price": 10000, "emoji": "🟣"},
            "curse": {"name": "$CURSE", "volatility": 0.40, "base_price": 1000, "emoji": "💀"}
        }
        
        self.ensure_files()
        self.market_data = self.load_data(self.market_file)
        self.user_data = self.load_data(self.user_crypto_file)
        
        # Initialize market if empty
        if not self.market_data:
            self.init_market()
            
        self.update_market.start()

    def ensure_files(self):
        Path("data").mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.market_file):
            safe_save_json({}, self.market_file)
        if not os.path.exists(self.user_crypto_file):
            safe_save_json({}, self.user_crypto_file)

    def load_data(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except:
            return {}

    def init_market(self):
        self.market_data = {
            "sentiment": "neutral",
            "sentiment_expiry": int(time.time()) + 14400, # 4 hours
            "last_update": int(time.time()),
            "prices": {k: v["base_price"] for k, v in self.coins.items()},
            "history": {k: [v["base_price"]] for k, v in self.coins.items()},
            "news": "Market is opening. Trade wisely."
        }
        safe_save_json(self.market_data, self.market_file)

    @tasks.loop(minutes=60)
    async def update_market(self):
        """Background task to update crypto prices every hour"""
        now = int(time.time())
        
        # Update Sentiment if expired
        if now >= self.market_data.get("sentiment_expiry", 0):
            sentiments = ["bullish", "bearish", "neutral", "volatile"]
            self.market_data["sentiment"] = random.choice(sentiments)
            self.market_data["sentiment_expiry"] = now + random.randint(7200, 21600) # 2-6 hours
            
        # Random News Event (20% chance)
        event_impact = {k: 0 for k in self.coins}
        self.market_data["news"] = "Market is stable."
        
        if random.random() < 0.20:
            events = [
                ("Whale Buyback! $MAHO pumps.", "maho", 0.15),
                ("FUD! $CURSE is being investigated.", "curse", -0.30),
                ("Global adoption! All coins moon.", "all", 0.10),
                ("Exchange hack! All coins crash.", "all", -0.20),
                ("Tech update! $ZEN price surges.", "zen", 0.20)
            ]
            msg, target, impact = random.choice(events)
            self.market_data["news"] = msg
            if target == "all":
                for k in event_impact: event_impact[k] = impact
            else:
                event_impact[target] = impact

        # Calculate New Prices
        sentiment = self.market_data["sentiment"]
        for key, coin in self.coins.items():
            current_price = self.market_data["prices"][key]
            
            # Base volatility
            vol = coin["volatility"]
            change = random.uniform(-vol, vol)
            
            # Apply Sentiment
            if sentiment == "bullish": change += random.uniform(0, 0.05)
            elif sentiment == "bearish": change -= random.uniform(0, 0.05)
            elif sentiment == "volatile": change *= 2
            
            # Apply News Impact
            change += event_impact[key]
            
            new_price = int(current_price * (1 + change))
            if new_price < 10: new_price = 10 # Minimum price
            
            self.market_data["prices"][key] = new_price
            
            # Update History (keep last 10 points)
            history = self.market_data["history"].get(key, [])
            history.append(new_price)
            if len(history) > 10: history.pop(0)
            self.market_data["history"][key] = history

        self.market_data["last_update"] = now
        safe_save_json(self.market_data, self.market_file)
        logger.info(f"✅ Crypto Market Updated: Sentiment={sentiment}")

    @update_market.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

    def get_user_crypto(self, user_id):
        user_id = str(user_id)
        if user_id not in self.user_data:
            self.user_data[user_id] = {k: {"amount": 0.0, "avg_price": 0} for k in self.coins}
            safe_save_json(self.user_data, self.user_crypto_file)
        return self.user_data[user_id]

    def save_user_data(self):
        safe_save_json(self.user_data, self.user_crypto_file)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog: return
        
        current_prefix = economy_cog.get_guild_prefix(str(message.guild.id))
        content = message.content.lower().strip()
        user_id = str(message.author.id)

        # 1. Market Dashboard
        if content == f"{current_prefix}crypto" or content == f"{current_prefix}market":
            sentiment_emoji = {"bullish": "📈 Bullish", "bearish": "📉 Bearish", "neutral": "⚖️ Neutral", "volatile": "🌪️ Volatile"}
            
            embed = discord.Embed(
                title="📊 Maho-Crypto Exchange",
                description=f"Market Sentiment: **{sentiment_emoji.get(self.market_data['sentiment'], 'Neutral')}**\n"
                            f"📰 News: *{self.market_data['news']}*",
                color=discord.Color.dark_blue()
            )
            
            for key, coin in self.coins.items():
                price = self.market_data["prices"][key]
                history = self.market_data["history"][key]
                last_price = history[-2] if len(history) > 1 else price
                change_pct = ((price - last_price) / last_price) * 100 if last_price > 0 else 0
                
                trend = "🟢" if change_pct >= 0 else "🔴"
                embed.add_field(
                    name=f"{coin['emoji']} {coin['name']}",
                    value=f"Price: **{price:,}** MC\n24h: {trend} `{change_pct:+.2f}%`",
                    inline=True
                )
            
            next_update = 60 - (int(time.time() - self.market_data["last_update"]) // 60)
            embed.set_footer(text=f"Next price update in ~{next_update} minutes")
            await message.channel.send(embed=embed)

        # 2. Portfolio
        elif content == f"{current_prefix}pf" or content == f"{current_prefix}portfolio":
            crypto = self.get_user_crypto(user_id)
            total_value = 0
            desc = ""
            
            for key, coin in self.coins.items():
                amount = crypto[key]["amount"]
                if amount > 0:
                    current_p = self.market_data["prices"][key]
                    val = int(amount * current_p)
                    total_value += val
                    avg = crypto[key]["avg_price"]
                    profit = val - int(amount * avg)
                    trend = "📈" if profit >= 0 else "📉"
                    
                    desc += f"{coin['emoji']} **{coin['name']}**: {amount:.4f}\n"
                    desc += f"Value: `{val:,} MC` | PNL: {trend} `{profit:,} MC`\n\n"
            
            embed = discord.Embed(
                title=f"💼 {message.author.name}'s Portfolio",
                description=desc if desc else "You don't own any crypto yet.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Total Net Worth (Crypto)", value=f"💶 **{total_value:,} Mahocoin**", inline=False)
            await message.channel.send(embed=embed)

        # 3. Buy Command: <prefix>buy <coin> <amount_in_mc/all>
        elif content.startswith(f"{current_prefix}buy "):
            parts = content.split()
            if len(parts) < 3:
                await message.channel.send(f"⚠️ Usage: `{current_prefix}buy <maho/zen/curse> <amount_in_mc/all>`")
                return
            
            coin_key = parts[1]
            if coin_key not in self.coins:
                await message.channel.send("❌ Invalid coin! Choose: `maho`, `zen`, or `curse`.")
                return
            
            balance = economy_cog.get_user_balance(user_id)
            if parts[2] == "all":
                spend_amount = balance
            else:
                try:
                    spend_amount = int(parts[2].replace(".", "").replace(",", ""))
                except:
                    await message.channel.send("❌ Invalid amount!")
                    return
            
            if spend_amount <= 0 or spend_amount > balance:
                await message.channel.send("❌ Insufficient or invalid balance!")
                return
            
            # Trading Fee (1%)
            fee = int(spend_amount * 0.01)
            net_spend = spend_amount - fee
            
            # Calculate coin amount
            price = self.market_data["prices"][coin_key]
            coin_amount = net_spend / price
            
            # Update user crypto
            crypto = self.get_user_crypto(user_id)
            old_amount = crypto[coin_key]["amount"]
            old_avg = crypto[coin_key]["avg_price"]
            
            new_amount = old_amount + coin_amount
            new_avg = ((old_amount * old_avg) + (coin_amount * price)) / new_amount
            
            crypto[coin_key]["amount"] = new_amount
            crypto[coin_key]["avg_price"] = int(new_avg)
            
            # Execute economy transactions
            economy_cog.update_balance(user_id, -spend_amount)
            economy_cog.update_server_tax(str(message.guild.id), fee)
            self.save_user_data()
            
            await message.channel.send(
                f"✅ **Purchase Successful!**\n"
                f"Bought **{coin_amount:.4f} {self.coins[coin_key]['name']}** for **{spend_amount:,} MC**.\n"
                f"*(Fee: {fee:,} MC sent to server vault)*"
            )

        # 4. Sell Command: <prefix>sell <coin> <amount_in_crypto/all>
        elif content.startswith(f"{current_prefix}sell "):
            parts = content.split()
            if len(parts) < 3:
                await message.channel.send(f"⚠️ Usage: `{current_prefix}sell <maho/zen/curse> <amount_of_coin/all>`")
                return
            
            coin_key = parts[1]
            if coin_key not in self.coins:
                await message.channel.send("❌ Invalid coin!")
                return
            
            crypto = self.get_user_crypto(user_id)
            owned_amount = crypto[coin_key]["amount"]
            
            if owned_amount <= 0:
                await message.channel.send("❌ You don't own this coin!")
                return
                
            if parts[2] == "all":
                sell_amount = owned_amount
            else:
                try:
                    sell_amount = float(parts[2].replace(",", "."))
                except:
                    await message.channel.send("❌ Invalid amount!")
                    return
            
            if sell_amount <= 0 or sell_amount > owned_amount:
                await message.channel.send(f"❌ You only own {owned_amount:.4f} {self.coins[coin_key]['name']}!")
                return
            
            # Calculate value
            price = self.market_data["prices"][coin_key]
            gross_receive = int(sell_amount * price)
            
            # Trading Fee (1%)
            fee = int(gross_receive * 0.01)
            net_receive = gross_receive - fee
            
            # Update user crypto
            crypto[coin_key]["amount"] -= sell_amount
            
            # Execute economy transactions
            economy_cog.update_balance(user_id, net_receive)
            economy_cog.update_server_tax(str(message.guild.id), fee)
            self.save_user_data()
            
            await message.channel.send(
                f"✅ **Sale Successful!**\n"
                f"Sold **{sell_amount:.4f} {self.coins[coin_key]['name']}** for **{net_receive:,} MC**.\n"
                f"*(Fee: {fee:,} MC sent to server vault)*"
            )

async def setup(bot):
    await bot.add_cog(CryptoMarket(bot))
    logger.info("✅ CryptoMarket cog loaded")
