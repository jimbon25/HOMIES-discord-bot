import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CryptoPrice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        self.cryptocompare_url = "https://min-api.cryptocompare.com/data"
        
        # Supported cryptocurrencies mapping
        # Maps user input to CoinGecko ID and CryptoCompare symbol
        self.crypto_ids = {
            "bitcoin": {"gecko": "bitcoin", "cc": "BTC"},
            "btc": {"gecko": "bitcoin", "cc": "BTC"},
            "ethereum": {"gecko": "ethereum", "cc": "ETH"},
            "eth": {"gecko": "ethereum", "cc": "ETH"},
            "cardano": {"gecko": "cardano", "cc": "ADA"},
            "ada": {"gecko": "cardano", "cc": "ADA"},
            "solana": {"gecko": "solana", "cc": "SOL"},
            "sol": {"gecko": "solana", "cc": "SOL"},
            "ripple": {"gecko": "ripple", "cc": "XRP"},
            "xrp": {"gecko": "ripple", "cc": "XRP"},
            "dogecoin": {"gecko": "dogecoin", "cc": "DOGE"},
            "doge": {"gecko": "dogecoin", "cc": "DOGE"},
            "litecoin": {"gecko": "litecoin", "cc": "LTC"},
            "ltc": {"gecko": "litecoin", "cc": "LTC"},
            "polkadot": {"gecko": "polkadot", "cc": "DOT"},
            "dot": {"gecko": "polkadot", "cc": "DOT"},
            "avalanche": {"gecko": "avalanche-2", "cc": "AVAX"},
            "avax": {"gecko": "avalanche-2", "cc": "AVAX"},
            "polygon": {"gecko": "matic-network", "cc": "MATIC"},
            "matic": {"gecko": "matic-network", "cc": "MATIC"},
            "arbitrum": {"gecko": "arbitrum", "cc": "ARB"},
            "arb": {"gecko": "arbitrum", "cc": "ARB"},
        }
    
    async def fetch_coingecko(self, crypto_id: str) -> dict:
        """Fetch crypto price from CoinGecko"""
        try:
            params = {
                "ids": crypto_id,
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.coingecko_url}/simple/price",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if crypto_id in data:
                            return {
                                "success": True,
                                "price": data[crypto_id].get("usd", 0),
                                "market_cap": data[crypto_id].get("usd_market_cap", 0),
                                "volume_24h": data[crypto_id].get("usd_24h_vol", 0),
                                "change_24h": data[crypto_id].get("usd_24h_change", 0),
                                "source": "CoinGecko"
                            }
                    return {"success": False}
        except Exception as e:
            logger.error(f"CoinGecko error: {e}")
            return {"success": False}
    

    
    async def fetch_cryptocompare(self, crypto_symbol: str) -> dict:
        """Fetch crypto price from CryptoCompare"""
        try:
            params = {
                "fsym": crypto_symbol.upper(),
                "tsyms": "USD"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.cryptocompare_url}/price",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "USD" in data:
                            return {
                                "success": True,
                                "price": float(data.get("USD", 0)),
                                "market_cap": 0,  # CryptoCompare /price doesn't include market cap
                                "volume_24h": 0,  # Would need different endpoint
                                "change_24h": 0,  # Would need different endpoint
                                "source": "CryptoCompare"
                            }
                    return {"success": False}
        except Exception as e:
            logger.error(f"CryptoCompare error: {e}")
            return {"success": False}
    
    async def get_crypto_price(self, crypto_name: str) -> tuple:
        """Get crypto price with fallback system (CoinGecko → CryptoCompare)"""
        # Normalize crypto name
        crypto_name = crypto_name.lower()
        crypto_data = self.crypto_ids.get(crypto_name)
        
        if not crypto_data:
            return None, "Cryptocurrency not found"
        
        gecko_id = crypto_data["gecko"]
        cc_symbol = crypto_data["cc"]
        
        # Try CoinGecko first (primary, has market cap)
        result = await self.fetch_coingecko(gecko_id)
        if result["success"]:
            return result, None
        
        logger.warning(f"CoinGecko failed for {gecko_id}, falling back to CryptoCompare")
        
        # Fallback to CryptoCompare (backup, price only)
        result = await self.fetch_cryptocompare(cc_symbol)
        if result["success"]:
            return result, None
        
        # All sources failed
        return None, "Unable to fetch price from all sources (CoinGecko & CryptoCompare unavailable)"
    
    def format_price(self, price: float) -> str:
        """Format price with proper notation"""
        if price >= 1000:
            return f"${price:,.2f}"
        elif price >= 1:
            return f"${price:.2f}"
        else:
            return f"${price:.8f}"
    
    @app_commands.command(name="price", description="Get cryptocurrency price")
    @app_commands.describe(cryptocurrency="Cryptocurrency name or symbol (e.g., bitcoin, btc, ethereum, eth)")
    async def price_command(self, interaction: discord.Interaction, cryptocurrency: str):
        """Get current cryptocurrency price with multi-source fallback"""
        
        # Check if user wants to see supported cryptos
        if cryptocurrency.lower() in ["list", "support", "supported", "help"]:
            embed = discord.Embed(
                title="💰 Supported Cryptocurrencies",
                description="Use `/price <name>` to get current price",
                color=discord.Color.gold()
            )
            
            # Group cryptos by category
            cryptos_list = []
            for name, data in self.crypto_ids.items():
                if name not in [v["gecko"] for v in self.crypto_ids.values() if isinstance(v, dict)]:
                    # Only show user-friendly names, not duplicates
                    continue
                gecko_id = data["gecko"]
                cc_symbol = data["cc"]
                if (gecko_id, cc_symbol) not in [(d["gecko"], d["cc"]) for _, d in list(self.crypto_ids.items())[:len(self.crypto_ids)//2]]:
                    continue
            
            # Better way: group by what we find
            seen = set()
            grouped = {}
            for name, data in sorted(self.crypto_ids.items()):
                if isinstance(data, dict):
                    gecko_id = data["gecko"]
                    cc_symbol = data["cc"]
                    key = (gecko_id, cc_symbol)
                    if key not in seen:
                        seen.add(key)
                        if gecko_id not in grouped:
                            grouped[gecko_id] = []
                        grouped[gecko_id].append((name, cc_symbol))
            
            # Format output
            crypto_text = ""
            for gecko_id in sorted(grouped.keys()):
                names = grouped[gecko_id]
                name_aliases = ", ".join([n[0].capitalize() for n in names])
                symbol = names[0][1]
                crypto_text += f"• **{name_aliases}** `{symbol}`\n"
            
            embed.add_field(
                name="Available Coins",
                value=crypto_text,
                inline=False
            )
            
            embed.add_field(
                name="📝 Examples",
                value="`/price bitcoin`\n`/price eth`\n`/price cardano`\n`/price doge`",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            result, error = await self.get_crypto_price(cryptocurrency)
            
            if error:
                embed = discord.Embed(
                    title="❌ Price Lookup Failed",
                    description=error,
                    color=discord.Color.red()
                )
                embed.add_field(name="🔍 Searched", value=cryptocurrency, inline=False)
                embed.add_field(
                    name="💡 Need Help?",
                    value="Type `/price list` to see all supported cryptocurrencies",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Build result embed
            crypto_name = cryptocurrency.capitalize()
            price = result["price"]
            change_24h = result["change_24h"]
            
            # Determine color based on change
            if change_24h > 0:
                color = discord.Color.green()
                change_emoji = "📈"
            elif change_24h < 0:
                color = discord.Color.red()
                change_emoji = "📉"
            else:
                color = discord.Color.greyple()
                change_emoji = "➡️"
            
            embed = discord.Embed(
                title=f"💰 {crypto_name} Price",
                description=f"**{self.format_price(price)}**",
                color=color,
                timestamp=discord.utils.utcnow()
            )
            
            # Price change
            embed.add_field(
                name=f"{change_emoji} 24h Change",
                value=f"{change_24h:+.2f}%",
                inline=True
            )
            
            # Market cap
            if result["market_cap"] > 0:
                market_cap_str = f"${result['market_cap']:,.0f}"
                if result['market_cap'] >= 1e9:
                    market_cap_str = f"${result['market_cap']/1e9:.2f}B"
                elif result['market_cap'] >= 1e6:
                    market_cap_str = f"${result['market_cap']/1e6:.2f}M"
                embed.add_field(
                    name="📊 Market Cap",
                    value=market_cap_str,
                    inline=True
                )
            
            # 24h Volume
            if result["volume_24h"] > 0:
                volume_str = f"${result['volume_24h']:,.0f}"
                if result['volume_24h'] >= 1e9:
                    volume_str = f"${result['volume_24h']/1e9:.2f}B"
                embed.add_field(
                    name="📈 24h Volume",
                    value=volume_str,
                    inline=True
                )
            
            # Data source
            source_info = result['source']
            if result['source'] == 'CoinGecko':
                source_info = "CoinGecko (Primary)"
            elif result['source'] == 'CryptoCompare':
                source_info = "CryptoCompare (Fallback)"
            
            embed.set_footer(text=f"Data from {source_info} | Last updated")
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Price command error: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CryptoPrice(bot))
