"""Tic Tac Toe Game"""
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import random
import logging

logger = logging.getLogger(__name__)


class TicTacToeGame:
    """Tic Tac Toe game logic"""
    
    def __init__(self, player_x: discord.User, player_o: discord.User = None, vs_bot: bool = False):
        self.board = [None] * 9  # 0-8 positions
        self.player_x = player_x
        self.player_o = player_o or (self if vs_bot else None)
        self.current_player = "X"
        self.vs_bot = vs_bot
        self.game_over = False
        self.winner = None
    
    def make_move(self, position: int, player: str) -> bool:
        """Make a move on the board"""
        if self.board[position] is not None:
            return False
        self.board[position] = player
        return True
    
    def get_board_display(self) -> str:
        """Get board as string for display (kept for reference)"""
        symbols = {None: "⬜", "X": "❌", "O": "⭕"}
        board_str = ""
        for i in range(9):
            board_str += symbols[self.board[i]] + " "
            if (i + 1) % 3 == 0:
                board_str += "\n"
        return board_str.strip()
    
    def check_winner(self) -> str:
        """Check for winner. Returns 'X', 'O', 'Draw', or None"""
        # Winning combinations
        winning_combos = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6]              # Diagonals
        ]
        
        for combo in winning_combos:
            if self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]] and self.board[combo[0]] is not None:
                return self.board[combo[0]]
        
        # Check for draw
        if all(cell is not None for cell in self.board):
            return "Draw"
        
        return None
    
    def get_available_moves(self) -> list:
        """Get list of available positions"""
        return [i for i in range(9) if self.board[i] is None]
    
    def get_bot_move(self) -> int:
        """Get bot's move (simple AI: random available or winning move)"""
        available = self.get_available_moves()
        
        # Check if bot can win
        for move in available:
            self.board[move] = "O"
            if self.check_winner() == "O":
                self.board[move] = None
                return move
            self.board[move] = None
        
        # Check if need to block player
        for move in available:
            self.board[move] = "X"
            if self.check_winner() == "X":
                self.board[move] = None
                return move
            self.board[move] = None
        
        # Take center if available
        if 4 in available:
            return 4
        
        # Take corner if available
        corners = [0, 2, 6, 8]
        corner_available = [c for c in corners if c in available]
        if corner_available:
            return random.choice(corner_available)
        
        # Random move
        return random.choice(available)
    
    def toggle_player(self):
        """Switch to next player"""
        self.current_player = "O" if self.current_player == "X" else "X"


