"""Help Command - Display all available commands"""
import discord
from discord.ext import commands
from discord import app_commands

class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="help", description="Show all available commands")
    async def help(self, interaction: discord.Interaction):
        """Display help guide with all commands"""
        
        embed = discord.Embed(
            title="Bot Commands Guide",
            description="Complete list of all available commands",
            color=discord.Color.blue()
        )
        
        # Announcement Commands
        embed.add_field(
            name="Announcements",
            value="`/announce` - Send announcement to channel with embed/plain format\n"
                  "`/announce text_size` - Set text size: normal, medium, large",
            inline=False
        )
        
        # AFK System
        embed.add_field(
            name="AFK System",
            value="`?afk <reason>` - Set yourself AFK with custom reason\n"
                  "Auto-removes when you send a message",
            inline=False
        )
        
        # Voice Channel Management
        embed.add_field(
            name="Voice Channels",
            value="`/vc rename <name>` - Rename your voice channel\n"
                  "`/vc limit <number>` - Set user limit (0-99)\n"
                  "`/vc lock` - Lock/unlock channel access\n"
                  "`/vc claim` - Claim channel ownership\n"
                  "`/vc info` - View channel information",
            inline=False
        )
        
        # Bot Stay AFK
        embed.add_field(
            name="Bot Stay AFK",
            value="`/stayafk join` - Bot joins your voice channel and stays AFK 24/7\n"
                  "`/stayafk leave` - Bot leaves voice channel\n"
                  "`/stayafk status` - Check bot voice connection status\n"
                  "`/stayafk clearcache` - Force clear voice cache (for troubleshooting)",
            inline=False
        )
        embed.add_field(
            name="Embed Builder",
            value="`/createembed` - Create custom embeds with modal form",
            inline=False
        )
        
        # Server Info
        embed.add_field(
            name="Server Information",
            value="`/serverhealth` - Main health dashboard\n"
                  "`/members` - Detailed member statistics\n"
                  "`/activity` - Activity tracking & top channels\n"
                  "`/engagement` - Engagement metrics\n"
                  "`/stats` - Quick server statistics\n"
                  "`/serverinfo` - Full server details\n"
                  "`/userinfo <@user>` - User profile information\n"
                  "`/avatar <@user>` - View user avatar",
            inline=False
        )
        
        # Moderation
        embed.add_field(
            name="Moderation",
            value="`/slowmode <channel> <seconds>` - Set slowmode (requires manage_channels)\n"
                  "`/disableslowmode <channel>` - Remove slowmode\n"
                  "`/mute <member> <duration>` - Timeout member (30m, 2h, 1d, etc)\n"
                  "`/unmute <member>` - Remove mute from member\n"
                  "`/deafen <member>` - Deafen member (mutes audio, requires manage_server)\n"
                  "`/undeafen <member>` - Undeafen member (restores audio, requires manage_server)",
            inline=False
        )
        
        # Role Management
        embed.add_field(
            name="Role Management",
            value="`/addrole <member> <role>` - Add role to member (manage_roles required)\n"
                  "`/delrole <member> <role>` - Remove role from member (manage_roles required)",
            inline=False
        )
        
        # Voting System
        embed.add_field(
            name="Voting System",
            value="`/create_vote` - Create a voting poll (2-4 options via modal)\n"
                  "`/cleanup_votes` - Delete all vote data",
            inline=False
        )
        
        # Admin Tools
        embed.add_field(
            name="Admin Tools",
            value="`/system` - View server resource stats (CPU, RAM, disk, uptime)\n"
                  "`/prefix enable` - Enable prefix commands on this server\n"
                  "`/prefix disable` - Disable prefix commands on this server\n"
                  "`/prefix view` - View current prefix settings",
            inline=False
        )
        
        # Custom Messages
        embed.add_field(
            name="Custom Prefix Commands",
            value="`/custommessage create` - Create custom prefix command (admin-only)\n"
                  "`/custommessage list` - View all custom commands\n"
                  "`/custommessage delete <name>` - Delete custom command (admin-only)\n"
                  "`/custommessage disable <name>` - Disable custom command (admin-only)\n"
                  "`/custommessage enable <name>` - Enable custom command (admin-only)",
            inline=False
        )
        
        # Fun & Games
        embed.add_field(
            name="Fun & Games",
            value="`/tictactoe` - Play Tic Tac Toe against bot or friend\n"
                  "`/tictactoe @player` - Play against specific player",
            inline=False
        )
        
        # Server Management
        embed.add_field(
            name="Server Management",
            value="`/rolelist` - List all roles with member counts\n"
                  "`/listcommands <@bot>` - List all bot commands\n"
                  "`/ping` - Check bot latency",
            inline=False
        )
        
        # Bot Info
        embed.add_field(
            name="Bot Information",
            value="`/author` - Bot & author information with social links\n"
                  "`/test` - Test bot response (miaw)",
            inline=False
        )
        
        embed.add_field(
            name="Tips",
            value="• Use `/announce format:plain text_size:large` for big announcements\n"
                  "• `/vc` commands only work when you're in a voice channel\n"
                  "• Admin commands require `administrator` or `manage_channels` permission\n"
                  "• Use `?afk reason` to set AFK status (prefix command)\n"
                  "• **Temporary voice channels** auto-delete when last member leaves - bot will also be kicked\n"
                  "• If bot disappears from voice, use `/stayafk join` to rejoin or `/stayafk clearcache` to reset",
            inline=False
        )
        
        embed.set_footer(text="Use commands with / (slash commands) or ? (prefix for AFK)")
        
        await interaction.response.send_message(embed=embed, ephemeral=False)

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(HelpCommand(bot))
