import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import os
from datetime import datetime
import logging
import yfinance as yf

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
        
        # Indonesian stocks (IDX) - using Yahoo Finance format with .JK suffix
        self.indonesian_stocks = {
            "bbri": "BBRI.JK",
            "bbca": "BBCA.JK",
            "asii": "ASII.JK",
            "tlkm": "TLKM.JK",
            "bmri": "BMRI.JK",
            "bnga": "BNGA.JK",
            "unvr": "UNVR.JK",
            "adro": "ADRO.JK",
            "intp": "INTP.JK",
            "jsmr": "JSMR.JK",
        }
        
        # Popular US stocks
        self.us_stocks = {
            "aapl": "AAPL",
            "googl": "GOOGL",
            "msft": "MSFT",
            "amzn": "AMZN",
            "meta": "META",
            "nvda": "NVDA",
            "tsla": "TSLA",
            "amg": "AMG",
        }
    
    def fetch_stock(self, symbol: str) -> dict:
        """Fetch stock price from Yahoo Finance using yfinance (supports US & IDX stocks)"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get current price - try different fields for compatibility
            price = info.get('currentPrice') or info.get('regularMarketPrice', None)
            
            if price is None or price == 0:
                return {"success": False, "error": "Unable to fetch stock price"}
            
            # Get latest historical data for OHLC
            hist = ticker.history(period='5d')
            
            if hist.empty:
                return {"success": False, "error": "No historical data available"}
            
            latest = hist.iloc[-1]
            previous = hist.iloc[-2] if len(hist) > 1 else None
            
            # Calculate change
            open_price = float(latest.get('Open', 0))
            close_price = float(latest.get('Close', price))
            high_price = float(latest.get('High', price))
            low_price = float(latest.get('Low', price))
            prev_close = float(previous.get('Close', open_price)) if previous is not None else open_price
            
            change = close_price - prev_close
            change_percent = (change / prev_close * 100) if prev_close > 0 else 0
            
            return {
                "success": True,
                "price": float(price),
                "change": change,
                "change_percent": change_percent,
                "high": high_price,
                "low": low_price,
                "open": open_price,
                "previous_close": prev_close,
                "source": "Yahoo Finance"
            }
        except Exception as e:
            logger.error(f"yfinance error: {e}")
            return {"success": False, "error": str(e)}
    
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
    
    def detect_asset_type(self, search_term: str) -> tuple:
        """Detect if search term is crypto or stock, return (type, symbol)"""
        search_lower = search_term.lower()
        
        # Check if it's a crypto
        if search_lower in self.crypto_ids:
            crypto_data = self.crypto_ids[search_lower]
            return "crypto", search_lower
        
        # Check if it's an Indonesian stock
        if search_lower in self.indonesian_stocks:
            return "stock", self.indonesian_stocks[search_lower]
        
        # Check if it's a US stock
        if search_lower in self.us_stocks:
            return "stock", self.us_stocks[search_lower]
        
        # If matches pattern like "BBRI.IDX" or "AAPL"
        if "." in search_term:
            return "stock", search_term.upper()
        
        # Default: try as stock with uppercase
        return "stock", search_term.upper()
    
    def format_price(self, price: float) -> str:
        """Format price with proper notation"""
        if price >= 1000:
            return f"${price:,.2f}"
        elif price >= 1:
            return f"${price:.2f}"
        else:
            return f"${price:.8f}"
    
    @app_commands.command(name="price", description="Get cryptocurrency or stock price")
    @app_commands.describe(asset="Crypto (bitcoin, ETH) or Stock (BBRI, AAPL)")
    async def price_command(self, interaction: discord.Interaction, asset: str):
        """Get current price for cryptocurrency or stock with multi-source fallback"""
        
        # Check if user wants to see supported assets
        if asset.lower() in ["list", "support", "supported", "help"]:
            embed = discord.Embed(
                title="💰 Supported Assets - Price Tracker",
                description="Get live prices for crypto, US stocks, and Indonesian IDX stocks",
                color=discord.Color.gold()
            )
            
            # Cryptocurrencies list
            crypto_list = ""
            seen = set()
            for name, data in sorted(self.crypto_ids.items()):
                if isinstance(data, dict):
                    gecko_id = data["gecko"]
                    key = gecko_id
                    if key not in seen:
                        seen.add(key)
                        crypto_list += f"• {name.upper()}"
                        if len(crypto_list.split("\n")) >= 6:
                            break
                        crypto_list += "\n"
            
            embed.add_field(
                name="🪙 Cryptocurrencies (15+ supported)",
                value=crypto_list + "\n• ... and more",
                inline=False
            )
            
            # Indonesian stocks
            indo_stocks = ""
            for i, (name, symbol) in enumerate(list(self.indonesian_stocks.items())):
                indo_stocks += f"• {name.upper()} ({symbol})"
                if i < len(self.indonesian_stocks) - 1:
                    indo_stocks += "\n"
            
            embed.add_field(
                name="🇮🇩 Indonesian Stocks (IDX)",
                value=indo_stocks,
                inline=False
            )
            
            # US stocks
            us_stocks = ""
            for name, symbol in list(self.us_stocks.items()):
                us_stocks += f"• {name.upper()} ({symbol})\n"
            us_stocks = us_stocks.strip()
            
            embed.add_field(
                name="🇺🇸 US Stocks",
                value=us_stocks,
                inline=False
            )
            
            # Example outputs
            embed.add_field(
                name="📝 Example Commands",
                value="`/price bitcoin` → Crypto with 24h change & market cap\n`/price bbri` → IDX stock with OHLC data\n`/price aapl` → US stock with OHLC data",
                inline=False
            )
            
            embed.set_footer(text="All prices are live • Supports 33+ assets • Free tier")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Detect asset type
            asset_type, symbol = self.detect_asset_type(asset)
            
            if asset_type == "crypto":
                result, error = await self.get_crypto_price(symbol)
                
                if error:
                    embed = discord.Embed(
                        title="❌ Crypto Lookup Failed",
                        description=error,
                        color=discord.Color.red()
                    )
                    embed.add_field(name="🔍 Searched", value=asset, inline=False)
                    embed.add_field(
                        name="💡 Need Help?",
                        value="Type `/price list` to see all supported assets",
                        inline=False
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                # Format crypto output
                crypto_name = asset.capitalize()
                price = result["price"]
                change_24h = result["change_24h"]
                
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
                
                embed.add_field(
                    name=f"{change_emoji} 24h Change",
                    value=f"{change_24h:+.2f}%",
                    inline=True
                )
                
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
                
                if result["volume_24h"] > 0:
                    volume_str = f"${result['volume_24h']:,.0f}"
                    if result['volume_24h'] >= 1e9:
                        volume_str = f"${result['volume_24h']/1e9:.2f}B"
                    embed.add_field(
                        name="📈 24h Volume",
                        value=volume_str,
                        inline=True
                    )
                
                source_info = result['source']
                if result['source'] == 'CoinGecko':
                    source_info = "CoinGecko (Primary)"
                elif result['source'] == 'CryptoCompare':
                    source_info = "CryptoCompare (Fallback)"
                
                embed.set_footer(text=f"Data from {source_info}")
            
            elif asset_type == "stock":
                result = self.fetch_stock(symbol)
                
                if not result["success"]:
                    embed = discord.Embed(
                        title="❌ Stock Lookup Failed",
                        description=result.get("error", "Unable to fetch stock data"),
                        color=discord.Color.red()
                    )
                    embed.add_field(name="📊 Symbol", value=symbol, inline=False)
                    embed.add_field(
                        name="💡 Need Help?",
                        value="Type `/price list` to see all supported stocks",
                        inline=False
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                # Format stock output
                price = result["price"]
                change = result["change"]
                change_percent = result["change_percent"]
                
                if change_percent > 0:
                    color = discord.Color.green()
                    change_emoji = "📈"
                elif change_percent < 0:
                    color = discord.Color.red()
                    change_emoji = "📉"
                else:
                    color = discord.Color.greyple()
                    change_emoji = "➡️"
                
                embed = discord.Embed(
                    title=f"📊 {symbol} Price",
                    description=f"**${price:,.2f}**",
                    color=color,
                    timestamp=discord.utils.utcnow()
                )
                
                embed.add_field(
                    name=f"{change_emoji} Change",
                    value=f"{change:+.2f} ({change_percent:+.2f}%)",
                    inline=True
                )
                
                embed.add_field(
                    name="📈 Open",
                    value=f"${result['open']:,.2f}",
                    inline=True
                )
                
                embed.add_field(
                    name="🔝 High",
                    value=f"${result['high']:,.2f}",
                    inline=True
                )
                
                embed.add_field(
                    name="🔻 Low",
                    value=f"${result['low']:,.2f}",
                    inline=True
                )
                
                embed.add_field(
                    name="⏹️ Prev Close",
                    value=f"${result['previous_close']:,.2f}",
                    inline=True
                )
                
                embed.set_footer(text=f"Data from {result['source']}")
            
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
