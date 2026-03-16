"""Dashboard Cog - Server Health Monitoring"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
import time
from datetime import datetime
from dashboard.tracker import activity_tracker
from dashboard.display import DashboardDisplay

class DashboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracker = activity_tracker
        self.display = DashboardDisplay()
        self.start_time = None
        self.last_reset_date = None
        self.daily_reset.start()
        self.update_uptime.start()
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize dashboard on bot ready"""
        if self.bot.user:
            # Set start time on first ready
            if self.start_time is None:
                self.start_time = datetime.now()
                print(f"Dashboard started at {self.start_time}")
            
            print(f"Dashboard cog loaded for {self.bot.user}")
            # Update server info on startup
            for guild in self.bot.guilds:
                await self.update_guild_stats(guild)
    
    @tasks.loop(hours=1)
    async def daily_reset(self):
        """Reset daily statistics at midnight UTC using date tracking"""
        await self.bot.wait_until_ready()
        
        now = datetime.utcnow()
        today = now.date()
        
        # Only reset once per day
        if self.last_reset_date != today:
            try:
                for guild in self.bot.guilds:
                    self.tracker.reset_daily_stats(guild.id)
                self.last_reset_date = today
                print(f"[Daily Reset] Statistics reset for all servers at {now}")
            except Exception as e:
                print(f"Error in daily reset: {e}")
    
    @tasks.loop(minutes=1)
    async def update_uptime(self):
        """Update bot uptime every minute to global file"""
        await self.bot.wait_until_ready()
        
        if self.start_time:
            try:
                uptime_delta = datetime.now() - self.start_time
                uptime_seconds = int(uptime_delta.total_seconds())
                
                # Save uptime to global file (not per-guild)
                self.tracker.save_uptime(uptime_seconds)
            except Exception as e:
                print(f"Error updating uptime: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Track messages - per-guild"""
        if message.author.bot or not message.guild:
            return
        
        self.tracker.record_message(
            message.guild.id,  # Add guild_id
            message.channel.id,
            message.channel.name if hasattr(message.channel, 'name') else "Unknown"
        )
        
        # Update bot latency - per-guild
        self.tracker.update_bot_latency(message.guild.id, self.bot.latency)
    
    async def update_guild_stats(self, guild: discord.Guild):
        """Update guild statistics"""
        try:
            member_count = guild.member_count or 0
            human_count = sum(1 for m in guild.members if not m.bot)
            bot_count = member_count - human_count
            role_count = len(guild.roles)
            channel_count = len(guild.channels)
            
            self.tracker.update_server_info(
                guild.id,  # guild_id as first parameter
                guild.id,  # server_id
                member_count,
                human_count,
                bot_count,
                role_count,
                channel_count
            )
            
            # Update voice channel count
            voice_count = sum(len(vc.members) for vc in guild.voice_channels)
            self.tracker.update_voice_active(guild.id, voice_count)
        except Exception as e:
            print(f"Error updating guild stats: {e}")
    
    @app_commands.command(name="serverhealth", description="Show main server health dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def serverhealth(self, interaction: discord.Interaction):
        """Display main health dashboard"""
        await interaction.response.defer()
        
        try:
            embed = self.display.create_main_dashboard(interaction.guild)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error loading dashboard: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="members", description="Show detailed members dashboard")
    async def members(self, interaction: discord.Interaction):
        """Display members dashboard"""
        await interaction.response.defer()
        
        try:
            embed = self.display.create_members_dashboard(interaction.guild)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error loading dashboard: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="activity", description="Show activity dashboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def activity(self, interaction: discord.Interaction):
        """Display activity dashboard"""
        await interaction.response.defer()
        
        try:
            embed = self.display.create_activity_dashboard(interaction.guild.id)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error loading dashboard: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="engagement", description="Show engagement dashboard")
    async def engagement(self, interaction: discord.Interaction):
        """Display engagement dashboard"""
        await interaction.response.defer()
        
        try:
            embed = self.display.create_engagement_dashboard(interaction.guild)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error loading dashboard: {str(e)}", ephemeral=True)
    
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="stats", description="Show quick server statistics")
    async def stats(self, interaction: discord.Interaction):
        """Quick statistics"""
        await interaction.response.defer()
        
        try:
            guild_id = interaction.guild.id
            members = self.display.analytics.get_member_stats(guild_id)
            activity = self.display.analytics.get_activity_stats(guild_id)
            bot_stats = self.display.analytics.get_bot_stats(guild_id)
            
            embed = discord.Embed(
                title="📈 Quick Stats",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="Members", value=f"**{members['total']}** total", inline=True)
            embed.add_field(name="Messages", value=f"**{activity['total_messages']}** lifetime", inline=True)
            embed.add_field(name="Latency", value=f"**{bot_stats['latency_ms']}**ms", inline=True)
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    def cog_unload(self):
        """Stop background tasks when cog unloads"""
        self.daily_reset.cancel()
        self.update_uptime.cancel()

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(DashboardCog(bot))
