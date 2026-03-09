import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="userinfo", description="View user's complete profile")
    @app_commands.describe(user="User to view information")
    async def userinfo(self, interaction: discord.Interaction, user: discord.User):
        """Menampilkan informasi lengkap user"""
        member = interaction.guild.get_member(user.id)
        
        embed = discord.Embed(
            title=f"User Info - {user.name}",
            color=discord.Color.blue()
        )
        
        # Basic info
        embed.add_field(
            name="Username",
            value=f"{user.name}#{user.discriminator}" if user.discriminator != "0" else user.name,
            inline=True
        )
        
        embed.add_field(
            name="ID",
            value=user.id,
            inline=True
        )
        
        # Account creation date
        created_at = user.created_at.strftime("%d/%m/%Y %H:%M:%S")
        embed.add_field(
            name="Account Created",
            value=created_at,
            inline=True
        )
        
        # Join date (if member in guild)
        if member:
            joined_at = member.joined_at.strftime("%d/%m/%Y %H:%M:%S")
            embed.add_field(
                name="Joined Server",
                value=joined_at,
                inline=True
            )
            
            # Status
            embed.add_field(
                name="Status",
                value=str(member.status).title(),
                inline=True
            )
            
            # Roles
            if member.roles[1:]:  # Skip @everyone
                role_names = ", ".join([r.mention for r in member.roles[1:]])
                embed.add_field(
                    name="Roles",
                    value=role_names,
                    inline=False
                )
        
        # Avatar
        embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UserInfo(bot))
