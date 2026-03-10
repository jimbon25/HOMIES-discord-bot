"""Owner-specific chat responses and interactions"""
import discord
from discord.ext import commands
import logging
import aiohttp
import os

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
        
        # Owner-specific message triggers and responses
        # Format: trigger_keyword (lowercase) → response message(s)
        # Text responses
        self.owner_responses = {
            'homies': 'Hi fein kamu kembali! ada yang bisa aku bantu hari ini?',
            'tidak ada aman saja': 'Hahaha aman-aman saja bro! Santai aja, aku di sini buat bantu kamu kapan pun kamu butuh! 😎',
            'iya sayang': 'Aww, iya sayang! wkwkwk, kamu lucu banget! Ada yang bisa aku bantu hari ini?',
            'gak ada njir': 'Hahaha yauda kalau gitu kalau ada yang mau kamu tanyain atau butuh bantuan, jangan ragu untuk tanya ya! 😊',
            'fast respon bgt gak kayak dia': 'Hahaha iya dong feinada! Aku selalu siap sedia untuk kamu, beda banget sama dia yang suka lama responnya wkwkwk. Ada yang bisa aku bantu hari ini?',
            'aku cantik atau tidak': 'Hahaha kamu cantik banget! Gak usah ragu sama penampilanmu, yang penting kamu nyaman dengan dirimu sendiri! 😎',
            'makasih': 'Sama-sama cantik! kalau ada pertanyaan atau butuh bantuan, jangan ragu untuk tanya ya! 😊',
            'hi': 'Hi, you comeback brother?',
            'hello': 'Hi Brother, how feel you today?',
            'yo': 'Yo! What\'s up bro?',
            'good': 'Nice. Glad to hear it!',
            'thanks': 'Anytime bro! Always here for you.',
            'thank you': 'Anytime bro! Always here for you.',
            'ok': 'Got it. Let me know if you need anything.',
            'bye': 'Peace out bro! See you later.',
            'goodbye': 'Peace out bro! See you later.',
            'kick feinada': 'Okay bro, kicking Feinada... Just kidding, I can\'t do that!',
            'halo jawab pertanyaanku dengan bahasa': 'Haha baik Mahoraga | DONTPINGME ada pertanyaan apa hari ini?',
            'kapan pd3': 'Hahaha kapan perang dunia ke 3? aku tidak tahu mungkin bisa di jelaskan konteksnya dalam pembahasan apa Mahoraga | DONTPINGME!',
            'aku capek': 'Istirahat dulu bro, kesehatan itu penting. Tidur yang cukup ya! 💪',
            'baiklah': 'Baiklah! tidur yang cukup ya bro, jangan begadang terus! 😴',
            'boribel': 'Haha Boribel! Meme klasik selamanya di hati kita 😂',
            'siapa lu': 'Gua bot, temen setia lo bro! Siapa nama gua? 🤖',
            'bot apa': 'Gua bot Discord lo! Bisa respond chat, fetch images, dan apapun yang lo butuh!',
            'giliran siapa': 'Giliran lo untuk tidur bro 😴 Jangan begadang terus!',
            'emang aku orang yang apa': 'Lo orang yang paling penting buat gua bro! 💙',
            'mau apa': 'Mau bantu lo dengan apapun yang lo butuh! Ada yang bisa gua lakukan?',
            'udah berapa jam': 'Waktu sudah berjalan bro. Jangan lupa istirahat dan makan! ⏰',
            'siapa yang ngebully': 'Siapa yang berani? Gua siap defend lo! 🛡️',
            'ada server baru': 'Server baru? Sounds interesting! Lo pengen apa di server itu?',
            'jawab dengan bahasa indonesia': 'Baik Mahoraga | DONTPINGME, ada yang bisa saya bantu hari ini? Ada pertanyaan atau topik yang ingin dibahas?'
        }
        
        # Image triggers - will fetch from API or use fallback URLs
        # Format: trigger_keyword → (search_query, embed_title, embed_color)
        self.image_triggers = {
            'cat': ('cat', '🐱 Here\'s a cute cat for you', discord.Color.orange()),
            'cats': ('cat', '🐱 Here\'s a cute cat for you', discord.Color.orange()),
            'dog': ('dog', '🐕 Here\'s a cute dog for you', discord.Color.blurple()),
            'dogs': ('dog', '🐕 Here\'s a cute dog for you', discord.Color.blurple()),
            'pic': ('nature', '🌅 Here\'s a nice pic for you', discord.Color.green()),
            'photo': ('nature', '🌅 Here\'s a nice pic for you', discord.Color.green()),
        }
    
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
        
        # Check if message matches any text trigger first
        for trigger, response in self.owner_responses.items():
            if content == trigger or content.startswith(trigger + ' '):
                try:
                    await message.reply(response, mention_author=False)
                    logger.info(f"🗨️  OwnerChat: Owner triggered '{trigger}' → responded")
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
                        logger.info(f"🖼️  OwnerChat: Owner triggered '{trigger}' → sent image")
                    else:
                        await message.reply(f"Sorry bro, couldn't fetch a {query} image right now. Try again later.", mention_author=False)
                except Exception as e:
                    logger.error(f"❌ OwnerChat: Error fetching image for '{trigger}': {e}")
                    await message.reply(f"Error fetching image: {str(e)}", mention_author=False)
                return
    
    # Easy method to add new responses dynamically if needed
    def add_response(self, trigger: str, response: str):
        """Add a new trigger-response pair"""
        self.owner_responses[trigger.lower()] = response
        logger.info(f"➕ OwnerChat: Added text response for '{trigger}'")
    
    def remove_response(self, trigger: str):
        """Remove a trigger-response pair"""
        trigger_lower = trigger.lower()
        if trigger_lower in self.owner_responses:
            del self.owner_responses[trigger_lower]
            logger.info(f"➖ OwnerChat: Removed text response for '{trigger}'")
    
    def get_responses(self) -> dict:
        """Get all current text responses"""
        return self.owner_responses.copy()
    
    def add_image_trigger(self, trigger: str, search_query: str, title: str = None, color = None):
        """Add a new image trigger"""
        if color is None:
            color = discord.Color.blue()
        if title is None:
            title = f"Here's a {search_query} for you"
        
        self.image_triggers[trigger.lower()] = (search_query, title, color)
        logger.info(f"➕ OwnerChat: Added image trigger for '{trigger}' (query: {search_query})")
    
    def remove_image_trigger(self, trigger: str):
        """Remove an image trigger"""
        trigger_lower = trigger.lower()
        if trigger_lower in self.image_triggers:
            del self.image_triggers[trigger_lower]
            logger.info(f"➖ OwnerChat: Removed image trigger for '{trigger}'")
    
    def get_image_triggers(self) -> dict:
        """Get all current image triggers"""
        return self.image_triggers.copy()


async def setup(bot):
    await bot.add_cog(OwnerChat(bot))
    logger.info("✅ OwnerChat cog loaded")
