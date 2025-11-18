import asyncio
import signal
import sys
import os
from aiohttp import web
from typing import Optional

from config import Config
from bot.logger import setup_logger
from bot.database import DatabaseManager
from bot.market_data import MarketDataClient
from bot.strategy import TradingStrategy
from bot.risk_manager import RiskManager
from bot.position_tracker import PositionTracker
from bot.chart_generator import ChartGenerator
from bot.telegram_bot import TradingBot
from bot.alert_system import AlertSystem
from bot.error_handler import ErrorHandler
from bot.user_manager import UserManager
from bot.task_scheduler import TaskScheduler, setup_default_tasks

logger = setup_logger('Main')

class TradingBotOrchestrator:
    def __init__(self):
        self.config = Config()
        self.running = False
        self.health_server = None
        
        logger.info("Initializing Trading Bot components...")
        
        self.db_manager = DatabaseManager(self.config.DATABASE_PATH)
        logger.info("Database initialized")
        
        self.error_handler = ErrorHandler(self.config)
        logger.info("Error handler initialized")
        
        self.user_manager = UserManager(self.config)
        logger.info("User manager initialized")
        
        self.market_data = MarketDataClient(self.config)
        logger.info("Market data client initialized")
        
        self.strategy = TradingStrategy(self.config)
        logger.info("Trading strategy initialized")
        
        self.risk_manager = RiskManager(self.config, self.db_manager)
        logger.info("Risk manager initialized")
        
        self.chart_generator = ChartGenerator(self.config)
        logger.info("Chart generator initialized")
        
        self.alert_system = AlertSystem(self.config, self.db_manager)
        logger.info("Alert system initialized")
        
        self.position_tracker = PositionTracker(
            self.config, 
            self.db_manager, 
            self.risk_manager,
            self.alert_system,
            self.user_manager,
            self.chart_generator,
            self.market_data
        )
        logger.info("Position tracker initialized")
        
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
        logger.info("Telegram bot initialized")
        
        self.task_scheduler = TaskScheduler(self.config)
        logger.info("Task scheduler initialized")
        
        logger.info("All components initialized successfully")
        
    async def start_health_server(self):
        try:
            async def health_check(request):
                market_status = self.market_data.get_status()
                
                health_status = {
                    'status': 'healthy' if self.running else 'stopped',
                    'market_data': market_status,
                    'telegram_bot': 'running' if self.telegram_bot.app else 'stopped',
                    'scheduler': 'running' if self.task_scheduler.running else 'stopped'
                }
                
                return web.json_response(health_status)
            
            app = web.Application()
            app.router.add_get('/health', health_check)
            
            runner = web.AppRunner(app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', self.config.HEALTH_CHECK_PORT)
            await site.start()
            
            self.health_server = runner
            logger.info(f"Health check server started on port {self.config.HEALTH_CHECK_PORT}")
            
        except Exception as e:
            logger.error(f"Failed to start health server: {e}")
    
    async def setup_scheduled_tasks(self):
        bot_components = {
            'chart_generator': self.chart_generator,
            'alert_system': self.alert_system,
            'db_manager': self.db_manager,
            'market_data': self.market_data
        }
        
        setup_default_tasks(self.task_scheduler, bot_components)
        logger.info("Scheduled tasks configured")
    
    async def start(self):
        logger.info("=" * 60)
        logger.info("XAUUSD TRADING BOT STARTING")
        logger.info("=" * 60)
        logger.info(f"Mode: {'DRY RUN (Simulation)' if self.config.DRY_RUN else 'LIVE'}")
        logger.info(f"Telegram Bot Token: {'Configured' if self.config.TELEGRAM_BOT_TOKEN else 'NOT CONFIGURED'}")
        logger.info(f"Authorized Users: {len(self.config.AUTHORIZED_USER_IDS)}")
        logger.info("=" * 60)
        
        if not self.config.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not configured! Bot cannot start.")
            logger.error("Please set TELEGRAM_BOT_TOKEN environment variable.")
            return
        
        self.running = True
        
        try:
            logger.info("Starting health check server...")
            await self.start_health_server()
            
            logger.info("Connecting to market data feed...")
            market_task = asyncio.create_task(self.market_data.connect_websocket())
            
            logger.info("Waiting for initial market data...")
            for i in range(30):
                await asyncio.sleep(1)
                if self.market_data.is_connected():
                    logger.info("Market data connection established")
                    break
                if i % 5 == 0:
                    logger.info(f"Still waiting for market data... ({i}s)")
            
            if not self.market_data.is_connected():
                logger.warning("Market data not connected yet, but continuing startup...")
            
            logger.info("Setting up scheduled tasks...")
            await self.setup_scheduled_tasks()
            
            logger.info("Starting task scheduler...")
            await self.task_scheduler.start()
            
            logger.info("Starting position tracker...")
            position_task = asyncio.create_task(
                self.position_tracker.monitor_positions(self.market_data)
            )
            
            logger.info("Initializing Telegram bot...")
            bot_initialized = await self.telegram_bot.initialize()
            
            if not bot_initialized:
                logger.error("Failed to initialize Telegram bot!")
                return
            
            if self.telegram_bot.app and self.config.AUTHORIZED_USER_IDS:
                self.alert_system.set_telegram_app(
                    self.telegram_bot.app,
                    self.config.AUTHORIZED_USER_IDS
                )
                self.alert_system.telegram_app = self.telegram_bot.app
                self.position_tracker.telegram_app = self.telegram_bot.app
                logger.info("Telegram app set for alert system and position tracker")
            
            logger.info("Starting Telegram bot polling...")
            bot_task = asyncio.create_task(self.telegram_bot.run())
            
            logger.info("Waiting for candles to build (minimal 30 candles)...")
            for i in range(60):
                await asyncio.sleep(1)
                df_check = await self.market_data.get_historical_data('M1', 100)
                if df_check is not None and len(df_check) >= 30:
                    logger.info(f"✅ Got {len(df_check)} candles, ready for trading!")
                    break
                if i % 10 == 0:
                    logger.info(f"Building candles... {i}s elapsed")
            
            if self.config.AUTHORIZED_USER_IDS:
                startup_msg = (
                    "🤖 *Bot Started Successfully*\n\n"
                    f"Mode: {'DRY RUN' if self.config.DRY_RUN else 'LIVE'}\n"
                    f"Market: {'Connected' if self.market_data.is_connected() else 'Connecting...'}\n"
                    f"Status: Auto-monitoring AKTIF ✅\n\n"
                    "Bot akan otomatis mendeteksi sinyal trading.\n"
                    "Gunakan /help untuk list command"
                )
                
                for user_id in self.config.AUTHORIZED_USER_IDS:
                    try:
                        await self.telegram_bot.app.bot.send_message(
                            chat_id=user_id,
                            text=startup_msg,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Failed to send startup message to user {user_id}: {e}")
                
                logger.info("Auto-starting monitoring for authorized users...")
                await self.telegram_bot.auto_start_monitoring(self.config.AUTHORIZED_USER_IDS)
            
            logger.info("=" * 60)
            logger.info("BOT IS NOW RUNNING")
            logger.info("=" * 60)
            logger.info("Press Ctrl+C to stop")
            
            await asyncio.gather(market_task, bot_task, position_task, return_exceptions=True)
            
        except asyncio.CancelledError:
            logger.info("Bot tasks cancelled")
        except Exception as e:
            logger.error(f"Error during bot operation: {e}")
            if self.error_handler:
                self.error_handler.log_exception(e, "main_loop")
            if self.alert_system:
                await self.alert_system.send_system_error(f"Bot crashed: {str(e)}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        if not self.running:
            return
        
        logger.info("=" * 60)
        logger.info("SHUTTING DOWN BOT...")
        logger.info("=" * 60)
        
        self.running = False
        
        try:
            if self.telegram_bot and self.telegram_bot.app and self.config.AUTHORIZED_USER_IDS:
                shutdown_msg = "🛑 *Bot Shutting Down*\n\nBot is being stopped."
                
                for user_id in self.config.AUTHORIZED_USER_IDS:
                    try:
                        await self.telegram_bot.app.bot.send_message(
                            chat_id=user_id,
                            text=shutdown_msg,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Failed to send shutdown message: {e}")
            
            logger.info("Stopping position tracker...")
            if self.position_tracker:
                self.position_tracker.stop_monitoring()
            
            logger.info("Stopping task scheduler...")
            if self.task_scheduler:
                await self.task_scheduler.stop()
            
            logger.info("Stopping market data connection...")
            if self.market_data:
                self.market_data.disconnect()
            
            logger.info("Stopping Telegram bot...")
            if self.telegram_bot and self.telegram_bot.app:
                await self.telegram_bot.app.stop()
                await self.telegram_bot.app.shutdown()
            
            logger.info("Closing database connections...")
            if self.db_manager:
                self.db_manager.close()
            
            logger.info("Stopping health server...")
            if self.health_server:
                await self.health_server.cleanup()
            
            logger.info("=" * 60)
            logger.info("BOT SHUTDOWN COMPLETE")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

async def main():
    orchestrator = TradingBotOrchestrator()
    
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        asyncio.create_task(orchestrator.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
    finally:
        await orchestrator.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
