import discord
from discord import app_commands
from discord.ext import commands
import io

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
        self.attachment = None
    
    def parse_color(self, color_str: str) -> discord.Color:
        """Parse color from HEX code or color name"""
        color_str = color_str.strip().lower()
        
        # Discord color constants - only valid methods from discord.py 2.0+
        color_map = {
            'red': discord.Color.red(),
            'blue': discord.Color.blue(),
            'green': discord.Color.green(),
            'yellow': discord.Color.yellow(),
            'orange': discord.Color.orange(),
            'purple': discord.Color.purple(),
            'pink': discord.Color.magenta(),
            'magenta': discord.Color.magenta(),
            'teal': discord.Color.teal(),
            'dark_gray': discord.Color.dark_gray(),
            'darker_gray': discord.Color.darker_gray(),
            'light_gray': discord.Color.light_gray(),
            'dark_grey': discord.Color.dark_gray(),
            'darker_grey': discord.Color.darker_gray(),
            'light_grey': discord.Color.light_gray(),
            'blurple': discord.Color.blurple(),
            'brand': discord.Color.blurple(),
            'white': discord.Color.from_rgb(255, 255, 255),
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
        # Defer immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
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
        confirm_view = ConfirmEmbedView(embed, self.channel, self.attachment)
        
        await interaction.followup.send(
            f"Preview embed untuk {self.channel.mention}:",
            embed=embed,
            view=confirm_view,
            ephemeral=True
        )

class ConfirmEmbedView(discord.ui.View):
    def __init__(self, embed, channel, attachment=None):
        super().__init__()
        self.embed = embed
        self.channel = channel
        self.attachment = attachment
    
    @discord.ui.button(label="✅ Confirm & Send", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Defer to prevent interaction timeout
            await interaction.response.defer()
            
            # Send embed with attachment if provided
            if self.attachment:
                # Download attachment and convert to File
                file_bytes = await self.attachment.read()
                file = discord.File(io.BytesIO(file_bytes), filename=self.attachment.filename)
                await self.channel.send(embed=self.embed, file=file)
            else:
                await self.channel.send(embed=self.embed)
            
            # Disable semua button
            for item in self.children:
                item.disabled = True
            
            # Update message dengan button disabled
            await interaction.message.edit(view=self)
            
            await interaction.followup.send(
                content=f"✅ Embed berhasil dikirim ke {self.channel.mention}!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.followup.send(
            "Embed dibatalkan, tidak ada yang dikirim.",
            ephemeral=True
        )

class EmbedBuilder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="createembed", description="Create custom embed with fields and optional image/file")
    @app_commands.describe(channel="Target channel for embed", attachment="Optional file to attach with embed")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_embed(self, interaction: discord.Interaction, channel: discord.TextChannel, attachment: discord.Attachment = None):
        """Membuat custom embed dengan modal, image URL, dan optional file attachment."""
        modal = CreateEmbedModal(channel, self.bot)
        modal.attachment = attachment
        await interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(EmbedBuilder(bot))
