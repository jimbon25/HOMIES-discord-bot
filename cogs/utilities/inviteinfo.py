"""Discord Invite Analyzer"""
import discord
from discord import app_commands
from discord.ext import commands
import re


class InviteAnalyzer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def extract_invite_code(self, invite_input: str) -> str:
        """Extract invite code from URL or return code directly"""
        # Match formats: https://discord.gg/XXXXX or discord.gg/XXXXX or XXXXX
        patterns = [
            r'discord\.gg\/([a-zA-Z0-9-]+)',  # discord.gg/code
            r'discordapp\.com\/invite\/([a-zA-Z0-9-]+)',  # discordapp.com format
            r'^([a-zA-Z0-9-]{3,})$'  # Just the code
        ]
        
        for pattern in patterns:
            match = re.search(pattern, invite_input)
            if match:
                return match.group(1)
        
        return None

    @app_commands.command(name="inviteinfo", description="Get information about a Discord server invite")
    @app_commands.describe(invite="Discord invite link (e.g., discord.gg/XXXXX or https://discord.gg/XXXXX)")
    async def invite_info(self, interaction: discord.Interaction, invite: str):
        """Analyze Discord invite and show server information"""
        await interaction.response.defer(ephemeral=True)
        
        # Extract invite code
        code = self.extract_invite_code(invite)
        
        if not code:
            embed = discord.Embed(
                title="❌ Invalid Invite",
                description="Could not parse the invite. Please use:\n• `discord.gg/CODE`\n• Full URL\n• Just the code",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            # Fetch invite info
            invite_obj = await self.bot.fetch_invite(code, with_counts=True, with_expiration=True)
            
            # Create embed
            embed = discord.Embed(
                title=f"Invite Analysis - {invite_obj.guild.name}",
                color=discord.Color.blurple()
            )
            
            # Member count
            if invite_obj.approximate_member_count:
                embed.add_field(
                    name="Members",
                    value=f"~{invite_obj.approximate_member_count:,}",
                    inline=True
                )
            
            # Online count
            if invite_obj.approximate_presence_count:
                embed.add_field(
                    name="Online",
                    value=f"~{invite_obj.approximate_presence_count:,}",
                    inline=True
                )
            
            # Verification level with fallback
            verification_level_name = "Unknown"
            try:
                verification_levels = {
                    discord.VerificationLevel.none: "None",
                    discord.VerificationLevel.low: "Low",
                    discord.VerificationLevel.medium: "Medium",
                    discord.VerificationLevel.high: "High"
                }
                # Try to add very_high if it exists
                if hasattr(discord.VerificationLevel, 'very_high'):
                    verification_levels[discord.VerificationLevel.very_high] = "Very High"
                
                verification_level_name = verification_levels.get(invite_obj.guild.verification_level, "Unknown")
            except:
                verification_level_name = str(invite_obj.guild.verification_level).title()
            
            embed.add_field(
                name="Verification",
                value=verification_level_name,
                inline=True
            )
            
            # Explicit content filter with fallback
            filter_level_name = "Unknown"
            try:
                filter_levels = {
                    discord.ContentFilter.disabled: "Disabled",
                    discord.ContentFilter.all_members: "All Members",
                    discord.ContentFilter.no_role: "No Role"
                }
                filter_level_name = filter_levels.get(invite_obj.guild.explicit_content_filter, "Unknown")
            except:
                filter_level_name = str(invite_obj.guild.explicit_content_filter).title()
            
            embed.add_field(
                name="Content Filter",
                value=filter_level_name,
                inline=True
            )
            
            # Owner
            if invite_obj.guild.owner:
                embed.add_field(
                    name="Owner",
                    value=f"{invite_obj.guild.owner.mention}",
                    inline=True
                )
            
            # Boost level
            boost_level = invite_obj.guild.premium_tier
            booster_count = invite_obj.guild.premium_subscription_count or 0
            
            embed.add_field(
                name="Boost Level",
                value=f"Level {boost_level} ({booster_count} boosters)",
                inline=True
            )
            
            # Features
            if invite_obj.guild.features:
                features = ", ".join([f.replace("_", " ").title() for f in list(invite_obj.guild.features)[:5]])
                if len(invite_obj.guild.features) > 5:
                    features += f" + {len(invite_obj.guild.features) - 5} more"
                
                embed.add_field(
                    name="Features",
                    value=features,
                    inline=False
                )
            
            # Channel count
            channel_count = len(invite_obj.guild.channels) if hasattr(invite_obj.guild, 'channels') else "N/A"
            
            embed.add_field(
                name="Channels",
                value=str(channel_count),
                inline=True
            )
            
            # Role count
            role_count = len(invite_obj.guild.roles) if hasattr(invite_obj.guild, 'roles') else "N/A"
            
            embed.add_field(
                name="Roles",
                value=str(role_count),
                inline=True
            )
            
            # Invite expiration (if available)
            if invite_obj.expires_at:
                embed.add_field(
                    name="Expires",
                    value=f"<t:{int(invite_obj.expires_at.timestamp())}:R>",
                    inline=True
                )
            
            # Invite code
            embed.add_field(
                name="Code",
                value=f"`{code}`",
                inline=False
            )
            
            # Icon
            if invite_obj.guild.icon:
                embed.set_thumbnail(url=invite_obj.guild.icon.url)
            
            embed.set_footer(text=f"Guild ID: {invite_obj.guild.id}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except discord.NotFound:
            embed = discord.Embed(
                title="❌ Invite Not Found",
                description=f"The invite code `{code}` does not exist or has expired.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ No Access",
                description="I don't have permission to view this invite.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to fetch invite info: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(InviteAnalyzer(bot))
