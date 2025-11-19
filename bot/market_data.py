import asyncio
import websockets
import json
from datetime import datetime, timedelta
from collections import deque
import pandas as pd
import pytz
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
        
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=pytz.UTC)
        
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
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.index = pd.DatetimeIndex(df.index)
        
        if len(df) > limit:
            df = df.tail(limit)
        
        return df

class MarketDataClient:
    def __init__(self, config):
        self.config = config
        self.ws_url = "wss://ws.derivws.com/websockets/v3?app_id=1089"
        self.symbol = "frxXAUUSD"
        self.current_bid = None
        self.current_ask = None
        self.current_quote = None
        self.current_timestamp = None
        self.ws = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.running = False
        self.use_simulator = False
        self.simulator_task = None
        self.last_ping = 0
        
        self.m1_builder = OHLCBuilder(timeframe_minutes=1)
        self.m5_builder = OHLCBuilder(timeframe_minutes=5)
        
        self.reconnect_delay = 3
        self.base_price = 2650.0
        self.price_volatility = 2.0
        
        self.subscribers = {}
        self.subscriber_failures = {}
        self.max_consecutive_failures = 5
        self.tick_log_counter = 0
        logger.info("Pub/Sub mechanism initialized")
    
    def _log_tick_sample(self, bid: float, ask: float, quote: float, spread: float = None, mode: str = ""):
        """Centralized tick logging dengan sampling - increment counter HANYA 1x per tick"""
        self.tick_log_counter += 1
        if self.tick_log_counter % self.config.TICK_LOG_SAMPLE_RATE == 0:
            if mode == "simulator":
                logger.info(f"💰 Simulator Tick Sample (setiap {self.config.TICK_LOG_SAMPLE_RATE}): Bid=${bid:.2f}, Ask=${ask:.2f}, Spread=${spread:.2f}")
            else:
                logger.info(f"💰 Tick Sample (setiap {self.config.TICK_LOG_SAMPLE_RATE}): Bid={bid:.2f}, Ask={ask:.2f}, Quote={quote:.2f}")
        else:
            if mode == "simulator":
                logger.debug(f"Simulator: Bid=${bid:.2f}, Ask=${ask:.2f}, Spread=${spread:.2f}")
            else:
                logger.debug(f"💰 Tick: Bid={bid:.2f}, Ask={ask:.2f}, Quote={quote:.2f}")
    
    async def subscribe_ticks(self, name: str) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)
        self.subscribers[name] = queue
        self.subscriber_failures[name] = 0
        logger.debug(f"Subscriber '{name}' registered untuk tick feed")
        return queue
    
    async def unsubscribe_ticks(self, name: str):
        if name in self.subscribers:
            del self.subscribers[name]
            if name in self.subscriber_failures:
                del self.subscriber_failures[name]
            logger.debug(f"Subscriber '{name}' unregistered dari tick feed")
    
    async def _broadcast_tick(self, tick_data: Dict):
        if not self.subscribers:
            return
        
        stale_subscribers = []
        
        for name, queue in list(self.subscribers.items()):
            success = False
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    queue.put_nowait(tick_data)
                    success = True
                    if name in self.subscriber_failures:
                        self.subscriber_failures[name] = 0
                    break
                    
                except asyncio.QueueFull:
                    if attempt < max_retries - 1:
                        backoff_time = 0.1 * (2 ** attempt)
                        logger.debug(f"Queue full for '{name}', retry {attempt + 1}/{max_retries} after {backoff_time}s")
                        await asyncio.sleep(backoff_time)
                    else:
                        logger.warning(f"Queue full for subscriber '{name}' after {max_retries} retries, skipping tick")
                        
                except Exception as e:
                    logger.error(f"Error broadcasting tick to '{name}': {e}")
                    break
            
            if not success:
                if name in self.subscriber_failures:
                    self.subscriber_failures[name] += 1
                else:
                    self.subscriber_failures[name] = 1
                
                if self.subscriber_failures[name] >= self.max_consecutive_failures:
                    logger.warning(f"Subscriber '{name}' failed {self.subscriber_failures[name]} times consecutively, marking for removal")
                    stale_subscribers.append(name)
        
        for name in stale_subscribers:
            if name in self.subscribers:
                del self.subscribers[name]
            if name in self.subscriber_failures:
                del self.subscriber_failures[name]
            logger.info(f"Removed stale subscriber '{name}' due to consecutive failures")
    
    async def fetch_historical_candles(self, websocket, timeframe_minutes: int = 1, count: int = 100):
        """Fetch historical candles from Deriv API to pre-populate OHLC data"""
        try:
            granularity = timeframe_minutes * 60
            
            history_request = {
                "ticks_history": self.symbol,
                "adjust_start_time": 1,
                "count": count,
                "end": "latest",
                "start": 1,
                "style": "candles",
                "granularity": granularity
            }
            
            await websocket.send(json.dumps(history_request))
            logger.debug(f"Requesting {count} historical M{timeframe_minutes} candles...")
            
            response = await websocket.recv()
            data = json.loads(response)
            
            if 'candles' in data:
                candles = data['candles']
                logger.info(f"Received {len(candles)} historical M{timeframe_minutes} candles")
                
                builder = self.m1_builder if timeframe_minutes == 1 else self.m5_builder
                
                for candle in candles:
                    timestamp = datetime.fromtimestamp(candle['epoch'], tz=pytz.UTC)
                    timestamp = timestamp.replace(second=0, microsecond=0)
                    
                    open_price = float(candle['open'])
                    high_price = float(candle['high'])
                    low_price = float(candle['low'])
                    close_price = float(candle['close'])
                    
                    candle_data = {
                        'timestamp': pd.Timestamp(timestamp),
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': 100
                    }
                    builder.candles.append(candle_data)
                
                logger.info(f"Pre-populated {len(builder.candles)} M{timeframe_minutes} candles")
                return True
            else:
                logger.warning(f"No historical candles in response: {data}")
                return False
                
        except Exception as e:
            logger.error(f"Error fetching historical candles: {e}")
            return False
        
    async def connect_websocket(self):
        self.running = True
        
        while self.running:
            try:
                logger.info(f"Connecting to Deriv WebSocket: {self.ws_url}")
                
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=None
                ) as websocket:
                    self.ws = websocket
                    self.connected = True
                    self.reconnect_attempts = 0
                    
                    logger.info(f"✅ Connected to Deriv WebSocket")
                    
                    await self.fetch_historical_candles(websocket, timeframe_minutes=1, count=100)
                    await self.fetch_historical_candles(websocket, timeframe_minutes=5, count=100)
                    
                    subscribe_msg = {"ticks": self.symbol}
                    await websocket.send(json.dumps(subscribe_msg))
                    logger.info(f"📡 Subscribed to {self.symbol}")
                    
                    heartbeat_task = asyncio.create_task(self._send_heartbeat())
                    
                    async for message in websocket:
                        await self._on_message(message)
                    
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass
                        
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                self.connected = False
                await self._handle_reconnect()
                
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.connected = False
                await self._handle_reconnect()
    
    async def _send_heartbeat(self):
        while self.running and self.ws:
            try:
                import time
                current_time = time.time()
                if current_time - self.last_ping >= 20:
                    ping_msg = {"ping": 1}
                    await self.ws.send(json.dumps(ping_msg))
                    self.last_ping = current_time
                await asyncio.sleep(1)
            except Exception as e:
                logger.debug(f"Heartbeat error: {e}")
                break
    
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
                self.current_quote = mid_price
                
                self.m1_builder.add_tick(self.current_bid, self.current_ask, self.current_timestamp)
                self.m5_builder.add_tick(self.current_bid, self.current_ask, self.current_timestamp)
                
                tick_data = {
                    'bid': self.current_bid,
                    'ask': self.current_ask,
                    'quote': self.current_quote,
                    'timestamp': self.current_timestamp
                }
                await self._broadcast_tick(tick_data)
                
                self._log_tick_sample(self.current_bid, self.current_ask, self.current_quote, spread, mode="simulator")
                
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
                if "tick" in data:
                    tick = data["tick"]
                    epoch = tick.get("epoch", int(datetime.utcnow().timestamp()))
                    bid = tick.get("bid")
                    ask = tick.get("ask")
                    quote = tick.get("quote")
                    
                    if bid and ask:
                        self.current_bid = float(bid)
                        self.current_ask = float(ask)
                        self.current_quote = float(quote) if quote else (self.current_bid + self.current_ask) / 2
                        self.current_timestamp = datetime.fromtimestamp(epoch)
                        
                        self.m1_builder.add_tick(self.current_bid, self.current_ask, self.current_timestamp)
                        self.m5_builder.add_tick(self.current_bid, self.current_ask, self.current_timestamp)
                        
                        self._log_tick_sample(self.current_bid, self.current_ask, self.current_quote, mode="websocket")
                        
                        tick_data = {
                            'bid': self.current_bid,
                            'ask': self.current_ask,
                            'quote': self.current_quote,
                            'timestamp': self.current_timestamp
                        }
                        await self._broadcast_tick(tick_data)
                    
                elif "pong" in data:
                    logger.debug("Pong received")
                
                elif "error" in data:
                    error = data["error"]
                    logger.error(f"API Error: {error.get('message', 'Unknown error')}")
                
                elif "msg_type" in data:
                    if data["msg_type"] not in ["tick", "ping", "pong"]:
                        logger.debug(f"Message: {data.get('msg_type')}")
                        
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
