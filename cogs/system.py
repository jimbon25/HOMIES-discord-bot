"""System Monitor Cog - Monitor bot's system resources"""
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import psutil
import platform
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OWNER_ID = int(os.getenv('OWNER_ID', 0)) if os.getenv('OWNER_ID') else None


class SystemMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def get_cpu_usage_blocking(self) -> float:
        """Get CPU usage percentage (blocking call - use with executor)"""
        return psutil.cpu_percent(interval=0.1)  # Reduced from 1s to 0.1s for speed
    
    async def get_cpu_usage(self) -> float:
        """Get CPU usage percentage (async, non-blocking)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_cpu_usage_blocking)
    
    def get_ram_usage(self) -> dict:
        """Get RAM usage statistics"""
        ram = psutil.virtual_memory()
        used_gb = ram.used / (1024 ** 3)
        total_gb = ram.total / (1024 ** 3)
        percent = ram.percent
        
        return {
            "used_gb": round(used_gb, 2),
            "total_gb": round(total_gb, 2),
            "percent": percent
        }
    
    def get_disk_usage(self) -> dict:
        """Get disk usage statistics"""
        disk = psutil.disk_usage('/')
        free_gb = disk.free / (1024 ** 3)
        total_gb = disk.total / (1024 ** 3)
        percent = disk.percent
        
        return {
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "percent": percent
        }
    
    def get_system_uptime(self) -> str:
        """Get system uptime formatted"""
        uptime_seconds = int(datetime.now().timestamp() - psutil.boot_time())
        
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def get_cpu_temperature(self) -> str:
        """Get CPU temperature if available"""
        try:
            temps = psutil.sensors_temperatures()
            
            # Try common temperature sensor names (Linux)
            if 'coretemp' in temps:  # Intel
                temp = temps['coretemp'][0].current
                return f"{temp}°C"
            elif 'k10temp' in temps:  # AMD
                temp = temps['k10temp'][0].current
                return f"{temp}°C"
            elif 'it8792' in temps:  # Other
                temp = temps['it8792'][0].current
                return f"{temp}°C"
            
            # Fallback: try first available sensor
            for sensor_name, entries in temps.items():
                if entries:
                    temp = entries[0].current
                    return f"{temp}°C"
            
            return "Not available"
        except:
            return "Not available"
    
    def get_os_info(self) -> dict:
        """Get OS information"""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor() or "Unknown"
        }
    
    def get_cpu_count(self) -> dict:
        """Get CPU core information"""
        return {
            "physical": psutil.cpu_count(logical=False),
            "logical": psutil.cpu_count(logical=True)
        }
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is bot owner"""
        if OWNER_ID is None:
            # If OWNER_ID not set, fallback to bot owner
            return user_id == self.bot.owner_id
        return user_id == OWNER_ID
    
    @app_commands.command(name="system", description="Show system resource information")
    @app_commands.checks.has_permissions(administrator=True)
    async def system_info(self, interaction: discord.Interaction):
        """Display system information - Owner only"""
        # Check if user is bot owner
        if not self.is_owner(interaction.user.id):
            embed = discord.Embed(
                title="Access Denied",
                description="This command is restricted to bot owner only.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Gather all system data
            cpu_usage = await self.get_cpu_usage()  # Now async!
            ram_info = self.get_ram_usage()
            disk_info = self.get_disk_usage()
            uptime = self.get_system_uptime()
            cpu_temp = self.get_cpu_temperature()
            os_info = self.get_os_info()
            cpu_count = self.get_cpu_count()
            
            # Helper function for status
            def get_status(percent):
                if percent > 80:
                    return "🔴 [CRITICAL]"
                elif percent > 50:
                    return "🟡 [HIGH]"
                else:
                    return "🟢 [OK]"
            
            # Build embed
            embed = discord.Embed(
                title="System Information",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            # OS Information
            embed.add_field(
                name="Operating System",
                value=f"**{os_info['system']} {os_info['release']}**\n"
                      f"Architecture: {os_info['machine']}",
                inline=False
            )
            
            # CPU Information
            cpu_info_text = f"**Physical**: {cpu_count['physical']} cores | **Logical**: {cpu_count['logical']} cores\n" \
                           f"**Usage**: {cpu_usage}% {get_status(cpu_usage)}\n" \
                           f"**Temperature**: {cpu_temp}"
            
            embed.add_field(
                name="CPU",
                value=cpu_info_text,
                inline=True
            )
            
            # RAM Information
            embed.add_field(
                name="RAM",
                value=f"**Used**: {ram_info['used_gb']}GB / {ram_info['total_gb']}GB\n"
                      f"**Usage**: {ram_info['percent']}% {get_status(ram_info['percent'])}",
                inline=True
            )
            
            # Disk Information
            embed.add_field(
                name="Disk",
                value=f"**Free**: {disk_info['free_gb']}GB / {disk_info['total_gb']}GB\n"
                      f"**Used**: {disk_info['percent']}% {get_status(disk_info['percent'])}",
                inline=True
            )
            
            # Uptime Information
            embed.add_field(
                name="System Uptime",
                value=f"**{uptime}**",
                inline=False
            )
            
            # Bot Statistics (if available)
            embed.add_field(
                name="Bot Latency",
                value=f"**{round(self.bot.latency * 1000, 2)}ms**",
                inline=True
            )
            
            # Footer with update time
            embed.set_footer(text="Updated at")
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Failed to retrieve system information:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(SystemMonitor(bot))
