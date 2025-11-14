import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, timedelta
import pytz
import pandas as pd
from typing import Optional
from bot.logger import setup_logger
from bot.database import Trade, Position, Performance

logger = setup_logger('TelegramBot')

class TradingBot:
    def __init__(self, config, db_manager, strategy, risk_manager, 
                 market_data, position_tracker, chart_generator):
        self.config = config
        self.db = db_manager
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.market_data = market_data
        self.position_tracker = position_tracker
        self.chart_generator = chart_generator
        self.app = None
        self.monitoring = False
        
    def is_authorized(self, user_id: int) -> bool:
        if not self.config.AUTHORIZED_USER_IDS:
            return True
        return user_id in self.config.AUTHORIZED_USER_IDS
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Anda tidak memiliki akses ke bot ini.")
            return
        
        welcome_msg = (
            "🤖 *XAUUSD Trading Bot*\n\n"
            "Bot trading otomatis untuk XAUUSD dengan analisis teknikal.\n\n"
            "*Commands:*\n"
            "/start - Tampilkan pesan ini\n"
            "/help - Bantuan lengkap\n"
            "/monitor - Mulai monitoring sinyal trading\n"
            "/stopmonitor - Stop monitoring\n"
            "/riwayat - Lihat riwayat trading\n"
            "/performa - Statistik performa\n"
            "/settings - Lihat konfigurasi\n\n"
            f"*Mode:* {'DRY RUN (Simulasi)' if self.config.DRY_RUN else 'LIVE'}\n"
        )
        
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        help_msg = (
            "📖 *Bantuan XAUUSD Trading Bot*\n\n"
            "*Cara Kerja:*\n"
            "1. Gunakan /monitor untuk mulai monitoring\n"
            "2. Bot akan menganalisis chart XAUUSD M1 dan M5\n"
            "3. Sinyal BUY/SELL akan dikirim jika kondisi terpenuhi\n"
            "4. Posisi akan dimonitor hingga TP/SL tercapai\n\n"
            "*Indikator:*\n"
            f"- EMA: {', '.join(map(str, self.config.EMA_PERIODS))}\n"
            f"- RSI: {self.config.RSI_PERIOD} (OB/OS: {self.config.RSI_OVERBOUGHT_LEVEL}/{self.config.RSI_OVERSOLD_LEVEL})\n"
            f"- Stochastic: K={self.config.STOCH_K_PERIOD}, D={self.config.STOCH_D_PERIOD}\n"
            f"- ATR: {self.config.ATR_PERIOD}\n\n"
            "*Risk Management:*\n"
            f"- Max trades per day: {self.config.MAX_TRADES_PER_DAY}\n"
            f"- Daily loss limit: {self.config.DAILY_LOSS_PERCENT}%\n"
            f"- Signal cooldown: {self.config.SIGNAL_COOLDOWN_SECONDS}s\n"
            f"- Risk per trade: {self.config.RISK_PER_TRADE_PERCENT}%\n"
        )
        
        await update.message.reply_text(help_msg, parse_mode='Markdown')
    
    async def monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        if self.monitoring:
            await update.message.reply_text("⚠️ Monitoring sudah berjalan!")
            return
        
        self.monitoring = True
        await update.message.reply_text("✅ Monitoring dimulai! Mencari sinyal trading...")
        
        asyncio.create_task(self._monitoring_loop(update.effective_chat.id))
    
    async def stopmonitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        if not self.monitoring:
            await update.message.reply_text("⚠️ Monitoring tidak sedang berjalan.")
            return
        
        self.monitoring = False
        await update.message.reply_text("🛑 Monitoring dihentikan.")
    
    async def _monitoring_loop(self, chat_id: int):
        while self.monitoring:
            try:
                df_m1 = await self.market_data.get_historical_data('M1', 100)
                
                if df_m1 is not None and len(df_m1) >= 50:
                    from bot.indicators import IndicatorEngine
                    indicator_engine = IndicatorEngine(self.config)
                    indicators = indicator_engine.get_indicators(df_m1)
                    
                    if indicators:
                        signal = self.strategy.detect_signal(indicators, 'M1')
                        
                        if signal:
                            can_trade, rejection_reason = self.risk_manager.can_trade(signal['signal'])
                            
                            if can_trade:
                                current_price = await self.market_data.get_current_price()
                                spread = 0.5
                                
                                is_valid, validation_msg = self.strategy.validate_signal(signal, spread)
                                
                                if is_valid:
                                    await self._send_signal(chat_id, signal, df_m1)
                                    self.risk_manager.record_signal()
                                else:
                                    logger.info(f"Signal validation failed: {validation_msg}")
                            else:
                                logger.info(f"Trade rejected: {rejection_reason}")
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _send_signal(self, chat_id: int, signal: dict, df: Optional[pd.DataFrame] = None):
        try:
            session = self.db.get_session()
            
            trade = Trade(
                ticker='XAUUSD',
                signal_type=signal['signal'],
                entry_price=signal['entry_price'],
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit'],
                timeframe=signal['timeframe'],
                status='OPEN'
            )
            session.add(trade)
            session.commit()
            trade_id = trade.id
            session.close()
            
            estimated_pl = self.risk_manager.calculate_pl(
                signal['entry_price'],
                signal['take_profit'],
                signal['signal']
            )
            
            sl_pips = abs(signal['entry_price'] - signal['stop_loss']) * self.config.XAUUSD_PIP_VALUE
            tp_pips = abs(signal['entry_price'] - signal['take_profit']) * self.config.XAUUSD_PIP_VALUE
            
            msg = (
                f"🚨 *{signal['signal']} SIGNAL*\n\n"
                f"*Ticker:* XAUUSD\n"
                f"*Timeframe:* {signal['timeframe']}\n"
                f"*Entry:* ${signal['entry_price']:.2f}\n"
                f"*Stop Loss:* ${signal['stop_loss']:.2f} ({sl_pips:.1f} pips)\n"
                f"*Take Profit:* ${signal['take_profit']:.2f} ({tp_pips:.1f} pips)\n"
                f"*Estimated P/L:* ${estimated_pl:.2f}\n\n"
                f"*Confidence:* {', '.join(signal.get('confidence_reasons', []))}\n"
            )
            
            if self.app and self.app.bot:
                await self.app.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
                
                if df is not None:
                    chart_path = self.chart_generator.generate_chart(df, signal, signal['timeframe'])
                    if chart_path:
                        with open(chart_path, 'rb') as photo:
                            await self.app.bot.send_photo(chat_id=chat_id, photo=photo)
            
            await self.position_tracker.add_position(
                trade_id,
                signal['signal'],
                signal['entry_price'],
                signal['stop_loss'],
                signal['take_profit']
            )
            
        except Exception as e:
            logger.error(f"Error sending signal: {e}")
    
    async def riwayat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        try:
            session = self.db.get_session()
            trades = session.query(Trade).order_by(Trade.signal_time.desc()).limit(10).all()
            
            if not trades:
                await update.message.reply_text("📊 Belum ada riwayat trading.")
                return
            
            msg = "📊 *Riwayat Trading (10 Terakhir):*\n\n"
            
            jakarta_tz = pytz.timezone('Asia/Jakarta')
            
            for trade in trades:
                signal_time = trade.signal_time.replace(tzinfo=pytz.UTC).astimezone(jakarta_tz)
                
                msg += f"*{trade.signal_type}* - {signal_time.strftime('%d/%m %H:%M')}\n"
                msg += f"Entry: ${trade.entry_price:.2f}\n"
                
                if trade.status == 'CLOSED':
                    result_emoji = "✅" if trade.result == 'WIN' else "❌"
                    msg += f"Exit: ${trade.exit_price:.2f}\n"
                    msg += f"P/L: ${trade.actual_pl:.2f} {result_emoji}\n"
                else:
                    msg += f"Status: {trade.status}\n"
                
                msg += "\n"
            
            session.close()
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error fetching history: {e}")
            await update.message.reply_text("❌ Error mengambil riwayat.")
    
    async def performa_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        try:
            session = self.db.get_session()
            
            all_trades = session.query(Trade).filter(Trade.status == 'CLOSED').all()
            
            if not all_trades:
                await update.message.reply_text("📊 Belum ada data performa.")
                return
            
            total_trades = len(all_trades)
            wins = len([t for t in all_trades if t.result == 'WIN'])
            losses = len([t for t in all_trades if t.result == 'LOSS'])
            total_pl = sum([t.actual_pl for t in all_trades if t.actual_pl])
            
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            today = datetime.now(pytz.timezone('Asia/Jakarta')).replace(hour=0, minute=0, second=0, microsecond=0)
            today_utc = today.astimezone(pytz.UTC)
            
            today_trades = session.query(Trade).filter(
                Trade.signal_time >= today_utc,
                Trade.status == 'CLOSED'
            ).all()
            
            today_pl = sum([t.actual_pl for t in today_trades if t.actual_pl])
            
            msg = (
                "📊 *Statistik Performa*\n\n"
                f"*Total Trades:* {total_trades}\n"
                f"*Wins:* {wins} ✅\n"
                f"*Losses:* {losses} ❌\n"
                f"*Win Rate:* {win_rate:.1f}%\n"
                f"*Total P/L:* ${total_pl:.2f}\n"
                f"*Avg P/L per Trade:* ${total_pl/total_trades:.2f}\n\n"
                f"*Hari Ini:*\n"
                f"Trades: {len(today_trades)}\n"
                f"P/L: ${today_pl:.2f}\n"
            )
            
            session.close()
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error calculating performance: {e}")
            await update.message.reply_text("❌ Error menghitung performa.")
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        msg = (
            "⚙️ *Konfigurasi Bot*\n\n"
            f"*Mode:* {'DRY RUN' if self.config.DRY_RUN else 'LIVE'}\n\n"
            "*Indikator:*\n"
            f"EMA Periods: {', '.join(map(str, self.config.EMA_PERIODS))}\n"
            f"RSI Period: {self.config.RSI_PERIOD}\n"
            f"ATR Period: {self.config.ATR_PERIOD}\n\n"
            "*Risk Management:*\n"
            f"Max Trades/Day: {self.config.MAX_TRADES_PER_DAY}\n"
            f"Daily Loss Limit: {self.config.DAILY_LOSS_PERCENT}%\n"
            f"Signal Cooldown: {self.config.SIGNAL_COOLDOWN_SECONDS}s\n"
            f"SL ATR Multiplier: {self.config.SL_ATR_MULTIPLIER}x\n"
            f"TP/RR Ratio: {self.config.TP_RR_RATIO}x\n\n"
            "*Position:*\n"
            f"Lot Size: {self.config.LOT_SIZE}\n"
            f"Max Spread: {self.config.MAX_SPREAD_PIPS} pips\n"
        )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def run(self):
        if not self.config.TELEGRAM_BOT_TOKEN:
            logger.error("Telegram bot token not configured!")
            return
        
        self.app = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
        
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("monitor", self.monitor_command))
        self.app.add_handler(CommandHandler("stopmonitor", self.stopmonitor_command))
        self.app.add_handler(CommandHandler("riwayat", self.riwayat_command))
        self.app.add_handler(CommandHandler("performa", self.performa_command))
        self.app.add_handler(CommandHandler("settings", self.settings_command))
        
        logger.info("Telegram bot starting...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        logger.info("Telegram bot is running!")
