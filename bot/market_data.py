import asyncio
import aiohttp
import websocket
import json
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional, Dict
from bot.logger import setup_logger

logger = setup_logger('MarketData')

class MarketDataClient:
    def __init__(self, config):
        self.config = config
        self.polygon_key = config.POLYGON_API_KEY
        self.finnhub_key = config.FINNHUB_API_KEY
        self.current_price = None
        self.ws = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.loop = None
        
    async def connect_websocket(self):
        if not self.polygon_key:
            logger.warning("Polygon API key not found, using REST fallback only")
            return False
        
        try:
            self.loop = asyncio.get_event_loop()
            
            ws_url = f"wss://socket.polygon.io/forex"
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            logger.info("Attempting WebSocket connection to Polygon.io...")
            await self.loop.run_in_executor(None, self.ws.run_forever)
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
    
    def _on_open(self, ws):
        logger.info("WebSocket connected")
        auth_msg = {"action": "auth", "params": self.polygon_key}
        ws.send(json.dumps(auth_msg))
        
        subscribe_msg = {"action": "subscribe", "params": "C.C:XAUUSD"}
        ws.send(json.dumps(subscribe_msg))
        
        self.connected = True
        self.reconnect_attempts = 0
    
    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            
            if isinstance(data, list):
                for item in data:
                    if item.get('ev') == 'C' and 'p' in item:
                        self.current_price = item['p']
                        logger.debug(f"Price update: {self.current_price}")
                        
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.connected = False
        
        if self.reconnect_attempts < self.max_reconnect_attempts and self.loop:
            self.reconnect_attempts += 1
            logger.info(f"Reconnecting... Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            self.loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self.connect_websocket())
            )
    
    async def get_current_price(self) -> Optional[float]:
        if self.connected and self.current_price:
            return self.current_price
        
        return await self.get_price_rest()
    
    async def get_price_rest(self) -> Optional[float]:
        try:
            if self.polygon_key:
                url = f"https://api.polygon.io/v2/last/trade/C:XAUUSD?apiKey={self.polygon_key}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'results' in data and 'p' in data['results']:
                                price = data['results']['p']
                                self.current_price = price
                                logger.debug(f"REST price: {price}")
                                return price
            
            if self.finnhub_key:
                url = f"https://finnhub.io/api/v1/forex/rates?base=XAU&token={self.finnhub_key}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'quote' in data and 'USD' in data['quote']:
                                price = data['quote']['USD']
                                self.current_price = price
                                logger.debug(f"Finnhub price: {price}")
                                return price
            
            logger.warning("No API keys available for price fetch")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching price via REST: {e}")
            return None
    
    async def get_historical_data(self, timeframe: str = 'M1', limit: int = 100) -> Optional[pd.DataFrame]:
        try:
            if self.polygon_key:
                df = await self._get_polygon_historical(timeframe, limit)
                if df is not None:
                    return df
                logger.warning("Polygon historical data failed, trying Finnhub...")
            
            if self.finnhub_key:
                df = await self._get_finnhub_historical(timeframe, limit)
                if df is not None:
                    return df
            
            logger.error("No API keys available or all sources failed for historical data")
            return None
                        
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None
    
    async def _get_polygon_historical(self, timeframe: str = 'M1', limit: int = 100) -> Optional[pd.DataFrame]:
        try:
            multiplier = 1
            timespan = 'minute'
            
            if timeframe == 'M5':
                multiplier = 5
            elif timeframe == 'M15':
                multiplier = 15
            elif timeframe == 'H1':
                multiplier = 1
                timespan = 'hour'
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            url = (f"https://api.polygon.io/v2/aggs/ticker/C:XAUUSD/range/"
                  f"{multiplier}/{timespan}/"
                  f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
                  f"?apiKey={self.polygon_key}&limit={limit}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'results' in data and data['results']:
                            df = pd.DataFrame(data['results'])
                            df.rename(columns={
                                'o': 'open',
                                'h': 'high',
                                'l': 'low',
                                'c': 'close',
                                'v': 'volume',
                                't': 'timestamp'
                            }, inplace=True)
                            
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                            df.set_index('timestamp', inplace=True)
                            
                            logger.info(f"Fetched {len(df)} candles from Polygon for {timeframe}")
                            return df
                        
            return None
                        
        except Exception as e:
            logger.error(f"Polygon historical data error: {e}")
            return None
    
    async def _get_finnhub_historical(self, timeframe: str = 'M1', limit: int = 100) -> Optional[pd.DataFrame]:
        try:
            resolution_map = {
                'M1': '1',
                'M5': '5',
                'M15': '15',
                'H1': '60'
            }
            
            resolution = resolution_map.get(timeframe, '1')
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            from_ts = int(start_date.timestamp())
            to_ts = int(end_date.timestamp())
            
            url = (f"https://finnhub.io/api/v1/forex/candles"
                  f"?symbol=OANDA:XAU_USD&resolution={resolution}"
                  f"&from={from_ts}&to={to_ts}&token={self.finnhub_key}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('s') == 'ok' and 'c' in data and len(data['c']) > 0:
                            df = pd.DataFrame({
                                'open': data['o'],
                                'high': data['h'],
                                'low': data['l'],
                                'close': data['c'],
                                'volume': data.get('v', [0] * len(data['c'])),
                                'timestamp': data['t']
                            })
                            
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                            df.set_index('timestamp', inplace=True)
                            
                            if len(df) > limit:
                                df = df.tail(limit)
                            
                            logger.info(f"Fetched {len(df)} candles from Finnhub for {timeframe}")
                            return df
            
            return None
                        
        except Exception as e:
            logger.error(f"Finnhub historical data error: {e}")
            return None
    
    def disconnect(self):
        if self.ws:
            self.ws.close()
        self.connected = False
        logger.info("MarketData client disconnected")
