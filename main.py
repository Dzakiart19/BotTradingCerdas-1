import asyncio
import signal
import sys
import os
from aiohttp import web
from typing import Optional
from sqlalchemy import text

from config import Config
from bot.logger import setup_logger, mask_token, sanitize_log_message
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
        
        logger.info("Validating configuration...")
        try:
            self.config.validate()
            logger.info("Configuration validated successfully")
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
        
        self.running = False
        self.shutdown_in_progress = False
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
    
    def _auto_detect_webhook_url(self) -> Optional[str]:
        """Auto-detect webhook URL for Replit and other cloud platforms
        
        Returns:
            str: Auto-detected webhook URL or None if not detected
        """
        if self.config.WEBHOOK_URL and self.config.WEBHOOK_URL.strip():
            return None
        
        import json
        from urllib.parse import urlparse
        
        replit_domains = os.getenv('REPLIT_DOMAINS')
        replit_dev_domain = os.getenv('REPLIT_DEV_DOMAIN')
        
        domain = None
        
        if replit_domains:
            try:
                domains_list = json.loads(replit_domains)
                if isinstance(domains_list, list) and len(domains_list) > 0:
                    domain = str(domains_list[0]).strip()
                    logger.info(f"Detected Replit deployment domain from REPLIT_DOMAINS: {domain}")
                else:
                    logger.warning(f"REPLIT_DOMAINS is not a valid array: {replit_domains}")
            except json.JSONDecodeError:
                domain = replit_domains.strip().strip('[]"\'').split(',')[0].strip().strip('"\'')
                logger.warning(f"Failed to parse REPLIT_DOMAINS as JSON, using fallback: {domain}")
            except Exception as e:
                logger.error(f"Error parsing REPLIT_DOMAINS: {e}")
        
        if not domain and replit_dev_domain:
            domain = replit_dev_domain.strip()
            logger.info(f"Detected Replit dev domain from REPLIT_DEV_DOMAIN: {domain}")
        
        if domain:
            domain = domain.strip().strip('"\'')
            
            if not domain or domain.startswith('[') or domain.startswith('{') or '"' in domain or "'" in domain or '://' in domain:
                logger.error(f"Invalid domain detected after parsing: {domain}")
                return None
            
            try:
                test_url = f"https://{domain}"
                parsed = urlparse(test_url)
                if not parsed.netloc or parsed.netloc != domain:
                    logger.error(f"Domain validation failed - invalid structure: {domain}")
                    return None
            except Exception as e:
                logger.error(f"Domain validation error: {e}")
                return None
            
            bot_token = self.config.TELEGRAM_BOT_TOKEN
            webhook_url = f"https://{domain}/bot{bot_token}"
            
            logger.info(f"✅ Auto-constructed webhook URL: {webhook_url}")
            return webhook_url
        
        logger.warning("Could not auto-detect webhook URL - no Replit domain found")
        return None
        
    async def start_health_server(self):
        try:
            async def health_check(request):
                market_status = self.market_data.get_status()
                
                db_status = 'unknown'
                try:
                    session = self.db_manager.get_session()
                    result = session.execute(text('SELECT 1'))
                    result.fetchone()
                    session.close()
                    db_status = 'connected'
                except Exception as e:
                    db_status = f'error: {str(e)[:50]}'
                    logger.error(f"Database health check failed: {e}")
                
                health_status = {
                    'status': 'healthy' if self.running else 'stopped',
                    'market_data': market_status,
                    'telegram_bot': 'running' if self.telegram_bot.app else 'stopped',
                    'scheduler': 'running' if self.task_scheduler.running else 'stopped',
                    'database': db_status,
                    'webhook_mode': self.config.TELEGRAM_WEBHOOK_MODE
                }
                
                return web.json_response(health_status)
            
            async def telegram_webhook(request):
                if not self.config.TELEGRAM_WEBHOOK_MODE:
                    logger.warning("Webhook endpoint called but webhook mode is disabled")
                    return web.json_response({'error': 'Webhook mode is disabled'}, status=400)
                
                if not self.telegram_bot or not self.telegram_bot.app:
                    logger.error("Webhook called but telegram bot not initialized")
                    return web.json_response({'error': 'Bot not initialized'}, status=503)
                
                try:
                    update_data = await request.json()
                    logger.debug(f"Received webhook update: {update_data.get('update_id', 'unknown')}")
                    
                    await self.telegram_bot.process_update(update_data)
                    
                    return web.json_response({'ok': True})
                    
                except Exception as e:
                    logger.error(f"Error processing webhook request: {e}")
                    if self.error_handler:
                        self.error_handler.log_exception(e, "webhook_endpoint")
                    return web.json_response({'error': str(e)}, status=500)
            
            app = web.Application()
            app.router.add_get('/health', health_check)
            app.router.add_get('/', health_check)
            
            webhook_path = f"/bot{self.config.TELEGRAM_BOT_TOKEN}"
            app.router.add_post(webhook_path, telegram_webhook)
            
            runner = web.AppRunner(app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', self.config.HEALTH_CHECK_PORT)
            await site.start()
            
            self.health_server = runner
            logger.info(f"Health check server started on port {self.config.HEALTH_CHECK_PORT}")
            if self.config.TELEGRAM_WEBHOOK_MODE:
                logger.info(f"Webhook endpoint available at: http://0.0.0.0:{self.config.HEALTH_CHECK_PORT}{webhook_path}")
            
        except Exception as e:
            logger.error(f"Failed to start health server: {e}")
    
    async def setup_scheduled_tasks(self):
        bot_components = {
            'chart_generator': self.chart_generator,
            'alert_system': self.alert_system,
            'db_manager': self.db_manager,
            'market_data': self.market_data,
            'position_tracker': self.position_tracker
        }
        
        setup_default_tasks(self.task_scheduler, bot_components)
        logger.info("Scheduled tasks configured")
    
    async def start(self):
        logger.info("=" * 60)
        logger.info("XAUUSD TRADING BOT STARTING")
        logger.info("=" * 60)
        logger.info(f"Mode: {'DRY RUN (Simulation)' if self.config.DRY_RUN else 'LIVE'}")
        
        if self.config.TELEGRAM_BOT_TOKEN:
            logger.info(f"Telegram Bot Token: Configured ({self.config.get_masked_token()})")
            
            if ':' in self.config.TELEGRAM_BOT_TOKEN and len(self.config.TELEGRAM_BOT_TOKEN) > 40:
                logger.warning("⚠️ Bot token detected - ensure it's never logged in plain text")
        else:
            logger.info("Telegram Bot Token: NOT CONFIGURED")
        
        logger.info(f"Authorized Users: {len(self.config.AUTHORIZED_USER_IDS)}")
        
        if self.config.TELEGRAM_WEBHOOK_MODE:
            webhook_url = self._auto_detect_webhook_url()
            if webhook_url:
                self.config.WEBHOOK_URL = webhook_url
                logger.info(f"Webhook URL auto-detected: {webhook_url}")
            else:
                logger.info(f"Webhook mode enabled with URL: {self.config.WEBHOOK_URL}")
        
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
            
            if self.config.TELEGRAM_WEBHOOK_MODE and self.config.WEBHOOK_URL:
                logger.info(f"Setting up webhook: {self.config.WEBHOOK_URL}")
                try:
                    await self.telegram_bot.setup_webhook(self.config.WEBHOOK_URL)
                    logger.info("Webhook setup completed successfully")
                except Exception as e:
                    logger.error(f"Failed to setup webhook: {e}")
                    if self.error_handler:
                        self.error_handler.log_exception(e, "webhook_setup")
            
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
            
            if self.telegram_bot.app and self.config.AUTHORIZED_USER_IDS:
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
                        logger.debug(f"Startup message sent successfully to user {user_id}")
                    except Exception as telegram_error:
                        error_type = type(telegram_error).__name__
                        logger.error(f"Failed to send startup message to user {user_id}: [{error_type}] {telegram_error}")
                        if self.error_handler:
                            self.error_handler.log_exception(telegram_error, f"startup_message_user_{user_id}")
                
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
        if not self.running or self.shutdown_in_progress:
            logger.debug("Shutdown already in progress or bot not running, skipping.")
            return
        
        self.shutdown_in_progress = True
        logger.info("=" * 60)
        logger.info("SHUTTING DOWN BOT...")
        logger.info("=" * 60)
        
        self.running = False
        shutdown_timeout = 10
        
        try:
            if self.telegram_bot and self.telegram_bot.app and self.config.AUTHORIZED_USER_IDS:
                try:
                    shutdown_msg = "🛑 *Bot Shutting Down*\n\nBot is being stopped."
                    
                    async def send_shutdown_messages():
                        for user_id in self.config.AUTHORIZED_USER_IDS:
                            try:
                                await self.telegram_bot.app.bot.send_message(
                                    chat_id=user_id,
                                    text=shutdown_msg,
                                    parse_mode='Markdown'
                                )
                            except Exception as e:
                                logger.error(f"Failed to send shutdown message: {e}")
                    
                    await asyncio.wait_for(send_shutdown_messages(), timeout=shutdown_timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"Sending shutdown messages timed out after {shutdown_timeout}s")
                except Exception as e:
                    logger.error(f"Error sending shutdown messages: {e}")
            
            logger.info("Stopping Telegram bot...")
            if self.telegram_bot:
                try:
                    await asyncio.wait_for(self.telegram_bot.stop(), timeout=shutdown_timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"Telegram bot shutdown timed out after {shutdown_timeout}s")
                except Exception as e:
                    logger.error(f"Error stopping Telegram bot: {e}")
            
            logger.info("Stopping position tracker...")
            if self.position_tracker:
                try:
                    self.position_tracker.stop_monitoring()
                except Exception as e:
                    logger.error(f"Error stopping position tracker: {e}")
            
            logger.info("Stopping task scheduler...")
            if self.task_scheduler:
                try:
                    await asyncio.wait_for(self.task_scheduler.stop(), timeout=shutdown_timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"Task scheduler shutdown timed out after {shutdown_timeout}s")
                except Exception as e:
                    logger.error(f"Error stopping task scheduler: {e}")
            
            logger.info("Stopping chart generator...")
            if self.chart_generator:
                try:
                    self.chart_generator.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down chart generator: {e}")
            
            logger.info("Stopping market data connection...")
            if self.market_data:
                try:
                    self.market_data.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting market data: {e}")
            
            logger.info("Closing database connections...")
            if self.db_manager:
                try:
                    self.db_manager.close()
                except Exception as e:
                    logger.error(f"Error closing database: {e}")
            
            logger.info("Stopping health server...")
            if self.health_server:
                try:
                    await asyncio.wait_for(self.health_server.cleanup(), timeout=shutdown_timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"Health server shutdown timed out after {shutdown_timeout}s")
                except Exception as e:
                    logger.error(f"Error stopping health server: {e}")
            
            logger.info("=" * 60)
            logger.info("BOT SHUTDOWN COMPLETE")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            self.shutdown_in_progress = False

async def main():
    orchestrator = TradingBotOrchestrator()
    loop = asyncio.get_running_loop()
    
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        loop.call_soon_threadsafe(lambda: asyncio.create_task(orchestrator.shutdown()))
    
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
