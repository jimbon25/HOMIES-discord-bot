import discord
from discord import app_commands
from discord.ext import commands

class CreateEmbedModal(discord.ui.Modal, title="Create Embed"):
    title_input = discord.ui.TextInput(
        label="Title",
        placeholder="Enter embed title",
        required=True,
        max_length=256
    )
    
    description_input = discord.ui.TextInput(
        label="Description",
        placeholder="Enter embed description",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=4000
    )
    
    field1_name = discord.ui.TextInput(
        label="Field 1 Title (Optional)",
        placeholder="Leave empty to skip",
        required=False,
        max_length=256
    )
    
    field1_value = discord.ui.TextInput(
        label="Field 1 Content",
        placeholder="Leave empty to skip",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=1024
    )
    
    color_input = discord.ui.TextInput(
        label="Color (HEX or name)",
        placeholder="#FF0000 or 'red', 'blue', 'green'...",
        required=False,
        max_length=50,
        default="blue"
    )
    
    def __init__(self, channel, bot):
        super().__init__()
        self.channel = channel
        self.bot = bot
    
    def parse_color(self, color_str: str) -> discord.Color:
        """Parse color from HEX code or color name"""
        color_str = color_str.strip().lower()
        
        # Discord color constants
        color_map = {
            'red': discord.Color.red(),
            'blue': discord.Color.blue(),
            'green': discord.Color.green(),
            'yellow': discord.Color.yellow(),
            'orange': discord.Color.orange(),
            'purple': discord.Color.purple(),
            'pink': discord.Color.magenta(),
            'magenta': discord.Color.magenta(),
            'cyan': discord.Color.cyan(),
            'teal': discord.Color.teal(),
            'darker_gray': discord.Color.darker_gray(),
            'dark_gray': discord.Color.dark_gray(),
            'light_gray': discord.Color.light_gray(),
            'darker_grey': discord.Color.darker_gray(),
            'dark_grey': discord.Color.dark_gray(),
            'light_grey': discord.Color.light_gray(),
            'blurple': discord.Color.blurple(),
            'brand': discord.Color.blurple(),
            'white': discord.Color.white(),
            'black': discord.Color.from_rgb(0, 0, 0),
        }
        
        # Check if it's a named color
        if color_str in color_map:
            return color_map[color_str]
        
        # Try to parse as HEX
        if color_str.startswith('#'):
            try:
                hex_value = color_str.lstrip('#')
                if len(hex_value) == 6:
                    return discord.Color(int(hex_value, 16))
            except ValueError:
                pass
        
        # Default to blue if parsing fails
        return discord.Color.blue()
    
    async def on_submit(self, interaction: discord.Interaction):
        color = self.parse_color(self.color_input.value)
        embed = discord.Embed(
            title=self.title_input.value,
            description=self.description_input.value,
            color=color
        )
        
        if self.field1_name.value and self.field1_value.value:
            embed.add_field(
                name=self.field1_name.value,
                value=self.field1_value.value,
                inline=False
            )
        
        # Create button untuk confirm
        confirm_view = ConfirmEmbedView(embed, self.channel)
        
        await interaction.response.send_message(
            f"Preview embed untuk {self.channel.mention}:",
            embed=embed,
            view=confirm_view,
            ephemeral=True
        )

class ConfirmEmbedView(discord.ui.View):
    def __init__(self, embed, channel):
        super().__init__()
        self.embed = embed
        self.channel = channel
    
    @discord.ui.button(label="✅ Confirm & Send", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.channel.send(embed=self.embed)
            
            # Disable semua button
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(
                content=f"✅ Embed berhasil dikirim ke {self.channel.mention}!",
                view=self
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Embed dibatalkan, tidak ada yang dikirim.",
            ephemeral=True
        )

class EmbedBuilder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="createembed", description="Create custom embed with fields")
    @app_commands.describe(channel="Target channel for embed")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_embed(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Membuat custom embed dengan modal."""
        modal = CreateEmbedModal(channel, self.bot)
        await interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(EmbedBuilder(bot))
