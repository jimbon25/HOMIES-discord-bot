"""Mahoraga Central Bank (MCB) - Tiered Savings and Term Deposits"""
import discord
from discord.ext import commands, tasks
import json
import os
import time
from pathlib import Path
from utils import safe_save_json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class MahoragaBank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bank_file = "data/bank_data.json"
        
        # Banking Plans
        # plan_id: {name, duration_days, interest_rate_daily, penalty_rate}
        self.plans = {
            "0": {"name": "Standard Savings", "days": 0, "rate": 0.001, "penalty": 0.0},
            "1": {"name": "Starter Deposit", "days": 3, "rate": 0.005, "penalty": 0.05},
            "2": {"name": "Elite Deposit", "days": 7, "rate": 0.012, "penalty": 0.10},
            "3": {"name": "Whale Deposit", "days": 30, "rate": 0.025, "penalty": 0.20}
        }
        
        self.ensure_files()
        self.bank_data = self.load_data()
        self.daily_interest_task.start()

    def ensure_files(self):
        Path("data").mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.bank_file):
            safe_save_json({}, self.bank_file)

    def load_data(self):
        try:
            with open(self.bank_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def save_data(self):
        safe_save_json(self.bank_data, self.bank_file)

    def get_user_bank(self, user_id):
        user_id = str(user_id)
        if user_id not in self.bank_data:
            self.bank_data[user_id] = {
                "savings_balance": 0,
                "deposits": [],
                "last_interest_payout": int(time.time())
            }
            self.save_data()
        return self.bank_data[user_id]

    @tasks.loop(minutes=1)
    async def daily_interest_task(self):
        """Check if it's 15:00 WIB (08:00 UTC) and process interest"""
        now = datetime.now(timezone.utc)
        if now.hour == 8 and now.minute == 0:
            logger.info("🏛️ MCB: Processing daily interest payouts...")
            self.process_all_interest()

    @daily_interest_task.before_loop
    async def before_daily_interest(self):
        await self.bot.wait_until_ready()

    def process_all_interest(self):
        """Logic to calculate and add interest for every user"""
        for user_id, data in self.bank_data.items():
            total_interest = 0
            
            # 1. Savings Interest
            savings = data.get("savings_balance", 0)
            if savings > 0:
                interest = int(savings * self.plans["0"]["rate"])
                data["savings_balance"] += interest
                total_interest += interest
            
            # 2. Term Deposits Interest & Maturity
            active_deposits = []
            now_ts = int(time.time())
            
            for dep in data.get("deposits", []):
                # Calculate daily interest for this deposit
                daily_gain = int(dep["amount"] * dep["interest_rate"])
                
                if now_ts >= dep["maturity_date"]:
                    # Deposit Matured! Move to savings
                    final_amount = dep["amount"] + daily_gain
                    data["savings_balance"] += final_amount
                    total_interest += daily_gain
                    # Note: in a real system, we'd notify the user
                else:
                    # Still locked, keep adding interest to the principal (compound)
                    dep["amount"] += daily_gain
                    active_deposits.append(dep)
                    total_interest += daily_gain
            
            data["deposits"] = active_deposits
            data["last_interest_payout"] = now_ts
            
        self.save_data()
        logger.info("🏛️ MCB: Interest processing complete.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog: return
        
        current_prefix = economy_cog.get_guild_prefix(str(message.guild.id))
        content = message.content.lower().strip()
        user_id = str(message.author.id)

        # 1. Bank Dashboard
        if content == f"{current_prefix}bank":
            data = self.get_user_bank(user_id)
            savings = data["savings_balance"]
            
            embed = discord.Embed(
                title="🏛️ Mahoraga Central Bank",
                description=f"Welcome back, {message.author.mention}. Secure your assets here.",
                color=discord.Color.gold()
            )
            embed.add_field(name="💰 Savings (Liquid)", value=f"```💶 {savings:,} MC```", inline=False)
            
            deps_text = ""
            for i, dep in enumerate(data["deposits"]):
                m_date = datetime.fromtimestamp(dep['maturity_date']).strftime('%Y-%m-%d')
                deps_text += f"**#{i+1}** | `{dep['amount']:,} MC` | Ends: `{m_date}`\n"
            
            if not deps_text: deps_text = "No active term deposits."
            embed.add_field(name="🔒 Term Deposits (Locked)", value=deps_text, inline=False)
            
            rates_text = ""
            for k, v in self.plans.items():
                rates_text += f"**Plan {k}**: {v['name']} ({v['rate']*100:.1f}% Daily)\n"
            embed.add_field(name="📈 Current Rates", value=rates_text, inline=False)
            
            embed.set_footer(text=f"Use {current_prefix}dep <amount> [plan_id] to save money.")
            await message.channel.send(embed=embed)

        # 2. Deposit Command
        elif content.startswith(f"{current_prefix}dep "):
            parts = content.split()
            if len(parts) < 2:
                await message.channel.send(f"⚠️ Usage: `{current_prefix}dep <amount/all> [plan_id (1-3)]`")
                return
            
            # Parse Amount
            balance = economy_cog.get_user_balance(user_id)
            if parts[1] == "all":
                amount = balance
            else:
                try:
                    amount = int(parts[1].replace(".", "").replace(",", ""))
                except:
                    await message.channel.send("❌ Invalid amount!")
                    return
            
            if amount <= 0 or amount > balance:
                await message.channel.send("❌ Insufficient or invalid amount!")
                return
            
            # Parse Plan
            plan_id = "0"
            if len(parts) >= 3:
                if parts[2] in ["1", "2", "3"]:
                    plan_id = parts[2]
                else:
                    await message.channel.send("❌ Invalid Plan ID! Use 1, 2, or 3 for deposits.")
                    return
            
            # Execute Deposit
            bank_data = self.get_user_bank(user_id)
            economy_cog.update_balance(user_id, -amount)
            
            if plan_id == "0":
                bank_data["savings_balance"] += amount
                await message.channel.send(f"✅ Successfully deposited **{amount:,} MC** into your Savings account.")
            else:
                plan = self.plans[plan_id]
                new_dep = {
                    "amount": amount,
                    "plan_id": plan_id,
                    "interest_rate": plan["rate"],
                    "start_date": int(time.time()),
                    "maturity_date": int(time.time()) + (plan["days"] * 86400)
                }
                bank_data["deposits"].append(new_dep)
                m_date = datetime.fromtimestamp(new_dep['maturity_date']).strftime('%Y-%m-%d %H:%M')
                await message.channel.send(
                    f"✅ **{plan['name']} Opened!**\n"
                    f"Principal: `{amount:,} MC`\n"
                    f"Maturity Date: `{m_date} WIB`\n"
                    f"*Note: Early withdrawal will incur a {int(plan['penalty']*100)}% penalty.*"
                )
            
            self.save_data()

        # 3. Withdraw Command
        elif content.startswith(f"{current_prefix}wit "):
            parts = content.split()
            if len(parts) < 2:
                await message.channel.send(f"⚠️ Usage: `{current_prefix}wit <amount/all> [deposit_index]`")
                return
            
            bank_data = self.get_user_bank(user_id)
            
            # Option A: Withdraw from Savings (No Index)
            if len(parts) == 2:
                savings = bank_data["savings_balance"]
                if parts[1] == "all":
                    amount = savings
                else:
                    try:
                        amount = int(parts[1].replace(".", "").replace(",", ""))
                    except:
                        await message.channel.send("❌ Invalid amount!")
                        return
                
                if amount <= 0 or amount > savings:
                    await message.channel.send(f"❌ Insufficient savings! (Balance: {savings:,} MC)")
                    return
                
                bank_data["savings_balance"] -= amount
                economy_cog.update_balance(user_id, amount)
                self.save_data()
                await message.channel.send(f"✅ Withdrew **{amount:,} MC** from your Savings.")
                
            # Option B: Early Withdrawal from Term Deposit (With Index)
            else:
                try:
                    idx = int(parts[2]) - 1
                    if idx < 0 or idx >= len(bank_data["deposits"]):
                        raise ValueError()
                except:
                    await message.channel.send("❌ Invalid deposit index!")
                    return
                
                dep = bank_data["deposits"].pop(idx)
                now_ts = int(time.time())
                
                if now_ts >= dep["maturity_date"]:
                    # No penalty (though normally these move to savings automatically at 15:00)
                    receive = dep["amount"]
                    msg = f"✅ Withdrew matured deposit: **{receive:,} MC**."
                else:
                    # Apply Penalty
                    plan = self.plans[dep["plan_id"]]
                    penalty = int(dep["amount"] * plan["penalty"])
                    receive = dep["amount"] - penalty
                    msg = f"⚠️ **Early Withdrawal!**\nPenalty: `-{penalty:,} MC` ({int(plan['penalty']*100)}%)\nReceived: **{receive:,} MC**."
                
                economy_cog.update_balance(user_id, receive)
                self.save_data()
                await message.channel.send(msg)

        # 4. Admin Only: Force Interest (for testing)
        elif content == f"{current_prefix}forceinterest":
            if message.author.guild_permissions.administrator:
                self.process_all_interest()
                await message.channel.send("🏛️ **MCB Notice:** Daily interest has been manually processed.")

async def setup(bot):
    await bot.add_cog(MahoragaBank(bot))
    logger.info("✅ MahoragaBank cog loaded")
