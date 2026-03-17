"""Advanced Voting System Cog"""
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
import json
import os
from datetime import datetime
import logging
from utils import safe_save_json

logger = logging.getLogger(__name__)


class VoteModal(Modal, title="Create Vote"):
    """Modal for creating a voting poll"""
    
    question_input = TextInput(
        label="Question",
        placeholder="What to vote on?",
        required=True,
        max_length=300,
        style=discord.TextStyle.paragraph
    )
    
    option_a = TextInput(
        label="Option 1",
        placeholder="Option 1",
        required=True,
        max_length=100
    )
    
    option_b = TextInput(
        label="Option 2",
        placeholder="Option 2",
        required=True,
        max_length=100
    )
    
    option_c = TextInput(
        label="Option 3",
        placeholder="Leave blank to skip",
        required=False,
        max_length=100
    )
    
    option_d = TextInput(
        label="Option 4",
        placeholder="Leave blank to skip",
        required=False,
        max_length=100
    )
    
    def __init__(self, bot, channel):
        super().__init__()
        self.bot = bot
        self.channel = channel
        self.guild = channel.guild
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Collect options (only non-empty ones)
            options = []
            for option_input in [self.option_a, self.option_b, self.option_c, self.option_d]:
                if option_input.value and option_input.value.strip():
                    options.append(option_input.value.strip())
            
            # Validate min 2 and max 4 options
            if len(options) < 2:
                await interaction.response.send_message(
                    "You must provide at least 2 voting options!",
                    ephemeral=True
                )
                return
            
            if len(options) > 4:
                options = options[:4]
                logger.warning(f"Vote options truncated to 4 max")
            
            # Create vote instance
            vote_id = int(datetime.now().timestamp() * 1000)  # Unique ID
            guild_member_count = len(self.guild.members)  # Get total member count
            vote_data = {
                "vote_id": vote_id,
                "question": self.question_input.value,
                "options": options,
                "votes": {str(i): 0 for i in range(len(options))},
                "voters": [],  # List of user IDs who voted
                "creator_id": interaction.user.id,
                "created_at": datetime.now().isoformat(),
                "is_active": True,
                "guild_member_count": guild_member_count  # Store for percentage calculation
            }
            
            # Save vote data
            VotingSystem.save_vote(vote_data)
            
            # Create and send embed with buttons
            view = VoteView(self.bot, vote_id, options)
            embed = VotingSystem.create_vote_embed(vote_data)
            
            await interaction.response.send_message(
                embed=embed,
                view=view
            )
        except Exception as e:
            logger.error(f"Error in vote modal submission: {e}")
            try:
                await interaction.response.send_message(
                    f"Error creating vote: {str(e)}",
                    ephemeral=True
                )
            except:
                pass


class VoteView(View):
    """View for voting buttons"""
    
    def __init__(self, bot, vote_id: int, options: list):
        super().__init__(timeout=None)
        self.bot = bot
        self.vote_id = vote_id
        self.options = options[:4]  # Limit to 4 options max
        
        # Create buttons for each option
        colors = [discord.ButtonStyle.primary, discord.ButtonStyle.secondary, 
                 discord.ButtonStyle.success, discord.ButtonStyle.danger]
        
        for idx, option in enumerate(self.options):
            button = Button(
                label=option[:80],  # Limit button label to 80 chars
                custom_id=f"vote_{vote_id}_{idx}",
                style=colors[idx % len(colors)]
            )
            button.callback = self.vote_callback
            self.add_item(button)
        
        # Add end vote button
        end_button = Button(
            label="End Vote",
            custom_id=f"end_vote_{vote_id}",
            style=discord.ButtonStyle.danger
        )
        end_button.callback = self.end_vote_callback
        self.add_item(end_button)
    
    async def vote_callback(self, interaction: discord.Interaction):
        """Handle vote button click"""
        vote_id = self.vote_id
        option_idx = int(interaction.custom_id.split("_")[2])
        user_id = interaction.user.id
        
        # Load vote data
        vote_data = VotingSystem.load_vote(vote_id)
        if not vote_data:
            await interaction.response.send_message(
                "Vote not found or has ended.",
                ephemeral=True
            )
            return
        
        if not vote_data["is_active"]:
            await interaction.response.send_message(
                "This vote has ended.",
                ephemeral=True
            )
            return
        
        # Check if user already voted
        if user_id in vote_data["voters"]:
            await interaction.response.send_message(
                "You have already voted in this poll.",
                ephemeral=True
            )
            return
        
        # Record vote
        vote_data["votes"][str(option_idx)] += 1
        vote_data["voters"].append(user_id)
        VotingSystem.save_vote(vote_data)
        
        # Update embed
        embed = VotingSystem.create_vote_embed(vote_data)
        await interaction.response.defer()
        await interaction.message.edit(embed=embed)
    
    async def end_vote_callback(self, interaction: discord.Interaction):
        """Handle end vote button click - admin only"""
        # Check if user is admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Only administrators can end a vote.",
                ephemeral=True
            )
            return
        
        vote_id = self.vote_id
        vote_data = VotingSystem.load_vote(vote_id)
        if not vote_data:
            await interaction.response.send_message(
                "Vote not found.",
                ephemeral=True
            )
            return
        
        # Deactivate vote
        vote_data["is_active"] = False
        VotingSystem.save_vote(vote_data)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Update embed with winner
        embed = VotingSystem.create_vote_embed(vote_data, ended=True)
        await interaction.response.defer()
        await interaction.message.edit(embed=embed, view=self)


