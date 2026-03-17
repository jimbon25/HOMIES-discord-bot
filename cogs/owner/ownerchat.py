"""Owner-specific chat responses and interactions"""
import discord
from discord.ext import commands, tasks
import logging
import aiohttp
import os
import json
from pathlib import Path
from utils import safe_save_json

logger = logging.getLogger(__name__)

class OwnerChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_ids = set()  # Support multiple owners
        self.loaded = False
        
        # Load additional owner IDs from .env (comma-separated)
        additional_owners_str = os.getenv('ADDITIONAL_OWNER_IDS', '')
        self.additional_owner_ids = set()
        if additional_owners_str:
            try:
                self.additional_owner_ids = {int(uid.strip()) for uid in additional_owners_str.split(',') if uid.strip()}
            except ValueError:
                logger.warning("⚠️  Invalid ADDITIONAL_OWNER_IDS in .env. Should be comma-separated numbers.")
        
        # Unsplash API key for image fetching (optional)
        self.unsplash_api_key = os.getenv('UNSPLASH_API_KEY', None)
        self.giphy_api_key = os.getenv('GIPHY_API_KEY', None)
        
        # Path to JSON file with responses
        self.json_path = Path(__file__).parent / "owner_responses.json"
        self.json_last_modified = None  # Track file modification time
        
        # Load responses from JSON - owner-specific only
        self.owner_specific_responses = {}  # {owner_id: {trigger: response}}
        self.image_triggers = {}
        self.load_responses_from_json()
        
        # Start auto-reload task
        self.auto_reload_responses.start()
    
    def load_responses_from_json(self):
        """Load owner-specific and image responses from JSON file"""
        try:
            if not self.json_path.exists():
                logger.error(f"❌ OwnerChat: JSON file not found at {self.json_path}")
                return
            
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load owner-specific responses
            owners_data = data.get('owners', {})
            self.owner_specific_responses = {}
            for owner_id_str, owner_data in owners_data.items():
                try:
                    owner_id = int(owner_id_str)
                    responses = owner_data.get('responses', {})
                    self.owner_specific_responses[owner_id] = responses
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️  Invalid owner ID in JSON: {owner_id_str}")
            
            # Load image triggers - convert color int back to discord.Color
            raw_image_triggers = data.get('image_triggers', {})
            self.image_triggers = {}
            for trigger, config in raw_image_triggers.items():
                color = discord.Color(config.get('color', 0))  # Convert int to Color
                self.image_triggers[trigger] = (
                    config.get('query', trigger),
                    config.get('title', 'Here you go'),
                    color
                )
            
            total_owner_responses = sum(len(r) for r in self.owner_specific_responses.values())
            logger.info(f"✅ OwnerChat: Loaded {total_owner_responses} owner-specific responses + {len(self.image_triggers)} image triggers from JSON")
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ OwnerChat: Invalid JSON in {self.json_path}: {e}")
        except Exception as e:
            logger.error(f"❌ OwnerChat: Error loading responses from JSON: {e}")
    
    @tasks.loop(seconds=5)
    async def auto_reload_responses(self):
        """Auto-reload responses if JSON file is modified"""
        try:
            if not self.json_path.exists():
                return
            
            # Get current file modification time
            current_mtime = self.json_path.stat().st_mtime
            
            # Check if file has been modified
            if self.json_last_modified is None:
                # First time check
                self.json_last_modified = current_mtime
            elif current_mtime > self.json_last_modified:
                # File has been modified, reload it
                logger.info("🔄 OwnerChat: Detected JSON file change, reloading...")
                self.json_last_modified = current_mtime
                self.load_responses_from_json()
        except Exception as e:
            logger.error(f"❌ OwnerChat: Error in auto-reload task: {e}")
    
    @auto_reload_responses.before_loop
    async def before_auto_reload(self):
        """Wait for bot to be ready before starting auto-reload"""
        await self.bot.wait_until_ready()
    
    async def load_owner_id(self):
        """Load owner IDs from bot application info"""
        if self.loaded:
            return
        
        try:
            app_info = await self.bot.application_info()
            # Add primary owner from app info
            self.owner_ids.add(app_info.owner.id)
            # Add additional owners
            self.owner_ids.update(self.additional_owner_ids)
            logger.info(f"✅ OwnerChat: Loaded owner IDs {self.owner_ids}")
            self.loaded = True
        except Exception as e:
            logger.error(f"❌ OwnerChat: Failed to load owner IDs: {e}")
    
    async def fetch_image_from_unsplash(self, query: str) -> str:
        """Fetch random image URL from Unsplash API"""
        if not self.unsplash_api_key:
            logger.warning("⚠️  Unsplash API key not set. Set UNSPLASH_API_KEY in .env")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.unsplash.com/photos/random"
                params = {
                    'query': query,
                    'count': 1,
                    'client_id': self.unsplash_api_key
                }
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list) and len(data) > 0:
                            return data[0]['urls']['regular']
                        elif isinstance(data, dict):
                            return data.get('urls', {}).get('regular')
        except Exception as e:
            logger.error(f"❌ OwnerChat: Error fetching from Unsplash: {e}")
        
        return None
    
    async def fetch_gif_from_giphy(self, query: str) -> str:
        """Fetch random GIF from Giphy API"""
        if not self.giphy_api_key:
            logger.warning("⚠️  Giphy API key not set. Set GIPHY_API_KEY in .env")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.giphy.com/v1/gifs/random"
                params = {
                    'q': query,
                    'api_key': self.giphy_api_key
                }
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('data', {}).get('images', {}).get('original', {}).get('url')
        except Exception as e:
            logger.error(f"❌ OwnerChat: Error fetching from Giphy: {e}")
        
        return None
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Load owner ID when bot is ready"""
        if not self.loaded:
            await self.load_owner_id()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for owner messages and respond accordingly"""
        # Ignore if bot message or not ready
        if message.author.bot or not self.loaded or not self.owner_ids:
            return
        
        # Only respond to owners
        if message.author.id not in self.owner_ids:
            return
        
        # Get message content in lowercase for matching
        content = message.content.strip().lower()
        
        # Check owner-specific responses (priority)
        owner_responses = self.owner_specific_responses.get(message.author.id, {})
        for trigger, response in owner_responses.items():
            if content == trigger or content.startswith(trigger + ' '):
                try:
                    await message.reply(response, mention_author=False)
                    logger.info(f"🗨️  OwnerChat: Owner {message.author.id} triggered '{trigger}'")
                except Exception as e:
                    logger.error(f"❌ OwnerChat: Error responding to owner: {e}")
                return  # Only respond once per message
        
        # Check if message matches any image trigger
        for trigger, (query, title, color) in self.image_triggers.items():
            if content == trigger or content.startswith(trigger + ' '):
                try:
                    # Try to fetch image
                    image_url = await self.fetch_image_from_unsplash(query)
                    
                    if image_url:
                        embed = discord.Embed(
                            title=title,
                            color=color
                        )
                        embed.set_image(url=image_url)
                        await message.reply(embed=embed, mention_author=False)
                        logger.info(f"🖼️  OwnerChat: Owner {message.author.id} triggered '{trigger}' → sent image")
                    else:
                        await message.reply(f"Sorry, couldn't fetch a {query} image right now. Try again later.", mention_author=False)
                except Exception as e:
                    logger.error(f"❌ OwnerChat: Error fetching image for '{trigger}': {e}")
                    await message.reply(f"Error fetching image: {str(e)}", mention_author=False)
                return
    
    # Easy method to add new responses dynamically if needed
    def add_owner_response(self, owner_id: int, trigger: str, response: str):
        """Add a new trigger-response pair to specific owner"""
        if owner_id not in self.owner_specific_responses:
            self.owner_specific_responses[owner_id] = {}
        
        trigger_lower = trigger.lower()
        self.owner_specific_responses[owner_id][trigger_lower] = response
        self.save_responses_to_json()
        logger.info(f"➕ OwnerChat: Added response for owner {owner_id} trigger '{trigger}'")
    
    def remove_owner_response(self, owner_id: int, trigger: str):
        """Remove a specific owner's trigger-response pair"""
        trigger_lower = trigger.lower()
        if owner_id in self.owner_specific_responses and trigger_lower in self.owner_specific_responses[owner_id]:
            del self.owner_specific_responses[owner_id][trigger_lower]
            self.save_responses_to_json()
            logger.info(f"➖ OwnerChat: Removed response for owner {owner_id} trigger '{trigger}'")
    
    def get_responses(self) -> dict:
        """Get all current responses"""
        return self.owner_specific_responses.copy()
    
    def add_image_trigger(self, trigger: str, search_query: str, title: str = None, color = None):
        """Add a new image trigger and save to JSON"""
        if color is None:
            color = discord.Color.blue()
        if title is None:
            title = f"Here's a {search_query} for you"
        
        trigger_lower = trigger.lower()
        self.image_triggers[trigger_lower] = (search_query, title, color)
        self.save_responses_to_json()
        logger.info(f"➕ OwnerChat: Added image trigger for '{trigger}' (query: {search_query})")
    
    def remove_image_trigger(self, trigger: str):
        """Remove an image trigger and save to JSON"""
        trigger_lower = trigger.lower()
        if trigger_lower in self.image_triggers:
            del self.image_triggers[trigger_lower]
            self.save_responses_to_json()
            logger.info(f"➖ OwnerChat: Removed image trigger for '{trigger}'")
    
    def get_image_triggers(self) -> dict:
        """Get all current image triggers"""
        return self.image_triggers.copy()
    
    def save_responses_to_json(self):
        """Save current responses to JSON file"""
        try:
            data = {
                'owners': {},
                'image_triggers': {}
            }
            
            # Convert owner-specific responses back to format suitable for JSON
            for owner_id, responses in self.owner_specific_responses.items():
                data['owners'][str(owner_id)] = {
                    'responses': responses
                }
            
            # Convert discord.Color objects to int for JSON serialization
            for trigger, (query, title, color) in self.image_triggers.items():
                data['image_triggers'][trigger] = {
                    'query': query,
                    'title': title,
                    'color': color.value  # Convert discord.Color to int
                }
            
            safe_save_json(data, self.json_path)
            
            logger.info(f"✅ OwnerChat: Saved responses to JSON")
        except Exception as e:
            logger.error(f"❌ OwnerChat: Error saving to JSON: {e}")
    
    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload_owner_responses(self, ctx):
        """Reload owner responses from JSON file (owner only)"""
        self.load_responses_from_json()
        total_responses = sum(len(r) for r in self.owner_specific_responses.values())
        await ctx.send(f"✅ Reloaded! Total responses: {total_responses}, Image triggers: {len(self.image_triggers)}")
        logger.info(f"🔄 OwnerChat: Reloaded from JSON")
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.auto_reload_responses.cancel()
        logger.info("✅ OwnerChat: Cleanup complete")


async def setup(bot):
    await bot.add_cog(OwnerChat(bot))
    logger.info("✅ OwnerChat cog loaded")
