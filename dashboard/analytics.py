"""Analytics Engine - Compute metrics and insights"""
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

class Analytics:
    def __init__(self, data_file: str = "data/stats.json"):
        self.data_file = data_file
    
    def get_guild_data_file(self, guild_id: int) -> str:
        """Get per-guild data file path"""
        return f"data/stats_guild_{guild_id}.json"
    
    def load_data(self, guild_id: int = None) -> Dict:
        """Load data from JSON - per-guild if guild_id provided"""
        if guild_id:
            data_file = self.get_guild_data_file(guild_id)
        else:
            data_file = self.data_file
        
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def get_member_stats(self, guild_id: int = None) -> Dict:
        """Get member statistics - per-guild"""
        data = self.load_data(guild_id)
        members = data.get("members", {})
        
        return {
            "total": members.get("total", 0),
            "humans": members.get("humans", 0),
            "bots": members.get("bots", 0),
            "joined_today": len(members.get("joined_today", [])),
            "left_today": len(members.get("left_today", []))
        }
    
    def get_activity_stats(self, guild_id: int = None) -> Dict:
        """Get activity statistics - per-guild"""
        data = self.load_data(guild_id)
        activity = data.get("activity", {})
        channels = activity.get("channels_activity", {})
        
        # Get top channels
        sorted_channels = sorted(
            channels.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True
        )[:5]  # Top 5
        
        top_channels = {k: v for k, v in sorted_channels}
        
        return {
            "total_messages": activity.get("total_messages", 0),
            "messages_today": activity.get("messages_today", 0),
            "top_channels": top_channels,
            "channel_count": len(channels)
        }
    
    def get_engagement_stats(self, guild_id: int = None) -> Dict:
        """Get engagement statistics - per-guild"""
        data = self.load_data(guild_id)
        engagement = data.get("engagement", {})
        
        return {
            "total_roles": engagement.get("total_roles", 0),
            "total_channels": engagement.get("total_channels", 0),
            "voice_active": engagement.get("voice_active", 0)
        }
    
    def get_bot_stats(self, guild_id: int = None) -> Dict:
        """Get bot statistics - per-guild (uptime from global file)"""
        data = self.load_data(guild_id)
        bot_stats = data.get("bot_stats", {})
        
        # Load uptime from global file
        uptime_seconds = self._load_global_uptime()
        
        return {
            "latency_ms": bot_stats.get("latency", 0),
            "uptime_seconds": uptime_seconds,
            "commands_used": bot_stats.get("commands_used", 0)
        }
    
    def _load_global_uptime(self) -> int:
        """Load uptime from global uptime.json file"""
        uptime_file = "data/uptime.json"
        if os.path.exists(uptime_file):
            try:
                with open(uptime_file, 'r') as f:
                    data = json.load(f)
                    return data.get("bot_uptime_seconds", 0)
            except:
                return 0
        return 0
    
    def get_recent_joins(self, guild_id: int = None, limit: int = 5) -> List[Dict]:
        """Get recent member joins - per-guild"""
        data = self.load_data(guild_id)
        members = data.get("members", {})
        joins = members.get("joined_today", [])
        return joins[-limit:][::-1]  # Last N, most recent first
    
    def get_health_score(self, guild_id: int = None) -> Tuple[int, str]:
        """Calculate server health score (0-100) - per-guild"""
        members = self.get_member_stats(guild_id)
        activity = self.get_activity_stats(guild_id)
        
        score = 50  # Base score
        
        # Member health
        if members["total"] > 10:
            score += 10
        if members["humans"] > members["bots"]:
            score += 10
        
        # Activity health
        if activity["messages_today"] > 0:
            score += 10
        if activity["total_messages"] > 100:
            score += 10
        if activity["channel_count"] > 3:
            score += 10
        
        # Determine status
        if score >= 80:
            status = "🟢 Excellent"
        elif score >= 60:
            status = "🟡 Good"
        elif score >= 40:
            status = "🟠 Fair"
        else:
            status = "🔴 Poor"
        
        return min(score, 100), status
    
    def get_uptime_formatted(self) -> str:
        """Get formatted uptime"""
        stats = self.get_bot_stats()
        seconds = stats["uptime_seconds"]
        
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
