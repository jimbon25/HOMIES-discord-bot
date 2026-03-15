import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import os
import logging
import asyncio

logger = logging.getLogger(__name__)

class SocialStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rapidapi_key = os.getenv('RAPIDAPI_KEY')
    
    async def fetch_instagram_stats(self, username: str) -> dict:
        """Fetch Instagram user stats from Instagram Statistics API (Rapid API)"""
        try:
            # Validate input
            if not username or not isinstance(username, str):
                return {"success": False, "error": "Username cannot be empty"}
            
            headers = {
                "x-rapidapi-key": self.rapidapi_key,
                "x-rapidapi-host": "instagram-statistics-api.p.rapidapi.com"
            }
            
            # Use search endpoint with balanced perPage for speed/accuracy
            # perPage: 30 takes ~5s, perPage: 100 takes ~11s
            params = {"ig_username": username, "perPage": 30}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://instagram-statistics-api.p.rapidapi.com/search",
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Extract relevant stats from Instagram Statistics API
                        if "data" in data and "meta" in data and data["meta"]["code"] == 200:
                            # Find exact username match in results
                            user_data = None
                            partial_matches = []  # Store similar usernames
                            
                            for user in data["data"]:
                                # Handle None values properly
                                screen_name = user.get("screenName") or ""
                                user_screen_name = screen_name.lower()
                                search_lower = username.lower() if username else ""
                                
                                # Exact match
                                if user_screen_name and user_screen_name == search_lower:
                                    user_data = user
                                    break
                                # Partial match (contains search term)
                                elif search_lower and (search_lower in user_screen_name or user_screen_name.startswith(search_lower)):
                                    partial_matches.append(user)
                            
                            # Return exact match if found
                            if user_data:
                                return {
                                    "success": True,
                                    "username": user_data.get("screenName") or username,
                                    "name": user_data.get("name") or username,
                                    "followers": user_data.get("usersCount", 0),
                                    "profile_pic": user_data.get("image", ""),
                                    "is_verified": user_data.get("verified", False),
                                    "url": user_data.get("url", f"https://instagram.com/{username}"),
                                    "source": "Instagram"
                                }
                            
                            # Return partial matches if found
                            elif partial_matches:
                                matches_list = [u.get("screenName", "") for u in partial_matches[:5] if u.get("screenName")]
                                return {
                                    "success": False,
                                    "error": f"User '@{username}' not found",
                                    "suggestions": matches_list if matches_list else None
                                }
                            
                            # No matches at all
                            else:
                                return {"success": False, "error": f"User '@{username}' not found"}
                        
                        return {"success": False, "error": "Invalid response format"}
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
                "x-rapidapi-host": "tiktok-api11.p.rapidapi.com"
            }
            
            params = {"username": username}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://tiktok-api11.p.rapidapi.com/user/info",
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
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
                
                # Show suggestions if available
                if result.get("suggestions"):
                    suggestions_text = "\n".join([f"• @{u}" for u in result["suggestions"]])
                    embed.add_field(
                        name="💡 Did you mean?",
                        value=suggestions_text,
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
                return
            
            # Format Instagram embed
            embed = discord.Embed(
                title=f"📸 Instagram Stats - @{result['username']}",
                description=result["name"],
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
            
            if verified:
                embed.add_field(
                    name="Status",
                    value=verified,
                    inline=True
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
