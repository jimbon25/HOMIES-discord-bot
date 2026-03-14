import discord
from discord.ext import commands
from datetime import datetime

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Dictionary untuk menyimpan AFK status: {user_id: {"reason": reason, "timestamp": datetime}}
        self.afk_users = {}

    def get_time_difference(self, timestamp):
        """Menghitung selisih waktu dan format jadi 'X minutes ago' atau 'X hours ago'"""
        now = datetime.now()
        diff = now - timestamp
        
        seconds = diff.total_seconds()
        minutes = int(seconds // 60)
        hours = int(minutes // 60)
        days = int(hours // 24)
        
        if minutes < 1:
            return "Just now"
        elif minutes < 60:
            return f"A {minutes} minute{'s' if minutes > 1 else ''} ago"
        elif hours < 24:
            return f"A {hours} hour{'s' if hours > 1 else ''} ago"
        else:
            return f"A {days} day{'s' if days > 1 else ''} ago"

    @commands.command(name="afk")
    async def set_afk(self, ctx, *, reason: str = "No reason provided"):
        """Set AFK status dengan alasan."""
        user_id = ctx.author.id
        self.afk_users[user_id] = {
            "reason": reason,
            "timestamp": datetime.now()
        }
        
        await ctx.send(f"<@{ctx.author.id}> | I set you AFK : {reason}")

    @commands.command(name="back")
    async def remove_afk(self, ctx):
        """Remove AFK status."""
        user_id = ctx.author.id
        if user_id in self.afk_users:
            del self.afk_users[user_id]
            await ctx.send(f"Welcome back {ctx.author.name}! AFK status removed.")
        else:
            await ctx.send(f"{ctx.author.name} was not AFK.")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Abaikan pesan dari bot
        if message.author.bot:
            return

        # Jika user yang mengirim adalah user yang AFK, remove AFK status dan notify
        # TAPI ignore jika ini adalah command (pesan dimulai dengan prefix)
        if message.author.id in self.afk_users:
            if not message.content.startswith(self.bot.command_prefix):
                del self.afk_users[message.author.id]
                await message.channel.send(f"Welcome back <@{message.author.id}>! AFK status removed.", delete_after=5)
            return

        # Cek apakah user yang mention adalah AFK
        if message.mentions:
            for mentioned_user in message.mentions:
                if mentioned_user.id in self.afk_users:
                    afk_data = self.afk_users[mentioned_user.id]
                    reason = afk_data["reason"]
                    timestamp = afk_data["timestamp"]
                    time_ago = self.get_time_difference(timestamp)
                    
                    embed = discord.Embed(
                        description=f"{mentioned_user.name} is AFK : {reason} | Since {time_ago}",
                        color=discord.Color.greyple()
                    )
                    
                    await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AFK(bot))

