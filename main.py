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
from bot.error_handler import ErrorHandler
from bot.alert_system import AlertSystem
from bot.user_manager import UserManager
from bot.task_scheduler import TaskScheduler, setup_default_tasks
from bot.pair_config import PairConfigManager
from bot.backtester import Backtester

logger = setup_logger('Main')

class TradingBotOrchestrator:
    def __init__(self):
        self.config = Config()
        self.running = False
        self.tasks = []
        
        logger.info("Initializing trading bot components...")
        
        self.error_handler = ErrorHandler(self.config)
        logger.info("Error handler initialized")
        
        self.db_manager = DatabaseManager(self.config.DATABASE_PATH)
        logger.info("Database initialized")
        
        self.pair_config = PairConfigManager(self.config)
        logger.info("Pair config initialized")
        
        self.user_manager = UserManager(self.config)
        logger.info("User manager initialized")
        
        self.alert_system = AlertSystem(self.config, self.db_manager)
        logger.info("Alert system initialized")
        
        self.indicator_engine = IndicatorEngine(self.config)
        self.market_data = MarketDataClient(self.config)
        self.strategy = TradingStrategy(self.config)
        self.risk_manager = RiskManager(self.config, self.db_manager)
        self.position_tracker = PositionTracker(
            self.config, 
            self.db_manager, 
            self.risk_manager,
            self.alert_system,
            self.user_manager
        )
        self.chart_generator = ChartGenerator(self.config)
        
        self.backtester = Backtester(self.config)
        logger.info("Backtester initialized")
        
        self.telegram_bot = TradingBot(
            self.config,
            self.db_manager,
            self.strategy,
            self.risk_manager,
            self.market_data,
            self.position_tracker,
            self.chart_generator,
            self.alert_system,
            self.error_handler,
            self.user_manager
        )
        
        self.task_scheduler = TaskScheduler(self.config)
        logger.info("Task scheduler initialized")
        
        logger.info("All components initialized successfully")
    
    async def health_check(self, request):
        return web.json_response({
            'status': 'healthy',
            'running': self.running,
            'active_positions': len(self.position_tracker.get_active_positions()),
            'scheduler_running': self.task_scheduler.running,
            'alert_system_enabled': self.alert_system.enabled,
            'enabled_pairs': len(self.pair_config.get_enabled_pairs())
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
        
        bot_components = {
            'chart_generator': self.chart_generator,
            'alert_system': self.alert_system,
            'db_manager': self.db_manager,
            'market_data': self.market_data
        }
        setup_default_tasks(self.task_scheduler, bot_components)
        
        await self.task_scheduler.start()
        logger.info("Task scheduler started")
        
        telegram_task = asyncio.create_task(self.telegram_bot.run())
        self.tasks.append(telegram_task)
        
        if self.telegram_bot.app:
            chat_ids = self.config.AUTHORIZED_USER_IDS
            self.alert_system.set_telegram_app(self.telegram_bot.app, chat_ids)
            logger.info("Alert system connected to Telegram")
        
        position_monitor_task = asyncio.create_task(
            self.position_tracker.monitor_positions(self.position_price_feed)
        )
        self.tasks.append(position_monitor_task)
        
        logger.info("🚀 Trading bot started successfully!")
        logger.info(f"Mode: {'DRY RUN (Simulation)' if self.config.DRY_RUN else 'LIVE'}")
        logger.info(f"Trading Pairs: {', '.join([p.symbol for p in self.pair_config.get_enabled_pairs()])}")
        logger.info(f"Max Trades/Day: Unlimited (24/7)")
        logger.info(f"Chart Auto-Delete: {'Enabled' if self.config.CHART_AUTO_DELETE else 'Disabled'}")
        logger.info("Waiting for Telegram commands...")
        
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled, shutting down...")
    
    async def stop(self):
        logger.info("Stopping trading bot...")
        self.running = False
        
        await self.task_scheduler.stop()
        logger.info("Task scheduler stopped")
        
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
