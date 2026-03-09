"""Display Engine - Create embeds for dashboard"""
import discord
from datetime import datetime
from .analytics import Analytics

class DashboardDisplay:
    def __init__(self, data_file: str = "data/stats.json"):
        self.analytics = Analytics(data_file)
    
    def create_main_dashboard(self, guild: discord.Guild) -> discord.Embed:
        """Create main dashboard embed - per-guild"""
        guild_id = guild.id
        members = self.analytics.get_member_stats(guild_id)
        activity = self.analytics.get_activity_stats(guild_id)
        engagement = self.analytics.get_engagement_stats(guild_id)
        bot_stats = self.analytics.get_bot_stats(guild_id)
        health_score, health_status = self.analytics.get_health_score(guild_id)
        
        embed = discord.Embed(
            title="📊 Server Health Dashboard",
            description=f"Server: **{guild.name}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Health Status
        embed.add_field(
            name="Server Health",
            value=f"{health_status}\nScore: {health_score}/100",
            inline=True
        )
        
        # Member Stats
        embed.add_field(
            name="👥 Members",
            value=f"Total: **{members['total']}**\nHumans: {members['humans']} | Bots: {members['bots']}\nJoined Today: +{members['joined_today']} | Left: -{members['left_today']}",
            inline=True
        )
        
        # Activity Stats
        embed.add_field(
            name="💬 Activity",
            value=f"Total Messages: **{activity['total_messages']}**\nToday: {activity['messages_today']}\nActive Channels: {activity['channel_count']}",
            inline=True
        )
        
        # Engagement
        embed.add_field(
            name="🎯 Engagement",
            value=f"Roles: {engagement['total_roles']}\nChannels: {engagement['total_channels']}\nVoice Active: {engagement['voice_active']}",
            inline=True
        )
        
        # Bot Stats
        embed.add_field(
            name="🤖 Bot Status",
            value=f"Latency: {bot_stats['latency_ms']}ms\nUptime: {self.analytics.get_uptime_formatted()}",
            inline=True
        )
        
        embed.set_footer(text="Data updates in real-time")
        return embed
    
    def create_members_dashboard(self, guild: discord.Guild) -> discord.Embed:
        """Create detailed members dashboard - per-guild"""
        guild_id = guild.id
        members = self.analytics.get_member_stats(guild_id)
        recent_joins = self.analytics.get_recent_joins(guild_id, 5)
        
        embed = discord.Embed(
            title="👥 Members Dashboard",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        # Overview
        embed.add_field(
            name="Overview",
            value=f"Total: **{members['total']}** members\nHumans: {members['humans']} ({self._percentage(members['humans'], members['total'])}%)\nBots: {members['bots']} ({self._percentage(members['bots'], members['total'])}%)",
            inline=False
        )
        
        # Today's activity
        embed.add_field(
            name="Today's Activity",
            value=f"Joined: +{members['joined_today']}\nLeft: -{members['left_today']}",
            inline=True
        )
        
        # Recent joins
        if recent_joins:
            joins_text = "\n".join([f"• {j['user_name']}" for j in recent_joins])
            embed.add_field(
                name="Recent Joins",
                value=joins_text,
                inline=False
            )
        else:
            embed.add_field(
                name="Recent Joins",
                value="No joins recorded today",
                inline=False
            )
        
        embed.set_footer(text="Use /serverhealth for main dashboard")
        return embed
    
    def create_activity_dashboard(self, guild_id: int = None) -> discord.Embed:
        """Create activity dashboard - per-guild"""
        activity = self.analytics.get_activity_stats(guild_id)
        
        embed = discord.Embed(
            title="💬 Activity Dashboard",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        # Overall activity
        embed.add_field(
            name="Message Statistics",
            value=f"Total: **{activity['total_messages']}**\nToday: {activity['messages_today']}\nActive Channels: {activity['channel_count']}",
            inline=False
        )
        
        # Top channels
        if activity['top_channels']:
            top_text = ""
            for i, (channel_id, data) in enumerate(activity['top_channels'].items(), 1):
                top_text += f"{i}. {data['name']}: **{data['count']}** messages\n"
            embed.add_field(
                name="🏆 Top Channels",
                value=top_text.strip(),
                inline=False
            )
        
        embed.set_footer(text="Updated in real-time")
        return embed
    
    def create_engagement_dashboard(self, guild: discord.Guild) -> discord.Embed:
        """Create engagement dashboard - per-guild"""
        guild_id = guild.id
        engagement = self.analytics.get_engagement_stats(guild_id)
        
        embed = discord.Embed(
            title="🎯 Engagement Dashboard",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Guild Structure",
            value=f"Roles: **{engagement['total_roles']}**\nChannels: **{engagement['total_channels']}**\nVoice Active: **{engagement['voice_active']}** users",
            inline=False
        )
        
        embed.add_field(
            name="Server Info",
            value=f"Owner: {guild.owner.mention if guild.owner else 'Unknown'}\nCreated: {guild.created_at.strftime('%Y-%m-%d')}",
            inline=False
        )
        
        embed.set_footer(text="Server engagement metrics")
        return embed
    
    def _percentage(self, part: int, total: int) -> int:
        """Calculate percentage"""
        if total == 0:
            return 0
        return round((part / total) * 100)
