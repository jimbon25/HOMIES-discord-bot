import discord
from discord import app_commands
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class Nickname(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="nickname", description="Set or clear member nickname")
    @app_commands.describe(
        action="set to give nickname, clear to remove",
        user="Target member",
        nickname="New nickname (leave empty to clear)"
    )
    async def nickname_command(
        self, 
        interaction: discord.Interaction, 
        action: str,
        user: discord.Member,
        nickname: str = None
    ):
        """Set or clear a member's nickname in the server"""
        
        # Check if command executor has permission to change nicknames
        if not interaction.user.guild_permissions.change_nickname and interaction.user.id != interaction.guild.owner_id:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need the `Change Nickname` permission to use this command",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if bot has permission
        if not interaction.guild.me.guild_permissions.manage_nicknames:
            embed = discord.Embed(
                title="❌ Bot Permission Missing",
                description="I need the `Manage Nicknames` permission to change nicknames",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if trying to change owner nickname
        if user.id == interaction.guild.owner_id:
            embed = discord.Embed(
                title="❌ Cannot Change Nickname",
                description="Cannot change the server owner's nickname",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if bot can change this user's nickname (hierarchy check)
        if user.top_role >= interaction.guild.me.top_role:
            embed = discord.Embed(
                title="❌ Cannot Change Nickname",
                description=f"Cannot change nickname for {user.mention} - their role is too high",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            action_lower = action.lower()
            
            if action_lower == "set":
                if not nickname or nickname.strip() == "":
                    embed = discord.Embed(
                        title="❌ Invalid Nickname",
                        description="Nickname cannot be empty",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                # Validate nickname length (Discord limit is 32 characters)
                if len(nickname) > 32:
                    embed = discord.Embed(
                        title="❌ Nickname Too Long",
                        description=f"Nickname must be 32 characters or less (provided: {len(nickname)})",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                old_nickname = user.display_name
                await user.edit(nick=nickname)
                
                embed = discord.Embed(
                    title="✅ Nickname Updated",
                    description=f"Changed {user.mention}'s nickname",
                    color=discord.Color.green()
                )
                embed.add_field(name="Previous", value=old_nickname, inline=True)
                embed.add_field(name="New", value=nickname, inline=True)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"{interaction.user} changed {user}'s nickname from '{old_nickname}' to '{nickname}'")
            
            elif action_lower == "clear":
                old_nickname = user.display_name
                await user.edit(nick=None)
                
                embed = discord.Embed(
                    title="✅ Nickname Cleared",
                    description=f"Removed {user.mention}'s nickname",
                    color=discord.Color.green()
                )
                embed.add_field(name="Previous Nickname", value=old_nickname, inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"{interaction.user} cleared {user}'s nickname (was: '{old_nickname}')")
            
            else:
                embed = discord.Embed(
                    title="❌ Invalid Action",
                    description="Use `set` to give a nickname or `clear` to remove it",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Error",
                description="I don't have permission to change this member's nickname",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Nickname command error: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Nickname(bot))
