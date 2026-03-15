import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import os
import logging

logger = logging.getLogger(__name__)

class SocialStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rapidapi_key = os.getenv('RAPIDAPI_KEY')
    
    async def fetch_instagram_stats(self, username: str) -> dict:
        """Fetch Instagram user stats from Instagram Statistics API (Rapid API)"""
        try:
            headers = {
                "x-rapidapi-key": self.rapidapi_key,
                "x-rapidapi-host": "instagram-statistics-api.p.rapidapi.com"
            }
            
            params = {"ig_username": username}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://instagram-statistics-api.p.rapidapi.com/",
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Extract relevant stats from Instagram Statistics API
                        if "data" in data and "meta" in data and data["meta"]["code"] == 200:
                            user_data = data["data"]
                            return {
                                "success": True,
                                "username": user_data.get("screenName", username),
                                "name": user_data.get("name", username),
                                "followers": user_data.get("usersCount", 0),
                                "posts": user_data.get("posts", 0) or len(user_data.get("lastPosts", [])),
                                "avg_likes": user_data.get("avgLikes", 0),
                                "avg_comments": user_data.get("avgComments", 0),
                                "engagement_rate": round(user_data.get("avgER", 0) * 100, 2),
                                "bio": user_data.get("description", "No bio"),
                                "profile_pic": user_data.get("image", ""),
                                "is_verified": user_data.get("verified", False),
                                "url": user_data.get("url", f"https://instagram.com/{username}"),
                                "source": "Instagram"
                            }
                        return {"success": False, "error": "Invalid response format"}
                    elif resp.status == 404:
                        return {"success": False, "error": "User not found"}
                    else:
                        return {"success": False, "error": f"API error: {resp.status}"}
        
        except asyncio.TimeoutError:
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Instagram API error: {e}")
            return {"success": False, "error": str(e)}
    
    async def fetch_tiktok_stats(self, username: str) -> dict:
        """Fetch TikTok user stats from Rapid API"""
        try:
            headers = {
                "x-rapidapi-key": self.rapidapi_key,
                "x-rapidapi-host": self.tiktok_host
            }
            
            params = {"username": username}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://tiktok-api11.p.rapidapi.com/user/info",
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Extract relevant stats
                        if "userInfo" in data:
                            stats = data["userInfo"]["stats"]
                            user_details = data["userInfo"]["user"]
                            
                            return {
                                "success": True,
                                "username": user_details.get("uniqueId", username),
                                "followers": stats.get("followerCount", 0),
                                "following": stats.get("followingCount", 0),
                                "hearts": stats.get("heartCount", 0),
                                "videos": stats.get("videoCount", 0),
                                "bio": user_details.get("signature", "No bio"),
                                "profile_pic": user_details.get("avatarLarger", ""),
                                "is_verified": user_details.get("verified", False),
                                "source": "TikTok"
                            }
                        return {"success": False, "error": "Invalid response format"}
                    elif resp.status == 404:
                        return {"success": False, "error": "User not found"}
                    else:
                        return {"success": False, "error": f"API error: {resp.status}"}
        
        except asyncio.TimeoutError:
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"TikTok API error: {e}")
            return {"success": False, "error": str(e)}
    
    @app_commands.command(name="socialstats", description="Get Instagram or TikTok user stats")
    @app_commands.describe(
        platform="instagram or tiktok",
        username="Username to lookup"
    )
    async def socialstats_command(
        self, 
        interaction: discord.Interaction, 
        platform: str,
        username: str
    ):
        """Get social media stats for Instagram or TikTok users"""
        
        # Check if API key is configured
        if not self.rapidapi_key:
            embed = discord.Embed(
                title="❌ API Not Configured",
                description="Rapid API key not found in .env file",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer()
        
        platform_lower = platform.lower()
        
        if platform_lower == "instagram":
            result = await self.fetch_instagram_stats(username)
            
            if not result["success"]:
                embed = discord.Embed(
                    title="❌ Instagram Lookup Failed",
                    description=result.get("error", "Unable to fetch data"),
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Format Instagram embed
            embed = discord.Embed(
                title=f"📸 Instagram Stats - @{result['username']}",
                description=result["bio"],
                color=discord.Color.from_rgb(224, 121, 57),  # Instagram pink
                url=result["url"]
            )
            
            # Verification badge
            verified = "✅ Verified" if result["is_verified"] else ""
            
            embed.add_field(
                name="👥 Followers",
                value=f"{result['followers']:,}",
                inline=True
            )
            
            embed.add_field(
                name="📝 Posts",
                value=f"{result['posts']:,}",
                inline=True
            )
            
            embed.add_field(
                name="📊 Engagement Rate",
                value=f"{result['engagement_rate']}%",
                inline=True
            )
            
            embed.add_field(
                name="❤️ Avg Likes",
                value=f"{result['avg_likes']:,}",
                inline=True
            )
            
            embed.add_field(
                name="💬 Avg Comments",
                value=f"{result['avg_comments']:,}",
                inline=True
            )
            
            if verified:
                embed.add_field(
                    name="Status",
                    value=verified,
                    inline=False
                )
            
            if result["profile_pic"]:
                embed.set_thumbnail(url=result["profile_pic"])
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Instagram stats fetched for {username}")
        
        elif platform_lower == "tiktok":
            result = await self.fetch_tiktok_stats(username)
            
            if not result["success"]:
                embed = discord.Embed(
                    title="❌ TikTok Lookup Failed",
                    description=result.get("error", "Unable to fetch data"),
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Format TikTok embed
            embed = discord.Embed(
                title=f"🎵 TikTok Stats - @{result['username']}",
                description=result["bio"],
                color=discord.Color.from_rgb(0, 0, 0),  # TikTok black
                url=f"https://tiktok.com/@{result['username']}"
            )
            
            # Verification badge
            verified = "✅ Verified" if result["is_verified"] else ""
            
            embed.add_field(
                name="👥 Followers",
                value=f"{result['followers']:,}",
                inline=True
            )
            
            embed.add_field(
                name="❤️ Likes",
                value=f"{result['hearts']:,}",
                inline=True
            )
            
            embed.add_field(
                name="🎬 Videos",
                value=f"{result['videos']:,}",
                inline=True
            )
            
            embed.add_field(
                name="➡️ Following",
                value=f"{result['following']:,}",
                inline=True
            )
            
            if verified:
                embed.add_field(
                    name="Status",
                    value=verified,
                    inline=False
                )
            
            if result["profile_pic"]:
                embed.set_thumbnail(url=result["profile_pic"])
            
            await interaction.followup.send(embed=embed)
            logger.info(f"TikTok stats fetched for {username}")
        
        else:
            embed = discord.Embed(
                title="❌ Invalid Platform",
                description="Use `instagram` or `tiktok`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SocialStats(bot))
