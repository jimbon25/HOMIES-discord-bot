import discord
from discord import app_commands
from discord.ext import commands

class ListCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="listcommands", description="Show all bot commands")
    @app_commands.describe(bot="Bot to view commands")
    async def listcommands(self, interaction: discord.Interaction, bot: discord.User):
        """Menampilkan semua slash commands yang tersedia"""
        
        # Check apakah user yang di-mention adalah bot
        if not bot.bot:
            await interaction.response.send_message(
                "❌ User yang di-mention harus bot!",
                ephemeral=True
            )
            return
        
        # Jika mention bot sendiri, tampilkan commands
        if bot.id == self.bot.user.id:
            # Get all app commands
            commands_list = self.bot.tree.get_commands()
            
            if not commands_list:
                await interaction.response.send_message(
                    "❌ Bot tidak memiliki commands",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"Commands - {bot.name}",
                description=f"Total commands: {len(commands_list)}",
                color=discord.Color.blue()
            )
            
            # Build command list
            for cmd in sorted(commands_list, key=lambda c: c.name):
                name = f"/{cmd.name}"
                description = cmd.description or "No description"
                embed.add_field(
                    name=name,
                    value=description,
                    inline=False
                )
            
            embed.set_footer(text=f"Bot ID: {bot.id}")
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                f"❌ Saya hanya bisa show commands dari bot saya sendiri",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(ListCommands(bot))