class VotingSystem:
    """Utility class for vote management"""
    
    VOTE_DATA_DIR = "data/votes"
    
    @staticmethod
    def ensure_dir():
        """Ensure vote data directory exists"""
        os.makedirs(VotingSystem.VOTE_DATA_DIR, exist_ok=True)
    
    @staticmethod
    def save_vote(vote_data: dict):
        """Save vote data to JSON"""
        VotingSystem.ensure_dir()
        filepath = f"{VotingSystem.VOTE_DATA_DIR}/{vote_data['vote_id']}.json"
        safe_save_json(vote_data, filepath)
    
    @staticmethod
    def load_vote(vote_id: int) -> dict:
        """Load vote data from JSON"""
        VotingSystem.ensure_dir()
        filepath = f"{VotingSystem.VOTE_DATA_DIR}/{vote_id}.json"
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    
    @staticmethod
    def create_progress_bar(votes: int, total: int, bar_length: int = 10) -> str:
        """Create visual progress bar with blocks"""
        if total == 0:
            return "⬜" * bar_length
        
        filled = int((votes / total) * bar_length)
        empty = bar_length - filled
        return "🟩" * filled + "⬜" * empty  # Shows votes/total_members visually
    
    @staticmethod
    def create_vote_embed(vote_data: dict, ended: bool = False) -> discord.Embed:
        """Create embedded vote display"""
        total_votes = sum(vote_data["votes"].values())
        guild_member_count = vote_data.get("guild_member_count", 1)  # Default to 1 to avoid division by 0
        
        title = "Vote Results" if vote_data["is_active"] else "Vote Ended"
        color = discord.Color.blue() if vote_data["is_active"] else discord.Color.red()
        
        embed = discord.Embed(
            title=title,
            description=f"**{vote_data['question']}**",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        # Add options with progress bars
        for idx, option in enumerate(vote_data["options"]):
            votes = vote_data["votes"].get(str(idx), 0)
            # Calculate percentage based on guild member count (participation rate)
            percentage = (votes / guild_member_count * 100) if guild_member_count > 0 else 0
            
            progress_bar = VotingSystem.create_progress_bar(votes, guild_member_count)
            option_text = f"{option}\n{progress_bar} {percentage:.1f}% ({votes} votes)"
            
            embed.add_field(
                name=f"Option {chr(65 + idx)}",
                value=option_text,
                inline=False
            )
        
        # Add winner if vote ended
        if not vote_data["is_active"]:
            if total_votes > 0:
                max_votes = max(vote_data["votes"].values())
                winners = [vote_data["options"][i] for i, v in enumerate(vote_data["votes"].values()) if v == max_votes]
                winner_text = " & ".join(winners) if len(winners) > 1 else winners[0]
                embed.add_field(
                    name="Winner",
                    value=f"**{winner_text}** with {max_votes} votes",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Winner",
                    value="No votes were cast.",
                    inline=False
                )
        
        return embed


class VoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="create_vote", description="Create a voting poll (2-4 options)")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_vote(self, interaction: discord.Interaction):
        """Open modal to create a vote (max 4 options due to Discord button limit)"""
        try:
            modal = VoteModal(self.bot, interaction.channel)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error opening vote modal: {e}")
            await interaction.response.send_message(
                f"Error opening vote modal: {str(e)}",
                ephemeral=True
            )
    
    @create_vote.error
    async def create_vote_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler for create_vote command"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "Only administrators can create votes.",
                ephemeral=True
            )
        else:
            logger.error(f"create_vote error: {error}")
            try:
                await interaction.response.send_message(
                    f"Command error: {str(error)}",
                    ephemeral=True
                )
            except:
                pass
    
    @app_commands.command(name="cleanup_votes", description="Delete all vote data")
    @app_commands.checks.has_permissions(administrator=True)
    async def cleanup_votes(self, interaction: discord.Interaction):
        """Delete all vote data files"""
        try:
            import shutil
            votes_dir = VotingSystem.VOTE_DATA_DIR
            
            if not os.path.exists(votes_dir):
                await interaction.response.send_message(
                    "No vote data to clean up.",
                    ephemeral=True
                )
                return
            
            # Count files before deletion
            vote_files = [f for f in os.listdir(votes_dir) if f.endswith('.json')]
            file_count = len(vote_files)
            
            if file_count == 0:
                await interaction.response.send_message(
                    "No vote data to clean up.",
                    ephemeral=True
                )
                return
            
            # Delete all vote files
            shutil.rmtree(votes_dir)
            os.makedirs(votes_dir, exist_ok=True)
            
            await interaction.response.send_message(
                f"✅ Deleted {file_count} vote(s) successfully.",
                ephemeral=True
            )
            logger.info(f"Cleaned up {file_count} vote files by {interaction.user}")
        except Exception as e:
            logger.error(f"Error in cleanup_votes: {e}")
            await interaction.response.send_message(
                f"Error cleaning up votes: {str(e)}",
                ephemeral=True
            )
    
    @cleanup_votes.error
    async def cleanup_votes_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler for cleanup_votes command"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "Only administrators can clean up votes.",
                ephemeral=True
            )
        else:
            logger.error(f"cleanup_votes error: {error}")
            try:
                await interaction.response.send_message(
                    f"Command error: {str(error)}",
                    ephemeral=True
                )
            except:
                pass


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(VoteCog(bot))
