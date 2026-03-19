"""Clear/Purge Messages from Channel"""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ClearMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="clear", description="Delete messages from a channel")
    @app_commands.describe(
        amount="Number of messages to delete (max 300)",
        channel="Target channel to clear (leave empty for current channel)",
        bot="Include bot messages (true/false, default: false)",
        user="Delete only messages from this user (optional)"
    )
    async def clear_messages(
        self, 
        interaction: discord.Interaction, 
        amount: int,
        channel: discord.TextChannel = None,
        bot: bool = False,
        user: discord.User = None
    ):
        """Clear/purge messages from a channel"""
        
        # Check permission: admin OR whitelisted user
        is_admin = interaction.user.guild_permissions.administrator
        is_whitelisted = self.bot.is_user_whitelisted(interaction.user.id)
        
        if not (is_admin or is_whitelisted):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="Only admins can use this command",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Validate amount
        if amount <= 0 or amount > 300:
            embed = discord.Embed(
                title="❌ Invalid Amount",
                description="Amount must be between 1 and 300",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Use current channel if not specified
        if channel is None:
            channel = interaction.channel
        
        # Check if bot has permissions
        if not channel.permissions_for(interaction.guild.me).manage_messages:
            embed = discord.Embed(
                title="❌ No Permission",
                description=f"I don't have permission to manage messages in {channel.mention}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Defer response (deletion might take time)
        await interaction.response.defer(ephemeral=True)
        
        try:
            deleted_count = 0
            messages_to_delete = []
            
            # Fetch messages from channel
            async for message in channel.history(limit=amount * 2):  # Fetch more to account for filtering
                # Stop if we have enough messages to delete
                if len(messages_to_delete) >= amount:
                    break
                
                # Filter by bot parameter
                if bot is False and message.author.bot:
                    # Skip bot messages if bot=False
                    continue
                elif bot is True and not message.author.bot:
                    # Skip non-bot messages if bot=True (delete only bot messages)
                    continue
                
                # Filter by user if specified
                if user is not None and message.author.id != user.id:
                    continue
                
                # Don't delete interaction responses that are still ephemeral
                if message.interaction is not None:
                    continue
                
                messages_to_delete.append(message)
            
            # Delete messages using bulk delete
            if messages_to_delete:
                # Bulk delete can only handle messages that are not older than 14 days
                # Discord API limitation - messages older than 14 days need individual deletion
                old_messages = []
                new_messages = []
                
                cutoff_time = datetime.now().timestamp() - (14 * 24 * 60 * 60)  # 14 days ago
                
                for msg in messages_to_delete:
                    if msg.created_at.timestamp() < cutoff_time:
                        old_messages.append(msg)
                    else:
                        new_messages.append(msg)
                
                # Delete newer messages with bulk delete (faster)
                if new_messages:
                    try:
                        await channel.delete_messages(new_messages)
                        deleted_count += len(new_messages)
                        logger.info(f"Bulk deleted {len(new_messages)} messages from {channel.name}")
                    except Exception as e:
                        logger.error(f"Error bulk deleting messages: {e}")
                
                # Delete older messages individually
                for msg in old_messages:
                    try:
                        await msg.delete()
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting message {msg.id}: {e}")
                        continue
            
            # Build response embed
            filter_info = []
            if bot:
                filter_info.append("Bot messages only")
            else:
                filter_info.append("Excluding bot messages")
            
            if user:
                filter_info.append(f"From {user.mention}")
            
            embed = discord.Embed(
                title="✅ Messages Cleared",
                description=f"Successfully deleted **{deleted_count}** messages from {channel.mention}",
                color=discord.Color.green()
            )
            
            if filter_info:
                embed.add_field(
                    name="Filters Applied",
                    value="\n".join(filter_info),
                    inline=False
                )
            
            embed.set_footer(text=f"Executed by: {interaction.user.name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to delete messages in that channel",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error clearing messages: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to clear messages: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ClearMessages(bot))
