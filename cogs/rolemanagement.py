"""Role Management Commands"""
import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)


class RoleManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="addrole", description="Add a role to a member")
    @app_commands.describe(
        member="The member to add role to",
        role="The role to add"
    )
    async def add_role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        """Add a role to a member"""
        
        # Check if user has permission to manage roles OR is whitelisted
        has_permission = interaction.user.guild_permissions.manage_roles
        is_whitelisted = self.bot.is_user_whitelisted(interaction.user.id)
        
        if not (has_permission or is_whitelisted):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to manage roles!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if bot can assign this role
        if role.position >= interaction.guild.me.top_role.position:
            embed = discord.Embed(
                title="❌ Role Too High",
                description=f"I can't assign **{role.mention}** - it's at or above my highest role!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if member already has the role
        if role in member.roles:
            embed = discord.Embed(
                title="⚠️ Already Has Role",
                description=f"**{member.mention}** already has **{role.mention}**!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await member.add_roles(role)
            
            # Log to modlog
            modlog_cog = self.bot.get_cog('ModerationLog')
            if modlog_cog:
                await modlog_cog.log_action(interaction.guild, "addrole", interaction.user, member, f"Role added: {role.mention}")
            
            embed = discord.Embed(
                title="✅ Role Added",
                description=f"Added **{role.mention}** to **{member.mention}**",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error adding role: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to add role: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="delrole", description="Remove a role from a member")
    @app_commands.describe(
        member="The member to remove role from",
        role="The role to remove"
    )
    async def del_role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        """Remove a role from a member"""
        
        # Check if user has permission to manage roles OR is whitelisted
        has_permission = interaction.user.guild_permissions.manage_roles
        is_whitelisted = self.bot.is_user_whitelisted(interaction.user.id)
        
        if not (has_permission or is_whitelisted):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to manage roles!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if bot can remove this role
        if role.position >= interaction.guild.me.top_role.position:
            embed = discord.Embed(
                title="❌ Role Too High",
                description=f"I can't remove **{role.mention}** - it's at or above my highest role!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if member has the role
        if role not in member.roles:
            embed = discord.Embed(
                title="⚠️ Doesn't Have Role",
                description=f"**{member.mention}** doesn't have **{role.mention}**!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await member.remove_roles(role)
            
            # Log to modlog
            modlog_cog = self.bot.get_cog('ModerationLog')
            if modlog_cog:
                await modlog_cog.log_action(interaction.guild, "delrole", interaction.user, member, f"Role removed: {role.mention}")
            
            embed = discord.Embed(
                title="✅ Role Removed",
                description=f"Removed **{role.mention}** from **{member.mention}**",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error removing role: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to remove role: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(RoleManagement(bot))
