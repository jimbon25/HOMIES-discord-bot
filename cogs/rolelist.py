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
        
        # Build role list with visual color representation
        role_list = []
        for role in roles:
            member_count = len(role.members)
            # Get hex color
            hex_color = f"#{role.color.value:06x}" if role.color.value != 0 else "No Color"
            # Create inline color block using unicode (attempts to visually represent color)
            role_info = f"𝟭 **{role.name}** | {member_count} members\n       └─ Color: {hex_color}"
            role_list.append({
                'name': role.name,
                'members': member_count,
                'hex': hex_color,
                'color': role.color,
                'info': role_info
            })
        
        # Split into chunks jika terlalu panjang
        if len(role_list) > 0:
            # Create embeds per role with color (max 25 roles per response)
            embeds = []
            
            for i in range(0, len(role_list), 25):
                chunk = role_list[i:i+25]
                
                # Create embed for this chunk
                chunk_embed = discord.Embed(
                    title=f"Role List - {guild.name}" if i == 0 else f"Role List (continued)",
                    description=f"Total roles: {len(roles)}" if i == 0 else "",
                    color=discord.Color.blue()
                )
                
                # Add each role as a field with its color
                for role_data in chunk:
                    field_value = f"Members: **{role_data['members']}**\nColor: `{role_data['hex']}`"
                    chunk_embed.add_field(
                        name=role_data['name'],
                        value=field_value,
                        inline=False
                    )
                
                # Set embed color to match first role in chunk (for visual appeal)
                if chunk[0]['color'].value != 0:
                    chunk_embed.color = chunk[0]['color']
                
                embeds.append(chunk_embed)
            
            if embeds:
                embeds[-1].set_footer(text=f"Server ID: {guild.id}")
                await interaction.response.send_message(embeds=embeds[:10])  # Discord limit: max 10 embeds

async def setup(bot):
    await bot.add_cog(RoleList(bot))
