"""Deafen/Undeafen moderation commands"""
import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)


class DeafenModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="deafen", description="Deafen a member")
    @app_commands.describe(member="The member to deafen")
    async def deafen(self, interaction: discord.Interaction, member: discord.Member):
        """Deafen a member (mutes their audio)"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need **Manage Server** permission to use this command!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Can't deafen self
        if member.id == interaction.user.id:
            embed = discord.Embed(
                title="⚠️ Can't Deafen Self",
                description="You can't deafen yourself!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if bot can manage member
        if member.top_role >= interaction.guild.me.top_role:
            embed = discord.Embed(
                title="❌ Role Too High",
                description=f"I can't deafen **{member.mention}** - they have a role at or above mine!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if already deafened
        if member.voice and member.voice.deaf:
            embed = discord.Embed(
                title="⚠️ Already Deafened",
                description=f"**{member.mention}** is already deafened!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await member.edit(deafen=True)
            embed = discord.Embed(
                title="🔇 Member Deafened",
                description=f"**{member.mention}** has been deafened",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error deafening member: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to deafen member: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="undeafen", description="Undeafen a member")
    @app_commands.describe(member="The member to undeafen")
    async def undeafen(self, interaction: discord.Interaction, member: discord.Member):
        """Undeafen a member (restores their audio)"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need **Manage Server** permission to use this command!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if bot can manage member
        if member.top_role >= interaction.guild.me.top_role:
            embed = discord.Embed(
                title="❌ Role Too High",
                description=f"I can't undeafen **{member.mention}** - they have a role at or above mine!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if not deafened
        if not member.voice or not member.voice.deaf:
            embed = discord.Embed(
                title="⚠️ Not Deafened",
                description=f"**{member.mention}** is not deafened!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await member.edit(deafen=False)
            embed = discord.Embed(
                title="🔊 Member Undeafened",
                description=f"**{member.mention}** has been undeafened",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error undeafening member: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to undeafen member: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(DeafenModeration(bot))
