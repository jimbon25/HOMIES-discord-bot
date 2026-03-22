import discord
from discord.ext import commands
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class GhostPingDetector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_modlog_channel(self):
        """Fetch the modlog channel from environment variable"""
        modlog_channel_id = os.getenv('MODLOG_CHANNEL_ID')
        if not modlog_channel_id:
            return None
        
        try:
            return await self.bot.fetch_channel(int(modlog_channel_id))
        except Exception as e:
            logger.error(f"Failed to fetch modlog channel for Ghost Ping: {e}")
            return None

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Detect when a message containing mentions is deleted"""
        # Ignore if sender is a bot
        if message.author.bot:
            return

        # Check if message had any mentions
        has_user_mention = len(message.mentions) > 0
        has_role_mention = len(message.role_mentions) > 0
        has_everyone_mention = message.mention_everyone

        if has_user_mention or has_role_mention or has_everyone_mention:
            modlog_channel = await self.get_modlog_channel()
            if not modlog_channel:
                return

            # Prepare list of mentions for the log
            mention_list = []
            if has_user_mention:
                mention_list.extend([user.mention for user in message.mentions])
            if has_role_mention:
                mention_list.extend([role.mention for role in message.role_mentions])
            if has_everyone_mention:
                mention_list.append("@everyone/@here")

            mentions_str = ", ".join(mention_list[:10]) # Limit to 10 to prevent long embeds
            if len(mention_list) > 10:
                mentions_str += f" (and {len(mention_list) - 10} more...)"

            # Create log embed
            embed = discord.Embed(
                title="👻 Ghost Ping Detected!",
                description=f"A message containing mentions was deleted.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
            embed.add_field(name="Channel", value=f"{message.channel.mention}", inline=True)
            embed.add_field(name="Mentioned Targets", value=mentions_str or "Unknown", inline=False)
            
            # Show message content if available (within limits)
            content = message.content if message.content else "*(No text content)*"
            if len(content) > 1024:
                content = content[:1021] + "..."
            embed.add_field(name="Original Message", value=content, inline=False)
            
            embed.set_footer(text=f"Ghost Ping Detection | Guild: {message.guild.name}")
            
            try:
                await modlog_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to send ghost ping log: {e}")

async def setup(bot):
    await bot.add_cog(GhostPingDetector(bot))
