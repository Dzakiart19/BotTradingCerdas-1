#!/usr/bin/env python3
"""
XAUUSD Trading Bot - Deriv WebSocket Client
Production-ready untuk Replit/Koyeb
No API key required
"""

import asyncio
import json
import time
import websockets
from datetime import datetime

DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"
SYMBOL = "frxXAUUSD"
HEARTBEAT_INTERVAL = 20
RECONNECT_DELAY = 3


class DerivWebSocketClient:
    def __init__(self):
        self.ws = None
        self.running = True
        self.last_ping = 0
        
    async def connect(self):
        """Establish WebSocket connection"""
        try:
            print(f"🔄 Connecting to Deriv WebSocket...")
            self.ws = await asyncio.wait_for(
                websockets.connect(DERIV_WS_URL, ping_interval=None),
                timeout=10
            )
            print(f"✅ Connected to {DERIV_WS_URL}")
            return True
        except asyncio.TimeoutError:
            print("⚠️ Connection timeout")
            return False
        except Exception as e:
            print(f"⚠️ Connection error: {e}")
            return False
    
    async def subscribe_ticks(self):
        """Subscribe to XAUUSD ticks"""
        try:
            subscribe_msg = {"ticks": SYMBOL}
            await self.ws.send(json.dumps(subscribe_msg))
            print(f"📡 Subscribed to {SYMBOL}")
            return True
        except Exception as e:
            print(f"⚠️ Subscribe error: {e}")
            return False
    
    async def send_heartbeat(self):
        """Send ping to keep connection alive"""
        while self.running and self.ws:
            try:
                current_time = time.time()
                if current_time - self.last_ping >= HEARTBEAT_INTERVAL:
                    ping_msg = {"ping": 1}
                    await self.ws.send(json.dumps(ping_msg))
                    self.last_ping = current_time
                await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️ Heartbeat error: {e}")
                break
    
    async def handle_ticks(self):
        """Receive and print tick data"""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    
                    if "tick" in data:
                        tick = data["tick"]
                        epoch = tick.get("epoch", int(time.time()))
                        bid = tick.get("bid", 0)
                        ask = tick.get("ask", 0)
                        quote = tick.get("quote", 0)
                        
                        timestamp = datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")
                        print(f"[{epoch}] {timestamp} | bid={bid:.2f}, ask={ask:.2f}, quote={quote:.2f}")
                    
                    elif "pong" in data:
                        pass
                    
                    elif "error" in data:
                        error = data["error"]
                        print(f"❌ API Error: {error.get('message', 'Unknown error')}")
                    
                    elif "msg_type" in data:
                        if data["msg_type"] != "tick" and data["msg_type"] != "ping":
                            print(f"ℹ️  Message: {data.get('msg_type')}")
                
                except json.JSONDecodeError:
                    print(f"⚠️ Invalid JSON: {message}")
                except Exception as e:
                    print(f"⚠️ Parse error: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            print("⚠️ Connection closed by server")
        except Exception as e:
            print(f"⚠️ Receive error: {e}")
    
    async def run(self):
        """Main loop with auto-reconnect"""
        while self.running:
            try:
                connected = await self.connect()
                
                if not connected:
                    print(f"⏳ Reconnecting in {RECONNECT_DELAY} seconds...")
                    await asyncio.sleep(RECONNECT_DELAY)
                    continue
                
                subscribed = await self.subscribe_ticks()
                
                if not subscribed:
                    print(f"⏳ Reconnecting in {RECONNECT_DELAY} seconds...")
                    await asyncio.sleep(RECONNECT_DELAY)
                    continue
                
                heartbeat_task = asyncio.create_task(self.send_heartbeat())
                
                await self.handle_ticks()
                
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                
                if self.ws:
                    await self.ws.close()
                
                print(f"⚠️ Disconnected, reconnecting in {RECONNECT_DELAY} seconds...")
                await asyncio.sleep(RECONNECT_DELAY)
            
            except KeyboardInterrupt:
                print("\n🛑 Shutting down...")
                self.running = False
                break
            except Exception as e:
                print(f"⚠️ Unexpected error: {e}")
                print(f"⏳ Reconnecting in {RECONNECT_DELAY} seconds...")
                await asyncio.sleep(RECONNECT_DELAY)
        
        if self.ws:
            await self.ws.close()
        
        print("👋 WebSocket client stopped")
    
    def stop(self):
        """Stop the client"""
        self.running = False


async def main():
    """Entry point"""
    print("=" * 70)
    print("🚀 XAUUSD Trading Bot - Deriv WebSocket Client")
    print("=" * 70)
    print(f"WebSocket: {DERIV_WS_URL}")
    print(f"Symbol: {SYMBOL}")
    print(f"Heartbeat: {HEARTBEAT_INTERVAL}s")
    print("=" * 70)
    print()
    
    client = DerivWebSocketClient()
    
    try:
        await client.run()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        client.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
