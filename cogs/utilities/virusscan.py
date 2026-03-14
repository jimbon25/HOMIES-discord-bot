import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import os
from urllib.parse import quote
import hashlib

class VirusScan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.virustotal_api_key = os.getenv('VIRUSTOTAL_API_KEY')
        self.virustotal_url = "https://www.virustotal.com/api/v3"
    
    async def check_url_virustotal(self, url: str) -> dict:
        """Check URL with VirusTotal API"""
        try:
            headers = {
                "x-apikey": self.virustotal_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                # Get URL analysis
                async with session.get(
                    f"{self.virustotal_url}/urls/{self._get_url_id(url)}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "success": True,
                            "data": data.get("data", {})
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"API returned {resp.status}",
                            "status_code": resp.status
                        }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_url_id(self, url: str) -> str:
        """Generate URL ID for VirusTotal (base64 URL-safe encoding)"""
        import base64
        url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        return url_id
    
    def _format_stats(self, last_analysis_stats: dict) -> tuple:
        """Extract detection stats"""
        malicious = last_analysis_stats.get("malicious", 0)
        suspicious = last_analysis_stats.get("suspicious", 0)
        undetected = last_analysis_stats.get("undetected", 0)
        total = malicious + suspicious + undetected
        
        return malicious, suspicious, undetected, total
    
    @app_commands.command(name="scan", description="Scan a URL with VirusTotal")
    @app_commands.describe(url="URL to scan (e.g., https://example.com)")
    async def scan_url(self, interaction: discord.Interaction, url: str):
        """Scan URL for malware using VirusTotal"""
        
        # Validate URL
        if not url.startswith(("http://", "https://")):
            await interaction.response.send_message(
                "❌ Please provide a valid URL starting with http:// or https://",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Scan URL
            result = await self.check_url_virustotal(url)
            
            if not result["success"]:
                embed = discord.Embed(
                    title="❌ Scan Failed",
                    description=f"Error: {result.get('error', 'Unknown error')}",
                    color=discord.Color.red()
                )
                embed.add_field(name="URL", value=url, inline=False)
                await interaction.followup.send(embed=embed)
                return
            
            # Parse results
            data = result["data"]
            attributes = data.get("attributes", {})
            last_analysis_stats = attributes.get("last_analysis_stats", {})
            last_analysis_results = attributes.get("last_analysis_results", {})
            
            malicious, suspicious, undetected, total = self._format_stats(last_analysis_stats)
            
            # Determine status
            if malicious > 0:
                status = "🔴 MALICIOUS"
                color = discord.Color.red()
            elif suspicious > 0:
                status = "🟡 SUSPICIOUS"
                color = discord.Color.orange()
            else:
                status = "🟢 SAFE"
                color = discord.Color.green()
            
            # Build embed
            embed = discord.Embed(
                title=f"{status} - URL Scan Result",
                description=f"**URL:** {url}",
                color=color,
                timestamp=discord.utils.utcnow()
            )
            
            # Detection ratio
            embed.add_field(
                name="📊 Detection Ratio",
                value=f"**{malicious + suspicious}/{total}** vendors detected\n"
                      f"🔴 Malicious: {malicious}\n"
                      f"🟡 Suspicious: {suspicious}\n"
                      f"✅ Undetected: {undetected}",
                inline=False
            )
            
            # Vendor details (show only detections)
            detections = []
            for vendor, result_data in list(last_analysis_results.items())[:10]:  # Limit to 10
                category = result_data.get("category", "undetected")
                if category != "undetected":
                    engine_name = result_data.get("engine_name", vendor)
                    detections.append(f"• **{engine_name}**: {category}")
            
            if detections:
                embed.add_field(
                    name="🦠 Detected By",
                    value="\n".join(detections) if len(detections) <= 10 else "\n".join(detections[:10]) + f"\n... and {len([v for v in last_analysis_results.values() if v.get('category') != 'undetected']) - 10} more",
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ Detection",
                    value="No malicious vendors detected",
                    inline=False
                )
            
            # Last analysis date
            last_analysis_date = attributes.get("last_analysis_date", 0)
            if last_analysis_date:
                from datetime import datetime
                date_str = datetime.utcfromtimestamp(last_analysis_date).strftime("%Y-%m-%d %H:%M:%S UTC")
                embed.add_field(name="📅 Last Scanned", value=date_str, inline=True)
            
            # Categories
            categories = attributes.get("categories", {})
            if categories:
                category_list = ", ".join(categories.keys())
                embed.add_field(name="🏷️ Categories", value=category_list, inline=True)
            
            embed.set_footer(text="Powered by VirusTotal | Results may vary")
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            embed = discord.Embed(
                title="❌ Scan Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VirusScan(bot))
