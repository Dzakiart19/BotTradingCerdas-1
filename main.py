import asyncio
import signal
import sys
from aiohttp import web
from config import Config
from bot.logger import setup_logger
from bot.database import DatabaseManager
from bot.indicators import IndicatorEngine
from bot.market_data import MarketDataClient
from bot.strategy import TradingStrategy
from bot.risk_manager import RiskManager
from bot.position_tracker import PositionTracker
from bot.chart_generator import ChartGenerator
from bot.telegram_bot import TradingBot

logger = setup_logger('Main')

class TradingBotOrchestrator:
    def __init__(self):
        self.config = Config()
        self.running = False
        self.tasks = []
        
        logger.info("Initializing trading bot components...")
        
        self.db_manager = DatabaseManager(self.config.DATABASE_PATH)
        logger.info("Database initialized")
        
        self.indicator_engine = IndicatorEngine(self.config)
        self.market_data = MarketDataClient(self.config)
        self.strategy = TradingStrategy(self.config)
        self.risk_manager = RiskManager(self.config, self.db_manager)
        self.position_tracker = PositionTracker(self.config, self.db_manager, self.risk_manager)
        self.chart_generator = ChartGenerator(self.config)
        
        self.telegram_bot = TradingBot(
            self.config,
            self.db_manager,
            self.strategy,
            self.risk_manager,
            self.market_data,
            self.position_tracker,
            self.chart_generator
        )
        
        logger.info("All components initialized successfully")
    
    async def health_check(self, request):
        return web.json_response({
            'status': 'healthy',
            'running': self.running,
            'active_positions': len(self.position_tracker.get_active_positions())
        })
    
    async def start_health_check_server(self):
        app = web.Application()
        app.router.add_get('/health', self.health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.config.HEALTH_CHECK_PORT)
        await site.start()
        
        logger.info(f"Health check server running on port {self.config.HEALTH_CHECK_PORT}")
    
    async def position_price_feed(self):
        price = await self.market_data.get_current_price()
        return price if price else 0.0
    
    async def start(self):
        logger.info("Starting trading bot orchestrator...")
        self.running = True
        
        await self.start_health_check_server()
        
        telegram_task = asyncio.create_task(self.telegram_bot.run())
        self.tasks.append(telegram_task)
        
        position_monitor_task = asyncio.create_task(
            self.position_tracker.monitor_positions(self.position_price_feed)
        )
        self.tasks.append(position_monitor_task)
        
        logger.info("🚀 Trading bot started successfully!")
        logger.info(f"Mode: {'DRY RUN (Simulation)' if self.config.DRY_RUN else 'LIVE'}")
        logger.info("Waiting for Telegram commands...")
        
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled, shutting down...")
    
    async def stop(self):
        logger.info("Stopping trading bot...")
        self.running = False
        
        self.position_tracker.stop_monitoring()
        self.market_data.disconnect()
        
        for task in self.tasks:
            task.cancel()
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.db_manager.close()
        logger.info("Trading bot stopped")

async def main():
    orchestrator = TradingBotOrchestrator()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(orchestrator.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await orchestrator.stop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application crashed: {e}", exc_info=True)
        sys.exit(1)
