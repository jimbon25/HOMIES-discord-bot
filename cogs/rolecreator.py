"""Role Creator - Create roles with custom colors"""
import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)

class RoleCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="createrole", description="Create a new role with optional color")
    @app_commands.describe(name="Role name", color="Role color in hex format (e.g., #FF5733) or color name (optional)")
    @app_commands.checks.has_permissions(administrator=True)
    async def createrole(self, interaction: discord.Interaction, name: str, color: str = None):
        """Create a new role with optional color"""
        
        try:
            # Parse color
            role_color = discord.Color.default()
            
            if color:
                color = color.strip()
                
                # Try hex color format
                if color.startswith('#'):
                    try:
                        role_color = discord.Color(int(color[1:], 16))
                    except ValueError:
                        await interaction.response.send_message(
                            f"❌ Invalid hex color format. Use #RRGGBB (e.g., #FF5733)",
                            ephemeral=True
                        )
                        return
                else:
                    # Try color name format
                    color_name = color.lower()
                    color_map = {
                        'red': discord.Color.red(),
                        'blue': discord.Color.blue(),
                        'green': discord.Color.green(),
                        'yellow': discord.Color.yellow(),
                        'purple': discord.Color.purple(),
                        'pink': discord.Color.magenta(),
                        'magenta': discord.Color.magenta(),
                        'cyan': discord.Color.cyan(),
                        'orange': discord.Color.orange(),
                        'gold': discord.Color.gold(),
                        'dark_red': discord.Color.dark_red(),
                        'dark_blue': discord.Color.dark_blue(),
                        'dark_green': discord.Color.dark_green(),
                        'dark_gold': discord.Color.dark_gold(),
                        'dark_orange': discord.Color.dark_orange(),
                        'light_gray': discord.Color.light_gray(),
                        'dark_gray': discord.Color.dark_gray(),
                        'darker_gray': discord.Color.darker_gray(),
                        'blurple': discord.Color.blurple(),
                        'greyple': discord.Color.greyple(),
                        'dark_theme_background': discord.Color.dark_theme_background(),
                    }
                    
                    if color_name in color_map:
                        role_color = color_map[color_name]
                    else:
                        available_colors = ", ".join(list(color_map.keys())[:10])
                        await interaction.response.send_message(
                            f"❌ Unknown color name. Available: {available_colors}...\nOr use hex format like #FF5733",
                            ephemeral=True
                        )
                        return
            
            # Create role
            new_role = await interaction.guild.create_role(
                name=name,
                color=role_color,
                reason=f"Created by {interaction.user.name}"
            )
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Role Created",
                color=role_color
            )
            embed.add_field(name="Role Name", value=f"<@&{new_role.id}>", inline=True)
            embed.add_field(name="Role ID", value=new_role.id, inline=True)
            if color:
                embed.add_field(name="Color", value=color, inline=True)
            embed.set_footer(text=f"Created by: {interaction.user.name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            logger.info(f"Role created: {name} (ID: {new_role.id}) by {interaction.user.name}")
        
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to create roles in this server",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error creating role: {e}")
            await interaction.response.send_message(
                f"❌ Error creating role: {str(e)}",
                ephemeral=True
            )
    
    @createrole.error
    async def createrole_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission (Admin) to use this command.",
                ephemeral=True
            )

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(RoleCreator(bot))
