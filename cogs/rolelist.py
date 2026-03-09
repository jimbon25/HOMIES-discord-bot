import discord
from discord import app_commands
from discord.ext import commands

class RoleList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rolelist", description="Show all server roles")
    async def rolelist(self, interaction: discord.Interaction):
        """Menampilkan list semua role yang ada di server"""
        guild = interaction.guild
        roles = guild.roles[1:]  # Skip @everyone role
        
        # Sort by position (highest role first)
        roles = sorted(roles, key=lambda r: r.position, reverse=True)
        
        embed = discord.Embed(
            title=f"Role List - {guild.name}",
            description=f"Total roles: {len(roles)}",
            color=discord.Color.blue()
        )
        
        # Build role list
        role_list = []
        for role in roles:
            member_count = len(role.members)
            role_info = f"**{role.name}** | {member_count} members"
            role_list.append(role_info)
        
        # Split into chunks jika terlalu panjang
        if len(role_list) > 0:
            # Add roles ke embed (max 25 fields per embed)
            for i in range(0, len(role_list), 25):
                chunk = role_list[i:i+25]
                field_value = "\n".join(chunk)
                
                if i == 0:
                    embed.add_field(
                        name="Roles",
                        value=field_value,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Roles (continued)",
                        value=field_value,
                        inline=False
                    )
        
        embed.set_footer(text=f"Server ID: {guild.id}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(RoleList(bot))
