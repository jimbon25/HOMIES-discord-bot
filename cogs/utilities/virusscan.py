import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import os
from urllib.parse import quote
import hashlib
from datetime import datetime
from collections import defaultdict

class VirusScan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.virustotal_api_key = os.getenv('VIRUSTOTAL_API_KEY')
        self.virustotal_url = "https://www.virustotal.com/api/v3"
        self.threat_levels = {
            "trojan": {"emoji": "🦠", "color": discord.Color.dark_red()},
            "ransomware": {"emoji": "🔐", "color": discord.Color.red()},
            "worm": {"emoji": "🐛", "color": discord.Color.red()},
            "backdoor": {"emoji": "🚪", "color": discord.Color.dark_red()},
            "exploit": {"emoji": "💥", "color": discord.Color.orange()},
            "pua": {"emoji": "⚠️", "color": discord.Color.orange()},
            "adware": {"emoji": "📢", "color": discord.Color.gold()},
            "spyware": {"emoji": "👁️", "color": discord.Color.purple()},
            "phishing": {"emoji": "🎣", "color": discord.Color.orange()},
            "malware": {"emoji": "☠️", "color": discord.Color.red()},
        }
    
    async def check_url_virustotal(self, url: str) -> dict:
        """Check URL with VirusTotal API"""
        try:
            headers = {
                "x-apikey": self.virustotal_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                # Get URL analysis
                url_id = self._get_url_id(url)
                async with session.get(
                    f"{self.virustotal_url}/urls/{url_id}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        attributes = data.get("data", {}).get("attributes", {})
                        return {
                            "success": True,
                            "data": data.get("data", {}),
                            "attributes": attributes
                        }
                    elif resp.status == 404:
                        # URL not in database yet, submit for scanning
                        submit_result = await self._submit_url(session, url, headers)
                        return {
                            "success": True,
                            "not_found": True,
                            "submit_result": submit_result,
                            "data": {},
                            "attributes": {}
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"API returned {resp.status}",
                            "status_code": resp.status
                        }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Request timeout (>10s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _submit_url(self, session, url: str, headers: dict) -> dict:
        """Submit URL for scanning if not found"""
        try:
            data = {"url": url}
            async with session.post(
                f"{self.virustotal_url}/urls",
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status in [200, 201]:
                    result = await resp.json()
                    return {
                        "submitted": True,
                        "analysis_id": result.get("data", {}).get("id")
                    }
                return {"submitted": False}
        except:
            return {"submitted": False}

    
    def _format_stats(self, last_analysis_stats: dict) -> tuple:
        """Extract detection stats"""
        malicious = last_analysis_stats.get("malicious", 0)
        suspicious = last_analysis_stats.get("suspicious", 0)
        undetected = last_analysis_stats.get("undetected", 0)
        harmless = last_analysis_stats.get("harmless", 0)
        timeout = last_analysis_stats.get("timeout", 0)
        total = malicious + suspicious + undetected + harmless + timeout
        
        return malicious, suspicious, undetected, harmless, timeout, total
    
    def _calculate_threat_score(self, malicious: int, suspicious: int, total: int) -> tuple:
        """Calculate threat score 1-100"""
        if total == 0:
            return 0, "Unknown"
        
        threat_score = int(((malicious * 100 + suspicious * 50) / total) / 1.5)
        threat_score = min(100, max(0, threat_score))
        
        if threat_score >= 80:
            level = "CRITICAL"
            emoji = "🔴"
        elif threat_score >= 60:
            level = "HIGH"
            emoji = "🟠"
        elif threat_score >= 40:
            level = "MEDIUM"
            emoji = "🟡"
        elif threat_score >= 20:
            level = "LOW"
            emoji = "🟢"
        else:
            level = "MINIMAL"
            emoji = "✅"
        
        return threat_score, level, emoji
    
    def _extract_malware_families(self, results: dict) -> dict:
        """Extract malware families from vendor results"""
        families = defaultdict(list)
        
        for vendor, data in results.items():
            if data.get("category") != "undetected":
                classification = data.get("result", "")
                engine = data.get("engine_name", vendor)
                
                # Extract malware family
                if classification:
                    for malware_type in self.threat_levels.keys():
                        if malware_type.lower() in classification.lower():
                            families[malware_type].append(engine)
                            break
                    else:
                        families["other"].append(engine)
        
        return dict(families)
    
    def _categorize_vendors(self, results: dict) -> dict:
        """Categorize detection results by type"""
        categories = {
            "malicious": [],
            "suspicious": [],
            "undetected": [],
            "harmless": []
        }
        
        for vendor, data in results.items():
            category = data.get("category", "undetected")
            engine = data.get("engine_name", vendor)
            result = data.get("result", "N/A")
            
            if category in categories:
                categories[category].append({
                    "engine": engine,
                    "result": result
                })
        
        return categories

    
    def _get_url_id(self, url: str) -> str:
        """Generate URL ID for VirusTotal (base64 URL-safe encoding)"""
        import base64
        url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        return url_id
    
    @app_commands.command(name="scan", description="Scan a URL with VirusTotal (Ultra detailed)")
    @app_commands.describe(url="URL to scan (e.g., https://example.com)")
    async def scan_url(self, interaction: discord.Interaction, url: str):
        """Scan URL for malware using VirusTotal with detailed analysis"""
        
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
            
            # Handle not found case
            if result.get("not_found"):
                embed = discord.Embed(
                    title="📝 URL Not In Database",
                    description="URL submitted for scanning",
                    color=discord.Color.blue()
                )
                embed.add_field(name="URL", value=url, inline=False)
                embed.add_field(
                    name="ℹ️",
                    value="This URL hasn't been analyzed yet. It has been submitted to VirusTotal. Please try again in a few seconds.",
                    inline=False
                )
                embed.set_footer(text="First scan may take 10-30 seconds")
                await interaction.followup.send(embed=embed)
                return
            
            # Parse results
            data = result["data"]
            attributes = result["attributes"]
            
            # Validate we have analysis data
            if not attributes or not data:
                embed = discord.Embed(
                    title="⚠️ No Analysis Data",
                    description="URL found but no analysis data available yet. Try again in a moment.",
                    color=discord.Color.gold()
                )
                embed.add_field(name="URL", value=url, inline=False)
                await interaction.followup.send(embed=embed)
                return
            
            last_analysis_stats = attributes.get("last_analysis_stats", {})
            last_analysis_results = attributes.get("last_analysis_results", {})
            
            malicious, suspicious, undetected, harmless, timeout, total = self._format_stats(last_analysis_stats)
            threat_score, threat_level, threat_emoji = self._calculate_threat_score(malicious, suspicious, total)
            
            # Get categorized vendors
            vendor_categories = self._categorize_vendors(last_analysis_results)
            malware_families = self._extract_malware_families(last_analysis_results)
            
            # === EMBED 1: THREAT OVERVIEW ===
            color_map = {
                "CRITICAL": discord.Color.dark_red(),
                "HIGH": discord.Color.red(),
                "MEDIUM": discord.Color.orange(),
                "LOW": discord.Color.green(),
                "MINIMAL": discord.Color.darker_grey()
            }
            
            embed1 = discord.Embed(
                title=f"{threat_emoji} THREAT ASSESSMENT",
                description=f"**Threat Level: {threat_level}**\n**Risk Score: {threat_score}/100**",
                color=color_map.get(threat_level, discord.Color.greyple()),
                timestamp=discord.utils.utcnow()
            )
            
            embed1.add_field(name="🔗 URL", value=f"[{url}]({url})", inline=False)
            
            # Detection summary
            embed1.add_field(
                name="📊 Detection Summary",
                value=f"🔴 **Malicious**: {malicious}/{total}\n" +
                      f"🟡 **Suspicious**: {suspicious}/{total}\n" +
                      f"✅ **Harmless**: {harmless}/{total}\n" +
                      f"⚪ **Undetected**: {undetected}/{total}\n" +
                      f"⏱️ **Timeout**: {timeout}",
                inline=False
            )
            
            # Timestamps
            last_analysis_date = attributes.get("last_analysis_date", 0)
            creation_date = attributes.get("creation_date", 0)
            
            if last_analysis_date:
                date_str = datetime.utcfromtimestamp(last_analysis_date).strftime("%Y-%m-%d %H:%M:%S UTC")
                embed1.add_field(name="⏰ Last Scanned", value=date_str, inline=True)
            
            if creation_date and creation_date != last_analysis_date:
                first_str = datetime.utcfromtimestamp(creation_date).strftime("%Y-%m-%d %H:%M:%S UTC")
                embed1.add_field(name="📅 First Scanned", value=first_str, inline=True)
            
            # Categories
            categories = attributes.get("categories", {})
            if categories:
                category_list = ", ".join([f"`{cat}`" for cat in categories.keys()])
                embed1.add_field(name="🏷️ Categories", value=category_list, inline=False)
            
            # Last HTTPS certificate info
            last_https_cert = attributes.get("last_https_certificate", {})
            if last_https_cert:
                cert_issuer = last_https_cert.get("issuer", "Unknown")
                cert_subject = last_https_cert.get("subject", {}).get("CN", "Unknown")
                embed1.add_field(
                    name="🔒 HTTPS Certificate",
                    value=f"**Subject**: {cert_subject}\n**Issuer**: {cert_issuer}",
                    inline=False
                )
            
            # Reputation
            reputation = attributes.get("reputation", 0)
            if reputation != 0:
                emoji = "👍" if reputation > 0 else "👎"
                embed1.add_field(name=f"{emoji} Reputation", value=f"**{reputation}**", inline=True)
            
            embeds = [embed1]
            
            # === EMBED 2: MALWARE FAMILIES & THREATS ===
            if malware_families and malware_families.get("other") is None and len(malware_families) > 0:
                embed2 = discord.Embed(
                    title="🦠 Detected Malware Families",
                    color=discord.Color.red(),
                )
                
                for malware_type, engines in malware_families.items():
                    if malware_type != "other":
                        threat_info = self.threat_levels.get(malware_type, {"emoji": "⚠️", "color": None})
                        emoji = threat_info["emoji"]
                        engines_str = "\n".join([f"• {e}" for e in engines[:5]])
                        if len(engines) > 5:
                            engines_str += f"\n• ... and {len(engines) - 5} more"
                        embed2.add_field(
                            name=f"{emoji} {malware_type.upper()}",
                            value=engines_str,
                            inline=False
                        )
                
                embeds.append(embed2)
            
            # === EMBED 3: VENDOR DETECTIONS ===
            if vendor_categories["malicious"] or vendor_categories["suspicious"]:
                embed3 = discord.Embed(
                    title="🚨 Detailed Vendor Detections",
                    color=discord.Color.orange(),
                )
                
                # Show malicious detections
                if vendor_categories["malicious"]:
                    mal_list = vendor_categories["malicious"][:15]  # Show first 15
                    mal_str = "\n".join([f"• **{v['engine']}**: {v['result']}" for v in mal_list])
                    if len(vendor_categories["malicious"]) > 15:
                        mal_str += f"\n• ... and {len(vendor_categories['malicious']) - 15} more"
                    embed3.add_field(
                        name=f"🔴 Malicious ({len(vendor_categories['malicious'])})",
                        value=mal_str,
                        inline=False
                    )
                
                # Show suspicious detections
                if vendor_categories["suspicious"]:
                    sus_list = vendor_categories["suspicious"][:10]  # Show first 10
                    sus_str = "\n".join([f"• **{v['engine']}**: {v['result']}" for v in sus_list])
                    if len(vendor_categories["suspicious"]) > 10:
                        sus_str += f"\n• ... and {len(vendor_categories['suspicious']) - 10} more"
                    embed3.add_field(
                        name=f"🟡 Suspicious ({len(vendor_categories['suspicious'])})",
                        value=sus_str,
                        inline=False
                    )
                
                embeds.append(embed3)
            
            # === EMBED 4: HARMLESS VENDORS ===
            if vendor_categories["harmless"]:
                embed4 = discord.Embed(
                    title="✅ Harmless Detections",
                    color=discord.Color.green(),
                )
                harm_list = vendor_categories["harmless"][:20]
                harm_str = ", ".join([v["engine"] for v in harm_list])
                if len(vendor_categories["harmless"]) > 20:
                    harm_str += f" ... (+{len(vendor_categories['harmless']) - 20} more)"
                embed4.description = harm_str
                embeds.append(embed4)
            
            # === EMBED 5: FOOTER & LINKS ===
            embed_footer = discord.Embed(
                title="📋 Additional Resources",
                color=discord.Color.blue(),
            )
            
            # Extract analysis ID safely
            analysis_id = "unknown"
            if data.get("id"):
                id_parts = data.get("id", "").split("-")
                if len(id_parts) > 1:
                    analysis_id = id_parts[1]
                else:
                    analysis_id = data.get("id")
            
            # Build VirusTotal link
            if analysis_id and analysis_id != "unknown":
                vt_link = f"https://www.virustotal.com/gui/home/url/{analysis_id.replace(':', '-')}"
            else:
                vt_link = f"https://www.virustotal.com/search/{quote(url)}"
            
            embed_footer.add_field(
                name="🔍 Full Report",
                value=f"[View on VirusTotal]({vt_link})",
                inline=True
            )
            
            embed_footer.set_footer(text="Powered by VirusTotal API | Ultra Detailed Analysis")
            embeds.append(embed_footer)
            
            # Send embeds
            await interaction.followup.send(embeds=embeds)
        
        except Exception as e:
            import traceback
            error_msg = str(e)
            tb = traceback.format_exc()
            
            embed = discord.Embed(
                title="❌ Scan Error",
                description=f"An error occurred: {error_msg}",
                color=discord.Color.red()
            )
            embed.add_field(name="URL", value=url, inline=False)
            
            # Log error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"VirusScan error for URL {url}: {error_msg}\n{tb}")
            
            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VirusScan(bot))