class TicTacToeView(View):
    """View for Tic Tac Toe board - 3x3 grid layout"""
    
    def __init__(self, game: TicTacToeGame, interaction: discord.Interaction):
        super().__init__(timeout=180)
        self.game = game
        self.initial_interaction = interaction
        
        # Create buttons in 3x3 grid
        # Row 1: positions 0, 1, 2
        for i in range(3):
            button = Button(label="⬜", custom_id=f"ttt_{i}", style=discord.ButtonStyle.secondary, row=0)
            button.callback = self.make_move
            self.add_item(button)
        
        # Row 2: positions 3, 4, 5
        for i in range(3, 6):
            button = Button(label="⬜", custom_id=f"ttt_{i}", style=discord.ButtonStyle.secondary, row=1)
            button.callback = self.make_move
            self.add_item(button)
        
        # Row 3: positions 6, 7, 8
        for i in range(6, 9):
            button = Button(label="⬜", custom_id=f"ttt_{i}", style=discord.ButtonStyle.secondary, row=2)
            button.callback = self.make_move
            self.add_item(button)
    
    def update_board_buttons(self):
        """Update button labels and states"""
        for i, child in enumerate(self.children):
            if isinstance(child, Button):
                symbol = self.game.board[i]
                if symbol == "X":
                    child.label = "❌"
                    child.disabled = True
                elif symbol == "O":
                    child.label = "⭕"
                    child.disabled = True
                else:
                    child.label = "⬜"
                    child.disabled = False
                
                # Set button style based on state
                if symbol is None:
                    child.style = discord.ButtonStyle.secondary
                else:
                    child.style = discord.ButtonStyle.success
    
    async def make_move(self, interaction: discord.Interaction):
        """Handle button click"""
        if interaction.user.id != self.game.player_x.id:
            await interaction.response.send_message(
                "You're not in this game!",
                ephemeral=True
            )
            return
        
        position = int(interaction.custom_id.split("_")[1])
        
        if not self.game.make_move(position, "X"):
            await interaction.response.send_message(
                "That square is already taken!",
                ephemeral=True
            )
            return
        
        # Update buttons immediately
        self.update_board_buttons()
        
        winner = self.game.check_winner()
        
        if winner == "X":
            self.game.game_over = True
            self.game.winner = "X"
            for child in self.children[:9]:  # Disable only game buttons
                if isinstance(child, Button):
                    child.disabled = True
            embed = discord.Embed(
                title="🎉 You Win!",
                description="Congratulations! You got 3 in a row!",
                color=discord.Color.gold()
            )
            play_again_view = PlayAgainView(self.game.player_x, self.game.player_o, self.game.vs_bot)
            await interaction.response.edit_message(embed=embed, view=play_again_view)
            return
        elif winner == "Draw":
            self.game.game_over = True
            for child in self.children[:9]:  # Disable only game buttons
                if isinstance(child, Button):
                    child.disabled = True
            embed = discord.Embed(
                title="🤝 It's a Draw!",
                description="No more moves available - everyone had a fair chance!",
                color=discord.Color.gold()
            )
            play_again_view = PlayAgainView(self.game.player_x, self.game.player_o, self.game.vs_bot)
            await interaction.response.edit_message(embed=embed, view=play_again_view)
            return
        
        # Bot's turn
        if self.game.vs_bot:
            try:
                bot_move = self.game.get_bot_move()
                self.game.make_move(bot_move, "O")
                
                winner = self.game.check_winner()
                if winner == "O":
                    self.game.game_over = True
                    self.game.winner = "O"
                    for child in self.children[:9]:  # Disable only game buttons
                        if isinstance(child, Button):
                            child.disabled = True
                    embed = discord.Embed(
                        title="🤖 Bot Wins!",
                        description="Bot got 3 in a row! Better luck next time!",
                        color=discord.Color.gold()
                    )
                    play_again_view = PlayAgainView(self.game.player_x, self.game.player_o, self.game.vs_bot)
                    await interaction.response.edit_message(embed=embed, view=play_again_view)
                    return
                elif winner == "Draw":
                    self.game.game_over = True
                    for child in self.children[:9]:  # Disable only game buttons
                        if isinstance(child, Button):
                            child.disabled = True
                    embed = discord.Embed(
                        title="🤝 It's a Draw!",
                        description="No more moves available - everyone had a fair chance!",
                        color=discord.Color.gold()
                    )
                    play_again_view = PlayAgainView(self.game.player_x, self.game.player_o, self.game.vs_bot)
                    await interaction.response.edit_message(embed=embed, view=play_again_view)
                    return
            except Exception as e:
                logger.error(f"Error during bot move: {e}")
        else:
            self.game.toggle_player()
        
        self.update_board_buttons()
        embed = self.get_game_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def get_game_embed(self) -> discord.Embed:
        """Create game embed"""
        current_text = "Your turn - Click a square ⬜" if self.game.current_player == "X" else "🤖 Bot is playing..."
        
        embed = discord.Embed(
            title="Tic Tac Toe",
            description=current_text,
            color=discord.Color.blue()
        )
        return embed
    
    async def on_timeout(self):
        """Called when view times out"""
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True


class PlayAgainView(View):
    """View for play again button"""
    
    def __init__(self, player_x: discord.User, player_o: discord.User, vs_bot: bool):
        super().__init__(timeout=3600)
        self.player_x = player_x
        self.player_o = player_o
        self.vs_bot = vs_bot
    
    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.primary, emoji="🔄")
    async def play_again(self, interaction: discord.Interaction, button: Button):
        """Start a new game"""
        if interaction.user.id != self.player_x.id:
            await interaction.response.send_message(
                "Only the original player can start a new game!",
                ephemeral=True
            )
            return
        
        # Create new game
        game = TicTacToeGame(self.player_x, self.player_o, self.vs_bot)
        view = TicTacToeView(game, self.vs_bot)
        
        embed = view.get_game_embed()
        await interaction.response.edit_message(embed=embed, view=view)


class TicTacToeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="tictactoe", description="Play Tic Tac Toe")
    @app_commands.describe(opponent="Play against: bot or @member (default: bot)")
    async def tictactoe(self, interaction: discord.Interaction, opponent: discord.User = None):
        """Start a Tic Tac Toe game"""
        try:
            vs_bot = opponent is None
            player_o = None if vs_bot else opponent
            
            if not vs_bot and player_o.id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ You can't play against yourself!",
                    ephemeral=True
                )
                return
            
            game = TicTacToeGame(interaction.user, player_o, vs_bot)
            view = TicTacToeView(game, interaction)
            
            opponent_text = "🤖 Bot" if vs_bot else player_o.mention
            embed = discord.Embed(
                title="Tic Tac Toe",
                description=f"Playing vs: {opponent_text}\n\nClick ⬜ to place ❌",
                color=discord.Color.blue()
            )
            
            await interaction.response.send_message(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error in tictactoe command: {e}")
            await interaction.response.send_message(
                f"Error starting game: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    """Load the cog"""
    await bot.add_cog(TicTacToeCog(bot))
