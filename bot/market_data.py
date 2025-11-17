import asyncio
import websockets
import json
from datetime import datetime, timedelta
from collections import deque
import pandas as pd
import random
from typing import Optional, Dict, List
from bot.logger import setup_logger

logger = setup_logger('MarketData')

class OHLCBuilder:
    def __init__(self, timeframe_minutes: int = 1):
        self.timeframe_minutes = timeframe_minutes
        self.timeframe_seconds = timeframe_minutes * 60
        self.current_candle = None
        self.candles = deque(maxlen=500)
        self.tick_count = 0
        
    def add_tick(self, bid: float, ask: float, timestamp: datetime):
        mid_price = (bid + ask) / 2.0
        
        candle_start = timestamp.replace(
            second=0, 
            microsecond=0,
            minute=(timestamp.minute // self.timeframe_minutes) * self.timeframe_minutes
        )
        
        if self.current_candle is None or self.current_candle['timestamp'] != candle_start:
            if self.current_candle is not None:
                self.candles.append(self.current_candle.copy())
                logger.debug(f"M{self.timeframe_minutes} candle completed: O={self.current_candle['open']:.2f} H={self.current_candle['high']:.2f} L={self.current_candle['low']:.2f} C={self.current_candle['close']:.2f} V={self.current_candle['volume']}")
            
            self.current_candle = {
                'timestamp': candle_start,
                'open': mid_price,
                'high': mid_price,
                'low': mid_price,
                'close': mid_price,
                'volume': 0
            }
            self.tick_count = 0
        
        self.current_candle['high'] = max(self.current_candle['high'], mid_price)
        self.current_candle['low'] = min(self.current_candle['low'], mid_price)
        self.current_candle['close'] = mid_price
        self.tick_count += 1
        self.current_candle['volume'] = self.tick_count
        
    def get_dataframe(self, limit: int = 100) -> Optional[pd.DataFrame]:
        all_candles = list(self.candles)
        if self.current_candle:
            all_candles.append(self.current_candle)
        
        if len(all_candles) == 0:
            return None
        
        df = pd.DataFrame(all_candles)
        df.set_index('timestamp', inplace=True)
        
        if len(df) > limit:
            df = df.tail(limit)
        
        return df

class MarketDataClient:
    def __init__(self, config):
        self.config = config
        self.ws_url = "wss://ws-json.exness.com/realtime"
        self.current_bid = None
        self.current_ask = None
        self.current_timestamp = None
        self.ws = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.running = False
        self.use_simulator = False
        self.simulator_task = None
        
        self.m1_builder = OHLCBuilder(timeframe_minutes=1)
        self.m5_builder = OHLCBuilder(timeframe_minutes=5)
        
        self.reconnect_delay = 5
        self.base_price = 2650.0
        self.price_volatility = 2.0
        
    async def connect_websocket(self):
        self.running = True
        
        while self.running:
            try:
                logger.info(f"Connecting to Exness WebSocket: {self.ws_url}")
                
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10
                ) as websocket:
                    self.ws = websocket
                    self.connected = True
                    self.reconnect_attempts = 0
                    
                    logger.info("WebSocket connected to Exness")
                    
                    subscribe_msg = {"type": "subscribe", "pairs": ["XAUUSD"]}
                    await websocket.send(json.dumps(subscribe_msg))
                    logger.info("Subscribed to XAUUSD")
                    
                    async for message in websocket:
                        await self._on_message(message)
                        
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                self.connected = False
                await self._handle_reconnect()
                
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.connected = False
                await self._handle_reconnect()
    
    async def _handle_reconnect(self):
        if not self.running:
            return
            
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts <= self.max_reconnect_attempts:
            logger.warning(f"WebSocket connection failed. Will retry in {self.reconnect_delay}s (Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            logger.warning(f"Note: URL {self.ws_url} may not be publicly accessible")
            await asyncio.sleep(self.reconnect_delay)
        else:
            logger.error(f"Max reconnect attempts ({self.max_reconnect_attempts}) reached")
            logger.warning("Switching to SIMULATOR MODE for testing purposes")
            self.use_simulator = True
            
            self._seed_initial_tick()
            
            await self._run_simulator()
    
    def _seed_initial_tick(self):
        spread = 0.40
        self.current_bid = self.base_price - (spread / 2)
        self.current_ask = self.base_price + (spread / 2)
        self.current_timestamp = datetime.utcnow()
        
        self.m1_builder.add_tick(self.current_bid, self.current_ask, self.current_timestamp)
        self.m5_builder.add_tick(self.current_bid, self.current_ask, self.current_timestamp)
        
        logger.info(f"Initial tick seeded: Bid=${self.current_bid:.2f}, Ask=${self.current_ask:.2f}")
    
    async def _run_simulator(self):
        logger.info("Starting price simulator (fallback mode)")
        logger.info(f"Base price: ${self.base_price}, Volatility: ±${self.price_volatility}")
        
        while self.use_simulator:
            try:
                spread = 0.30 + random.uniform(0, 0.20)
                
                price_change = random.uniform(-self.price_volatility, self.price_volatility)
                mid_price = self.base_price + price_change
                
                self.current_bid = mid_price - (spread / 2)
                self.current_ask = mid_price + (spread / 2)
                self.current_timestamp = datetime.utcnow()
                
                self.m1_builder.add_tick(self.current_bid, self.current_ask, self.current_timestamp)
                self.m5_builder.add_tick(self.current_bid, self.current_ask, self.current_timestamp)
                
                if random.randint(1, 100) == 1:
                    logger.debug(f"Simulator: Bid=${self.current_bid:.2f}, Ask=${self.current_ask:.2f}, Spread=${spread:.2f}")
                
                self.base_price = mid_price
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Simulator error: {e}")
                await asyncio.sleep(5)
        
        logger.info("Price simulator stopped")
    
    async def _on_message(self, message: str):
        try:
            data = json.loads(message)
            
            if isinstance(data, dict):
                bid = None
                ask = None
                timestamp_ms = None
                
                if 'bid' in data and 'ask' in data:
                    bid = data['bid']
                    ask = data['ask']
                    timestamp_ms = data.get('timestamp') or data.get('t')
                elif 'price' in data:
                    price = data['price']
                    spread = data.get('spread', 0.5)
                    bid = price - (spread / 2)
                    ask = price + (spread / 2)
                    timestamp_ms = data.get('timestamp') or data.get('t')
                
                if bid is not None and ask is not None:
                    self.current_bid = float(bid)
                    self.current_ask = float(ask)
                    
                    if timestamp_ms:
                        if timestamp_ms > 10000000000:
                            self.current_timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0)
                        else:
                            self.current_timestamp = datetime.fromtimestamp(timestamp_ms)
                    else:
                        self.current_timestamp = datetime.utcnow()
                    
                    self.m1_builder.add_tick(self.current_bid, self.current_ask, self.current_timestamp)
                    self.m5_builder.add_tick(self.current_bid, self.current_ask, self.current_timestamp)
                    
                    logger.info(f"WebSocket tick: Bid={self.current_bid:.2f}, Ask={self.current_ask:.2f}")
                else:
                    logger.debug(f"Unknown message format: {data}")
                        
        except Exception as e:
            logger.error(f"Error processing message: {e}, Raw: {message[:200]}")
    
    async def get_current_price(self) -> Optional[float]:
        if self.current_bid and self.current_ask:
            mid_price = (self.current_bid + self.current_ask) / 2.0
            return mid_price
        
        logger.warning("No current price available from WebSocket")
        return None
    
    async def get_bid_ask(self) -> Optional[tuple]:
        if self.current_bid and self.current_ask:
            return (self.current_bid, self.current_ask)
        return None
    
    async def get_spread(self) -> Optional[float]:
        if self.current_bid and self.current_ask:
            return self.current_ask - self.current_bid
        return None
    
    async def get_historical_data(self, timeframe: str = 'M1', limit: int = 100) -> Optional[pd.DataFrame]:
        try:
            if timeframe == 'M1':
                df = self.m1_builder.get_dataframe(limit)
                if df is not None:
                    logger.info(f"Generated {len(df)} M1 candles from tick feed")
                    return df
                    
            elif timeframe == 'M5':
                df = self.m5_builder.get_dataframe(limit)
                if df is not None:
                    logger.info(f"Generated {len(df)} M5 candles from tick feed")
                    return df
            
            logger.warning(f"No historical data available for {timeframe}")
            return None
                        
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None
    
    def disconnect(self):
        self.running = False
        self.use_simulator = False
        self.connected = False
        if self.ws:
            asyncio.create_task(self.ws.close())
        logger.info("MarketData client disconnected")
    
    def is_connected(self) -> bool:
        return self.connected or self.use_simulator
    
    def get_status(self) -> Dict:
        return {
            'connected': self.connected,
            'simulator_mode': self.use_simulator,
            'reconnect_attempts': self.reconnect_attempts,
            'has_data': self.current_bid is not None and self.current_ask is not None,
            'websocket_url': self.ws_url
        }
