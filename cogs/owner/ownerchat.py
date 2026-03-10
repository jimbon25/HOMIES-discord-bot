"""Owner-specific chat responses and interactions"""
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class OwnerChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = None
        self.loaded = False
        
        # Owner-specific message triggers and responses
        # Format: trigger_keyword (lowercase) → response message(s)
        self.owner_responses = {
            'hi': 'Hi Brother, how feel you today?',
            'hello': 'Hi Brother, how feel you today?',
            'yo': 'Yo! What\'s up bro?',
            'good': 'Nice. Glad to hear it!',
            'thanks': 'Anytime bro! Always here for you.',
            'thank you': 'Anytime bro! Always here for you.',
            'ok': 'Got it. Let me know if you need anything.',
            'bye': 'Peace out bro! See you later.',
            'goodbye': 'Peace out bro! See you later.',
        }
    
    async def load_owner_id(self):
        """Load owner ID from bot application info"""
        if self.loaded:
            return
        
        try:
            app_info = await self.bot.application_info()
            self.owner_id = app_info.owner.id
            logger.info(f"✅ OwnerChat: Loaded owner ID {self.owner_id}")
            self.loaded = True
        except Exception as e:
            logger.error(f"❌ OwnerChat: Failed to load owner ID: {e}")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Load owner ID when bot is ready"""
        if not self.loaded:
            await self.load_owner_id()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for owner messages and respond accordingly"""
        # Ignore if bot message or not ready
        if message.author.bot or not self.loaded or not self.owner_id:
            return
        
        # Only respond to owner in DMs or anywhere
        if message.author.id != self.owner_id:
            return
        
        # Get message content in lowercase for matching
        content = message.content.strip().lower()
        
        # Check if message matches any trigger
        for trigger, response in self.owner_responses.items():
            if content == trigger or content.startswith(trigger + ' '):
                try:
                    await message.reply(response, mention_author=False)
                    logger.info(f"🗨️  OwnerChat: Owner triggered '{trigger}' → responded")
                except Exception as e:
                    logger.error(f"❌ OwnerChat: Error responding to owner: {e}")
                break  # Only respond once per message
    
    # Easy method to add new responses dynamically if needed
    def add_response(self, trigger: str, response: str):
        """Add a new trigger-response pair"""
        self.owner_responses[trigger.lower()] = response
        logger.info(f"➕ OwnerChat: Added response for '{trigger}'")
    
    def remove_response(self, trigger: str):
        """Remove a trigger-response pair"""
        trigger_lower = trigger.lower()
        if trigger_lower in self.owner_responses:
            del self.owner_responses[trigger_lower]
            logger.info(f"➖ OwnerChat: Removed response for '{trigger}'")
    
    def get_responses(self) -> dict:
        """Get all current responses"""
        return self.owner_responses.copy()


async def setup(bot):
    await bot.add_cog(OwnerChat(bot))
    logger.info("✅ OwnerChat cog loaded")
