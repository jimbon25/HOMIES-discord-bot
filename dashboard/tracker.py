"""Activity Tracker - Records server events and activity with async I/O and caching"""
import json
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from utils import safe_save_json

import logging

logger = logging.getLogger(__name__)

class ActivityTracker:
    def __init__(self, data_file: str = "data/stats.json"):
        self.data_file = data_file
        self.cache: Dict[int, dict] = {}  # In-memory cache: {guild_id: data}
        self.cache_dirty: set = set()  # Track which guilds need saving
        self.ensure_data_file()
        self.sync_interval = 300  # Write to disk every 5 minutes
    
    def get_guild_data_file(self, guild_id: int) -> str:
        """Get per-guild data file path"""
        return f"data/stats_guild_{guild_id}.json"
    
    def ensure_data_file(self):
        """Create data directory if it doesn't exist"""
        Path(self.data_file).parent.mkdir(parents=True, exist_ok=True)
    
    def get_default_structure(self):
        """Get default data structure"""
        return {
            "server_id": None,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "members": {
                "total": 0,
                "humans": 0,
                "bots": 0,
                "joined_today": [],
                "left_today": []
            },
            "activity": {
                "total_messages": 0,
                "messages_today": 0,
                "channels_activity": {},
                "top_channels": {}
            },
            "engagement": {
                "total_roles": 0,
                "total_channels": 0,
                "voice_active": 0
            },
            "bot_stats": {
                "latency": 0,
                "uptime_seconds": 0,
                "commands_used": 0
            }
        }
    
    def load_data(self, guild_id: int = None):
        """Load data from cache (or file if not cached) - per-guild"""
        if guild_id:
            # Check cache first
            if guild_id in self.cache:
                return self.cache[guild_id].copy()
            
            data_file = self.get_guild_data_file(guild_id)
            if os.path.exists(data_file):
                try:
                    with open(data_file, 'r') as f:
                        data = json.load(f)
                        self.cache[guild_id] = data  # Cache it
                        return data.copy()
                except Exception as e:
                    logger.error(f"❌ Gagal memuat data statistik untuk guild {guild_id}: {e}")
                    return self.get_default_structure()
        
        return self.get_default_structure()
    
    def save_data(self, data, guild_id: int = None):
        """Save data to cache, mark as dirty for async flush"""
        if guild_id:
            self.cache[guild_id] = data
            self.cache_dirty.add(guild_id)
        else:
            data["last_updated"] = datetime.now().isoformat()
            safe_save_json(data, self.data_file)
    
    async def flush_cache(self):
        """Async flush cache to disk"""
        loop = asyncio.get_event_loop()
        for guild_id in list(self.cache_dirty):
            data = self.cache[guild_id].copy()
            data["last_updated"] = datetime.now().isoformat()
            data_file = self.get_guild_data_file(guild_id)
            
            # Run file write in executor (non-blocking)
            await loop.run_in_executor(
                None,
                self._write_file,
                data_file,
                data
            )
            self.cache_dirty.discard(guild_id)
    
    @staticmethod
    def _write_file(filepath: str, data: dict):
        """Helper to write file - runs in executor"""
        safe_save_json(data, filepath)
    
    def update_server_info(self, guild_id: int, server_id: int, member_count: int, human_count: int, bot_count: int, role_count: int, channel_count: int):
        """Update server info - per-guild"""
        data = self.load_data(guild_id)
        data["server_id"] = server_id
        data["members"]["total"] = member_count
        data["members"]["humans"] = human_count
        data["members"]["bots"] = bot_count
        data["engagement"]["total_roles"] = role_count
        data["engagement"]["total_channels"] = channel_count
        self.save_data(data, guild_id)
    
    def record_message(self, guild_id: int, channel_id: int, channel_name: str, user_id: int = None):
        """Record a message - per-guild"""
        data = self.load_data(guild_id)
        data["activity"]["total_messages"] += 1
        data["activity"]["messages_today"] += 1
        
        # Track per channel
        channel_key = str(channel_id)
        if channel_key not in data["activity"]["channels_activity"]:
            data["activity"]["channels_activity"][channel_key] = {
                "name": channel_name,
                "count": 0
            }
        data["activity"]["channels_activity"][channel_key]["count"] += 1
        
        self.save_data(data, guild_id)
    
    def record_member_join(self, guild_id: int, user_id: int, user_name: str):
        """Record member join - per-guild"""
        data = self.load_data(guild_id)
        data["members"]["joined_today"].append({
            "user_id": user_id,
            "user_name": user_name,
            "timestamp": datetime.now().isoformat()
        })
        self.save_data(data, guild_id)
    
    def record_member_leave(self, guild_id: int, user_id: int, user_name: str):
        """Record member leave - per-guild"""
        data = self.load_data(guild_id)
        data["members"]["left_today"].append({
            "user_id": user_id,
            "user_name": user_name,
            "timestamp": datetime.now().isoformat()
        })
        self.save_data(data, guild_id)
    
    def update_bot_latency(self, guild_id: int, latency: float):
        """Update bot latency - per-guild"""
        data = self.load_data(guild_id)
        data["bot_stats"]["latency"] = round(latency * 1000, 2)
        self.save_data(data, guild_id)
    
    def update_voice_active(self, guild_id: int, count: int):
        """Update active voice channel count - per-guild"""
        data = self.load_data(guild_id)
        data["engagement"]["voice_active"] = count
        self.save_data(data, guild_id)
    
    def reset_daily_stats(self, guild_id: int):
        """Reset daily statistics - per-guild"""
        data = self.load_data(guild_id)
        data["activity"]["messages_today"] = 0
        data["members"]["joined_today"] = []
        data["members"]["left_today"] = []
        self.save_data(data, guild_id)
    
    def load_uptime(self) -> dict:
        """Load uptime data from global file"""
        uptime_file = "data/uptime.json"
        if os.path.exists(uptime_file):
            try:
                with open(uptime_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"❌ Gagal memuat data uptime: {e}")
                return {}
        return {}
    
    def save_uptime(self, uptime_seconds: int):
        """Save uptime to global file"""
        uptime_file = "data/uptime.json"
        
        data = self.load_uptime()
        data["bot_uptime_seconds"] = uptime_seconds
        data["last_updated"] = datetime.now().isoformat()
        
        safe_save_json(data, uptime_file)

# Create global instance
activity_tracker = ActivityTracker()
