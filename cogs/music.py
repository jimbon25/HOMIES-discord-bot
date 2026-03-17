"""Music Player - Play local music files with queue management"""
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import os
import random
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class MusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_dir = Path("music")
        self.music_dir.mkdir(exist_ok=True)
        
        # Per-guild music state
        self.queue = {}  # guild_id -> list of song paths
        self.current_song = {}  # guild_id -> current song index
        self.voice_client = {}  # guild_id -> VoiceClient
        self.is_paused = {}  # guild_id -> bool
        self.loop_mode = {}  # guild_id -> "off" | "song" | "queue"
        self.shuffle_mode = {}  # guild_id -> bool
        self.now_playing_message = {}  # guild_id -> message for updates
    
    def get_songs(self) -> list:
        """Get list of available music files"""
        if not self.music_dir.exists():
            return []
        
        valid_formats = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.opus'}
        songs = []
        
        for file in self.music_dir.iterdir():
            if file.is_file() and file.suffix.lower() in valid_formats:
                songs.append(file)
        
        return sorted(songs)
    
    def init_guild(self, guild_id: int):
        """Initialize music state for a guild"""
        if guild_id not in self.queue:
            self.queue[guild_id] = []
            self.current_song[guild_id] = 0
            self.is_paused[guild_id] = False
            self.loop_mode[guild_id] = "off"
            self.shuffle_mode[guild_id] = False
    
    @app_commands.command(name="mplay", description="Select and play a song from music folder")
    async def mplay(self, interaction: discord.Interaction):
        """Play music - select from available songs"""
        
        # Check if user in voice
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ You must be in a voice channel first",
                ephemeral=True
            )
            return
        
        guild_id = interaction.guild.id
        self.init_guild(guild_id)
        
        # Get all available songs
        available_songs = self.get_songs()
        if not available_songs:
            await interaction.response.send_message(
                "❌ No music files found in library",
                ephemeral=True
            )
            return
        
        # Show selection buttons (max 5 songs at a time)
        view = SongSelectionView(self, interaction, available_songs[:5])
        
        song_list = "\n".join([f"**{i+1}.** {s.stem}" for i, s in enumerate(available_songs[:5])])
        embed = discord.Embed(
            title="🎵 Select a Song",
            description=song_list,
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def play_selected_song(self, interaction: discord.Interaction, selected_song: Path):
        """Internal method to play a selected song"""
        guild_id = interaction.guild.id
        self.init_guild(guild_id)
        
        try:
            # Connect to voice if not already
            if guild_id not in self.voice_client or not self.voice_client[guild_id].is_connected():
                voice_client = await interaction.user.voice.channel.connect()
                self.voice_client[guild_id] = voice_client
            
            # Play the song
            voice_client = self.voice_client[guild_id]
            
            # Create audio source with FFmpeg
            source = discord.FFmpegPCMAudio(
                str(selected_song),
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn"
            )
            
            def after_play(error):
                """Callback when song finishes"""
                if error:
                    logger.error(f"Playback error: {error}")
                
                # Handle queue/loop
                if self.loop_mode[guild_id] == "song":
                    # Restart same song
                    self.play_song(guild_id)
                elif self.loop_mode[guild_id] == "queue":
                    # Move to next, loop back at end
                    self.current_song[guild_id] = (self.current_song[guild_id] + 1) % len(self.queue[guild_id])
                    self.play_song(guild_id)
                else:
                    # Next song
                    if self.current_song[guild_id] + 1 < len(self.queue[guild_id]):
                        self.current_song[guild_id] += 1
                        self.play_song(guild_id)
            
            # Set queue
            self.queue[guild_id] = [selected_song]
            self.current_song[guild_id] = 0
            
            voice_client.play(source, after=after_play)
            self.is_paused[guild_id] = False
            
            # Create now playing embed and buttons
            await self.show_now_playing(interaction, guild_id, defer=True)
        
        except Exception as e:
            logger.error(f"Error playing song: {e}")
            await interaction.followup.send(f"❌ Error playing song: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="mstop", description="Stop music playback")
    async def stop(self, interaction: discord.Interaction):
        """Stop playback and disconnect"""
        guild_id = interaction.guild.id
        self.init_guild(guild_id)
        
        if guild_id not in self.voice_client or not self.voice_client[guild_id].is_connected():
            await interaction.response.send_message(
                "❌ Bot is not playing music",
                ephemeral=True
            )
            return
        
        try:
            voice_client = self.voice_client[guild_id]
            voice_client.stop()
            await voice_client.disconnect()
            
            # Cleanup
            self.queue[guild_id] = []
            self.current_song[guild_id] = 0
            
            embed = discord.Embed(
                title="⏹️ Music Stopped",
                description="Playback stopped and disconnected",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            logger.error(f"Error stopping music: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def show_now_playing(self, interaction: discord.Interaction, guild_id: int, defer: bool = True):
        """Show now playing embed with control buttons"""
        if not self.queue[guild_id]:
            return
        
        current_song = self.queue[guild_id][self.current_song[guild_id]]
        
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{current_song.stem}**",
            color=discord.Color.green()
        )
        
        # Add status info
        status = "⏸️ Paused" if self.is_paused[guild_id] else "▶️ Playing"
        loop_text = self.loop_mode[guild_id].capitalize()
        shuffle_text = "✅ On" if self.shuffle_mode[guild_id] else "❌ Off"
        
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Loop", value=loop_text, inline=True)
        embed.add_field(name="Shuffle", value=shuffle_text, inline=True)
        
        if len(self.queue[guild_id]) > 1:
            embed.add_field(
                name="Queue",
                value=f"{self.current_song[guild_id] + 1} / {len(self.queue[guild_id])}",
                inline=True
            )
        
        # Create control buttons
        view = MusicControlView(self, guild_id, interaction)
        
        if defer:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.defer()
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def play_song(self, guild_id: int):
        """Internal method to play song from queue"""
        if guild_id not in self.voice_client or not self.queue[guild_id]:
            return
        
        voice_client = self.voice_client[guild_id]
        if not voice_client.is_connected():
            return
        
        song_path = self.queue[guild_id][self.current_song[guild_id]]
        
        try:
            source = discord.FFmpegPCMAudio(
                str(song_path),
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn"
            )
            voice_client.play(source)
            self.is_paused[guild_id] = False
        except Exception as e:
            logger.error(f"Error playing song: {e}")




class SongSelectionView(View):
    """Buttons for selecting a song to play"""
    
    def __init__(self, music_cog: MusicPlayer, interaction: discord.Interaction, songs: list):
        super().__init__(timeout=30)
        self.music_cog = music_cog
        self.interaction = interaction
        self.songs = songs
        
        # Create buttons for each song
        for i, song in enumerate(songs):
            button = discord.ui.Button(
                label=f"{i+1}. {song.stem[:20]}",
                style=discord.ButtonStyle.primary,
                custom_id=f"song_{i}"
            )
            button.callback = self.create_callback(i, song)
            self.add_item(button)
    
    def create_callback(self, index: int, song: Path):
        """Create callback for song selection"""
        async def callback(button_interaction: discord.Interaction):
            await button_interaction.response.defer()
            await self.music_cog.play_selected_song(button_interaction, song)
        return callback


class MusicControlView(View):
    """Interactive buttons for music control"""
    
    def __init__(self, music_cog: MusicPlayer, guild_id: int, interaction: discord.Interaction):
        super().__init__(timeout=None)
        self.music_cog = music_cog
        self.guild_id = guild_id
        self.interaction = interaction
    
    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.primary)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Pause playback"""
        if self.guild_id not in self.music_cog.voice_client:
            await interaction.response.send_message("❌ No music playing", ephemeral=True)
            return
        
        voice_client = self.music_cog.voice_client[self.guild_id]
        if voice_client.is_playing():
            voice_client.pause()
            self.music_cog.is_paused[self.guild_id] = True
            await interaction.response.send_message("⏸️ Paused", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Not playing", ephemeral=True)
    
    @discord.ui.button(label="▶️ Resume", style=discord.ButtonStyle.primary)
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Resume playback"""
        if self.guild_id not in self.music_cog.voice_client:
            await interaction.response.send_message("❌ No music playing", ephemeral=True)
            return
        
        voice_client = self.music_cog.voice_client[self.guild_id]
        if voice_client.is_paused():
            voice_client.resume()
            self.music_cog.is_paused[self.guild_id] = False
            await interaction.response.send_message("▶️ Resumed", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Not paused", ephemeral=True)
    
    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Skip to next song"""
        if self.guild_id not in self.music_cog.voice_client or not self.music_cog.queue[self.guild_id]:
            await interaction.response.send_message("❌ Queue is empty", ephemeral=True)
            return
        
        voice_client = self.music_cog.voice_client[self.guild_id]
        voice_client.stop()
        
        # Move to next
        self.music_cog.current_song[self.guild_id] = (self.music_cog.current_song[self.guild_id] + 1) % len(self.music_cog.queue[self.guild_id])
        self.music_cog.play_song(self.guild_id)
        
        song = self.music_cog.queue[self.guild_id][self.music_cog.current_song[self.guild_id]]
        await interaction.response.send_message(f"⏭️ Skipped to: **{song.stem}**", ephemeral=True)
    
    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary)
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle shuffle mode"""
        self.music_cog.shuffle_mode[self.guild_id] = not self.music_cog.shuffle_mode[self.guild_id]
        status = "Enabled" if self.music_cog.shuffle_mode[self.guild_id] else "Disabled"
        await interaction.response.send_message(f"🔀 Shuffle {status}", ephemeral=True)
    
    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary)
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cycle loop modes: off -> song -> queue -> off"""
        modes = ["off", "song", "queue"]
        current = self.music_cog.loop_mode[self.guild_id]
        next_mode = modes[(modes.index(current) + 1) % len(modes)]
        self.music_cog.loop_mode[self.guild_id] = next_mode
        
        mode_text = {
            "off": "❌ Loop Off",
            "song": "🔂 Loop Song",
            "queue": "🔁 Loop Queue"
        }
        
        await interaction.response.send_message(mode_text[next_mode], ephemeral=True)
    
    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop music and disconnect"""
        if self.guild_id not in self.music_cog.voice_client:
            await interaction.response.send_message("❌ Not connected", ephemeral=True)
            return
        
        voice_client = self.music_cog.voice_client[self.guild_id]
        voice_client.stop()
        await voice_client.disconnect()
        
        self.music_cog.queue[self.guild_id] = []
        self.music_cog.current_song[self.guild_id] = 0
        
        await interaction.response.send_message("⏹️ Stopped and disconnected", ephemeral=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(MusicPlayer(bot))
