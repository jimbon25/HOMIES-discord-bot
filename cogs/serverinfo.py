import discord
from discord import app_commands
from discord.ext import commands

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="serverinfo", description="View server information")
    async def serverinfo(self, interaction: discord.Interaction):
        """Menampilkan informasi lengkap server"""
        guild = interaction.guild
        
        embed = discord.Embed(
            title=f"Server Info - {guild.name}",
            color=discord.Color.blue()
        )
        
        # Basic info
        embed.add_field(
            name="Server Name",
            value=guild.name,
            inline=True
        )
        
        embed.add_field(
            name="Server ID",
            value=guild.id,
            inline=True
        )
        
        # Member count
        embed.add_field(
            name="Member Count",
            value=f"{guild.member_count} members",
            inline=True
        )
        
        # Owner
        owner = guild.owner
        embed.add_field(
            name="Owner",
            value=f"{owner.mention} ({owner.name})" if owner else "Unknown",
            inline=True
        )
        
        # Created date
        created_at = guild.created_at.strftime("%d/%m/%Y %H:%M:%S")
        embed.add_field(
            name="Created",
            value=created_at,
            inline=True
        )
        
        # Channel count
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        embed.add_field(
            name="Channels",
            value=f"Text: {text_channels} | Voice: {voice_channels}",
            inline=True
        )
        
        # Role count
        embed.add_field(
            name="Roles",
            value=f"{len(guild.roles)} roles",
            inline=True
        )
        
        # Verification level
        embed.add_field(
            name="Verification Level",
            value=str(guild.verification_level).title(),
            inline=True
        )
        
        # Icon
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
