import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, timedelta
import pytz
import pandas as pd
from typing import Optional, List
from bot.logger import setup_logger
from bot.database import Trade, Position, Performance

logger = setup_logger('TelegramBot')

class TradingBot:
    def __init__(self, config, db_manager, strategy, risk_manager, 
                 market_data, position_tracker, chart_generator,
                 alert_system=None, error_handler=None, user_manager=None):
        self.config = config
        self.db = db_manager
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.market_data = market_data
        self.position_tracker = position_tracker
        self.chart_generator = chart_generator
        self.alert_system = alert_system
        self.error_handler = error_handler
        self.user_manager = user_manager
        self.app = None
        self.monitoring = False
        self.monitoring_chats = []
        self.signal_lock = asyncio.Lock()
        
    def is_authorized(self, user_id: int) -> bool:
        if self.user_manager:
            return self.user_manager.has_access(user_id)
        
        if not self.config.AUTHORIZED_USER_IDS:
            return True
        return user_id in self.config.AUTHORIZED_USER_IDS
    
    def is_admin(self, user_id: int) -> bool:
        if self.user_manager:
            user = self.user_manager.get_user(user_id)
            return user.is_admin if user else False
        return user_id in self.config.AUTHORIZED_USER_IDS
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.user_manager:
            self.user_manager.create_user(
                telegram_id=update.effective_user.id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
                last_name=update.effective_user.last_name
            )
            self.user_manager.update_user_activity(update.effective_user.id)
        
        if not self.is_authorized(update.effective_user.id):
            expired_msg = (
                "⛔ *Akses Ditolak*\n\n"
                "Anda tidak memiliki akses ke bot ini atau masa trial Anda telah berakhir.\n\n"
                "💎 *Untuk menggunakan bot:*\n"
                "Hubungi admin untuk upgrade ke premium:\n"
                "@dzeckyete\n\n"
                "*Paket Premium:*\n"
                "• 1 Minggu: Rp 15.000\n"
                "• 1 Bulan: Rp 30.000\n\n"
                "Setelah pembayaran, admin akan mengaktifkan akses Anda."
            )
            await update.message.reply_text(expired_msg, parse_mode='Markdown')
            return
        
        user_status = "Admin (Unlimited)" if self.is_admin(update.effective_user.id) else "User Premium"
        mode = "LIVE" if not self.config.DRY_RUN else "DRY RUN"
        
        welcome_msg = (
            "🤖 *XAUUSD Trading Bot Pro*\n\n"
            "Bot trading otomatis untuk XAUUSD dengan analisis teknikal canggih.\n\n"
            f"👑 Status: {user_status}\n\n"
            "*Commands:*\n"
            "/start - Tampilkan pesan ini\n"
            "/help - Bantuan lengkap\n"
            "/langganan - Cek status langganan\n"
            "/monitor - Mulai monitoring sinyal\n"
            "/stopmonitor - Stop monitoring\n"
            "/getsignal - Dapatkan sinyal manual\n"
            "/riwayat - Lihat riwayat trading\n"
            "/performa - Statistik performa\n"
            "/settings - Lihat konfigurasi\n"
        )
        
        if self.is_admin(update.effective_user.id):
            welcome_msg += (
                "\n*Admin Commands:*\n"
                "/riset - Reset database trading\n"
                "/addpremium - Tambah premium user\n"
            )
        
        welcome_msg += f"\n*Mode:* {mode}\n"
        welcome_msg += (
            "\n💎 *Paket Premium:*\n"
            "• 1 Minggu: Rp 15.000\n"
            "• 1 Bulan: Rp 30.000\n"
            "Hubungi: @dzeckyete\n"
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
            f"- Max trades per day: Unlimited (24/7)\n"
            f"- Daily loss limit: {self.config.DAILY_LOSS_PERCENT}%\n"
            f"- Signal cooldown: {self.config.SIGNAL_COOLDOWN_SECONDS}s\n"
            f"- Risk per trade: ${self.config.FIXED_RISK_AMOUNT:.2f} (Fixed)\n"
        )
        
        await update.message.reply_text(help_msg, parse_mode='Markdown')
    
    async def monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        chat_id = update.effective_chat.id
        
        if self.monitoring and chat_id in self.monitoring_chats:
            await update.message.reply_text("⚠️ Monitoring sudah berjalan untuk Anda!")
            return
        
        if not self.monitoring:
            self.monitoring = True
        
        if chat_id not in self.monitoring_chats:
            self.monitoring_chats.append(chat_id)
            await update.message.reply_text("✅ Monitoring dimulai! Bot akan mendeteksi sinyal secara real-time...")
            asyncio.create_task(self._monitoring_loop(chat_id))
    
    async def auto_start_monitoring(self, chat_ids: List[int]):
        if not self.monitoring:
            self.monitoring = True
        
        for chat_id in chat_ids:
            if chat_id not in self.monitoring_chats:
                self.monitoring_chats.append(chat_id)
                logger.info(f"Auto-starting monitoring for chat {chat_id}")
                asyncio.create_task(self._monitoring_loop(chat_id))
    
    async def stopmonitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        chat_id = update.effective_chat.id
        
        if chat_id in self.monitoring_chats:
            self.monitoring_chats.remove(chat_id)
            await update.message.reply_text("🛑 Monitoring dihentikan untuk Anda.")
            
            if len(self.monitoring_chats) == 0:
                self.monitoring = False
                logger.info("All monitoring stopped")
        else:
            await update.message.reply_text("⚠️ Monitoring tidak sedang berjalan untuk Anda.")
    
    async def _monitoring_loop(self, chat_id: int):
        tick_queue = await self.market_data.subscribe_ticks(f'telegram_bot_{chat_id}')
        logger.info(f"Monitoring loop subscribed ke tick feed for chat {chat_id} - mode real-time aktif")
        
        last_signal_check = datetime.now() - timedelta(seconds=self.config.SIGNAL_COOLDOWN_SECONDS)
        
        try:
            while self.monitoring and chat_id in self.monitoring_chats:
                try:
                    tick = await tick_queue.get()
                    
                    now = datetime.now()
                    time_since_last_check = (now - last_signal_check).total_seconds()
                    
                    if time_since_last_check < self.config.SIGNAL_COOLDOWN_SECONDS:
                        logger.debug(f"⏱️ Cooldown: {time_since_last_check:.1f}s / {self.config.SIGNAL_COOLDOWN_SECONDS}s")
                        continue
                    
                    logger.info(f"✅ Cooldown passed ({time_since_last_check:.1f}s), fetching candles...")
                    df_m1 = await self.market_data.get_historical_data('M1', 100)
                    
                    if df_m1 is None:
                        logger.warning("⚠️ get_historical_data returned None")
                        continue
                    
                    candle_count = len(df_m1)
                    logger.info(f"📈 Got {candle_count} candles from market data")
                    
                    if candle_count >= 30:
                        logger.info(f"📊 Analyzing {len(df_m1)} M1 candles for signals...")
                        from bot.indicators import IndicatorEngine
                        indicator_engine = IndicatorEngine(self.config)
                        indicators = indicator_engine.get_indicators(df_m1)
                        
                        if indicators:
                            logger.info("🔍 Indicators calculated, checking for signals...")
                            
                            if self.position_tracker.has_active_position():
                                logger.info("⏳ Posisi aktif sedang berjalan - menunggu TP/SL tercapai...")
                                continue
                            
                            signal = self.strategy.detect_signal(indicators, 'M1', signal_source='auto')
                            
                            if signal:
                                logger.info(f"🚨 Signal detected: {signal['signal']}")
                                can_trade, rejection_reason = self.risk_manager.can_trade(signal['signal'])
                                
                                if can_trade:
                                    current_price = await self.market_data.get_current_price()
                                    spread_value = await self.market_data.get_spread()
                                    spread = spread_value if spread_value else 0.5
                                    
                                    is_valid, validation_msg = self.strategy.validate_signal(signal, spread)
                                    
                                    if is_valid:
                                        async with self.signal_lock:
                                            for monitoring_chat_id in self.monitoring_chats:
                                                await self._send_signal(monitoring_chat_id, signal, df_m1)
                                        
                                        self.risk_manager.record_signal()
                                        last_signal_check = now
                                        
                                        if self.user_manager:
                                            self.user_manager.update_user_activity(chat_id)
                                    else:
                                        logger.info(f"❌ Signal validation failed: {validation_msg}")
                                else:
                                    logger.info(f"⛔ Trade rejected: {rejection_reason}")
                            else:
                                logger.debug("No signal detected in current candles")
                        else:
                            logger.warning("⚠️ Failed to calculate indicators - not enough data")
                    else:
                        logger.warning(f"❌ Not enough candles: {candle_count}/30 required for indicator calculation")
                    
                except Exception as e:
                    logger.error(f"Error processing tick dalam monitoring loop: {e}")
                    await asyncio.sleep(1)
                    
        finally:
            await self.market_data.unsubscribe_ticks(f'telegram_bot_{chat_id}')
            logger.info(f"Monitoring loop unsubscribed dari tick feed for chat {chat_id}")
    
    async def _send_signal(self, chat_id: int, signal: dict, df: Optional[pd.DataFrame] = None):
        try:
            session = self.db.get_session()
            
            signal_source = signal.get('signal_source', 'auto')
            
            trade = Trade(
                ticker='XAUUSD',
                signal_type=signal['signal'],
                signal_source=signal_source,
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
            
            sl_pips = abs(signal['entry_price'] - signal['stop_loss']) * self.config.XAUUSD_PIP_VALUE
            tp_pips = abs(signal['entry_price'] - signal['take_profit']) * self.config.XAUUSD_PIP_VALUE
            
            source_icon = "🤖" if signal_source == 'auto' else "👤"
            source_text = "OTOMATIS" if signal_source == 'auto' else "MANUAL"
            
            msg = (
                f"🚨 *SINYAL {signal['signal']}* {source_icon}\n\n"
                f"*Source:* {source_text}\n"
                f"*Ticker:* XAUUSD\n"
                f"*Timeframe:* {signal['timeframe']}\n"
                f"*Entry:* ${signal['entry_price']:.2f}\n"
                f"*Stop Loss:* ${signal['stop_loss']:.2f} ({sl_pips:.1f} pips)\n"
                f"*Take Profit:* ${signal['take_profit']:.2f} ({tp_pips:.1f} pips)\n"
            )
            
            if 'confidence_reasons' in signal and signal['confidence_reasons']:
                msg += f"\n*Alasan:*\n"
                for reason in signal['confidence_reasons']:
                    msg += f"• {reason}\n"
            
            if self.app and self.app.bot:
                await self.app.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
                
                if df is not None and len(df) >= 30:
                    chart_path = self.chart_generator.generate_chart(df, signal, signal['timeframe'])
                    if chart_path:
                        with open(chart_path, 'rb') as photo:
                            await self.app.bot.send_photo(chat_id=chat_id, photo=photo)
                        
                        if self.config.CHART_AUTO_DELETE:
                            await asyncio.sleep(2)
                            self.chart_generator.delete_chart(chart_path)
                            logger.info(f"Auto-deleted chart after sending: {chart_path}")
                    else:
                        logger.warning(f"Chart generation failed for {signal['signal']} signal")
                else:
                    logger.info(f"Skipping chart - insufficient candles ({len(df) if df is not None else 0}/30)")
            
            await self.position_tracker.add_position(
                trade_id,
                signal['signal'],
                signal['entry_price'],
                signal['stop_loss'],
                signal['take_profit']
            )
            logger.info(f"Position {trade_id} added to tracker: {signal['signal']} @ ${signal['entry_price']:.2f}")
            
        except Exception as e:
            logger.error(f"Error sending signal: {e}")
            if self.error_handler:
                self.error_handler.log_exception(e, "send_signal")
            if self.alert_system:
                await self.alert_system.send_system_error(f"Error sending signal: {str(e)}")
    
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
    
    async def getsignal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        try:
            if self.position_tracker and len(self.position_tracker.active_positions) > 0:
                await update.message.reply_text(
                    "⏳ *Tidak Dapat Membuat Sinyal Baru*\n\n"
                    "Saat ini ada posisi aktif yang sedang berjalan.\n"
                    "Bot akan tracking hingga TP/SL tercapai.\n\n"
                    "Tunggu hasil posisi saat ini sebelum request sinyal baru.",
                    parse_mode='Markdown'
                )
                return
            
            await update.message.reply_text("🔍 Menganalisis chart untuk sinyal manual...")
            
            df_m1 = await self.market_data.get_historical_data('M1', 100)
            
            if df_m1 is None or len(df_m1) < 30:
                await update.message.reply_text(
                    f"❌ Tidak cukup data candles!\n"
                    f"Tersedia: {len(df_m1) if df_m1 is not None else 0} candles\n"
                    f"Dibutuhkan: 30 candles minimum\n\n"
                    "Tunggu beberapa menit lagi untuk bot build candles."
                )
                return
            
            from bot.indicators import IndicatorEngine
            indicator_engine = IndicatorEngine(self.config)
            indicators = indicator_engine.get_indicators(df_m1)
            
            if not indicators:
                await update.message.reply_text("❌ Gagal menghitung indikator. Coba lagi.")
                return
            
            signal = self.strategy.detect_signal(indicators, 'M1', signal_source='manual')
            
            if not signal:
                await update.message.reply_text(
                    "❌ *Tidak Ada Sinyal Saat Ini*\n\n"
                    "Kondisi market tidak memenuhi kriteria strategi.\n"
                    "Silakan coba lagi nanti atau gunakan /monitor untuk deteksi otomatis.",
                    parse_mode='Markdown'
                )
                return
            
            current_price = await self.market_data.get_current_price()
            spread_value = await self.market_data.get_spread()
            spread = spread_value if spread_value else 0.5
            
            is_valid, validation_msg = self.strategy.validate_signal(signal, spread)
            
            if not is_valid:
                await update.message.reply_text(
                    f"⚠️ *Sinyal Tidak Valid*\n\n"
                    f"Alasan: {validation_msg}\n\n"
                    f"Signal: {signal['signal']}\n"
                    f"Entry: ${signal['entry_price']:.2f}\n"
                    f"SL: ${signal['stop_loss']:.2f}\n"
                    f"TP: ${signal['take_profit']:.2f}",
                    parse_mode='Markdown'
                )
                return
            
            chat_id = update.effective_chat.id
            async with self.signal_lock:
                await self._send_signal(chat_id, signal, df_m1)
            
            logger.info(f"Manual signal sent to chat {chat_id}: {signal['signal']}")
            
        except Exception as e:
            logger.error(f"Error in getsignal_command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
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
            f"Max Trades/Day: Unlimited (24/7)\n"
            f"Daily Loss Limit: {self.config.DAILY_LOSS_PERCENT}%\n"
            f"Signal Cooldown: {self.config.SIGNAL_COOLDOWN_SECONDS}s\n"
            f"SL ATR Multiplier: {self.config.SL_ATR_MULTIPLIER}x\n"
            f"TP/RR Ratio: {self.config.TP_RR_RATIO}x\n\n"
            "*Position:*\n"
            f"Lot Size: {self.config.LOT_SIZE}\n"
            f"Max Spread: {self.config.MAX_SPREAD_PIPS} pips\n"
        )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def langganan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.user_manager:
            self.user_manager.create_user(
                telegram_id=update.effective_user.id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
                last_name=update.effective_user.last_name
            )
        
        if not self.is_authorized(update.effective_user.id):
            expired_msg = (
                "⛔ *Akses Ditolak*\n\n"
                "Anda tidak memiliki akses ke bot ini atau masa trial Anda telah berakhir.\n\n"
                "💎 *Untuk menggunakan bot:*\n"
                "Hubungi admin untuk upgrade ke premium:\n"
                "@dzeckyete\n\n"
                "*Paket Premium:*\n"
                "• 1 Minggu: Rp 15.000\n"
                "• 1 Bulan: Rp 30.000\n\n"
                "Setelah pembayaran, admin akan mengaktifkan akses Anda."
            )
            await update.message.reply_text(expired_msg, parse_mode='Markdown')
            return
        
        if self.user_manager:
            status = self.user_manager.get_subscription_status(update.effective_user.id)
            
            if status:
                if status['tier'] == 'ADMIN':
                    msg = (
                        "💎 *Status Langganan*\n\n"
                        f"👑 Tier: {status['tier']}\n"
                        f"✅ Status: {status['status']}\n\n"
                        "Anda memiliki akses unlimited sebagai admin!"
                    )
                elif status['status'] == 'Aktif':
                    msg = (
                        "💎 *Status Langganan*\n\n"
                        f"📦 Tier: {status['tier']}\n"
                        f"✅ Status: {status['status']}\n"
                        f"📅 Berakhir: {status['expires']}\n"
                        f"⏰ Sisa: {status['days_left']} hari\n\n"
                        "Untuk perpanjang, hubungi @dzeckyete"
                    )
                else:
                    msg = (
                        "💎 *Status Langganan*\n\n"
                        f"📦 Tier: {status['tier']}\n"
                        f"❌ Status: {status['status']}\n\n"
                        "*Paket Premium:*\n"
                        "• 1 Minggu: Rp 15.000\n"
                        "• 1 Bulan: Rp 30.000\n\n"
                        "Hubungi @dzeckyete untuk berlangganan!"
                    )
                
                await update.message.reply_text(msg, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Gagal mengambil status langganan.")
        else:
            await update.message.reply_text("❌ User manager tidak tersedia.")
    
    async def riset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Command ini hanya untuk admin.")
            return
        
        try:
            session = self.db.get_session()
            
            session.query(Trade).delete()
            session.query(Position).delete()
            session.query(Performance).delete()
            session.commit()
            session.close()
            
            await update.message.reply_text("✅ Database trading berhasil direset!")
            logger.info(f"Database reset by admin: {update.effective_user.id}")
            
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def addpremium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"/addpremium called by user {update.effective_user.id}")
        
        if not self.is_admin(update.effective_user.id):
            logger.warning(f"Non-admin user {update.effective_user.id} tried to use /addpremium")
            await update.message.reply_text("⛔ Command ini hanya untuk admin.")
            return
        
        logger.info(f"Admin verified, args: {context.args}")
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ Format salah!\n\n"
                "*Penggunaan:*\n"
                "/addpremium <user_id/@username> <durasi>\n\n"
                "*Durasi:*\n"
                "• 1week - 1 Minggu\n"
                "• 1month - 1 Bulan\n\n"
                "*Contoh:*\n"
                "/addpremium 123456789 1month\n"
                "/addpremium @dzeckyete 1week",
                parse_mode='Markdown'
            )
            return
        
        try:
            user_input = context.args[0]
            duration = context.args[1]
            
            if duration not in ['1week', '1month']:
                await update.message.reply_text("❌ Durasi tidak valid! Gunakan: 1week atau 1month")
                return
            
            target_user_id = None
            
            if user_input.startswith('@'):
                username = user_input[1:]
                
                if self.user_manager:
                    target_user_id = self.user_manager.get_user_by_username(username)
                
                if not target_user_id:
                    await update.message.reply_text(
                        f"❌ Username @{username} tidak ditemukan!\n\n"
                        "User harus mengirim /start ke bot terlebih dahulu."
                    )
                    return
            else:
                try:
                    target_user_id = int(user_input)
                except ValueError:
                    await update.message.reply_text("❌ Format salah! Gunakan user ID (angka) atau @username")
                    return
            
            if self.user_manager:
                self.user_manager.create_user(telegram_id=target_user_id)
                
                success = self.user_manager.upgrade_subscription(target_user_id, duration)
                
                if success:
                    status = self.user_manager.get_subscription_status(target_user_id)
                    
                    duration_text = "1 Minggu" if duration == '1week' else "1 Bulan"
                    
                    msg = (
                        f"✅ Berhasil menambahkan premium!\n\n"
                        f"User ID: {target_user_id}\n"
                        f"Username: @{user_input[1:] if user_input.startswith('@') else 'N/A'}\n"
                        f"Durasi: {duration_text}\n"
                        f"Berakhir: {status['expires']}\n"
                    )
                    await update.message.reply_text(msg)
                    logger.info(f"Admin {update.effective_user.id} added premium to {target_user_id} for {duration}")
                    
                    try:
                        await self.app.bot.send_message(
                            chat_id=target_user_id,
                            text=f"🎉 *Selamat!*\n\nAkun Anda telah diupgrade ke premium!\n\n"
                                 f"Durasi: {duration_text}\n"
                                 f"Berakhir: {status['expires']}\n\n"
                                 f"Gunakan /monitor untuk mulai menerima sinyal trading.",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.warning(f"Could not send notification to user {target_user_id}: {e}")
                else:
                    await update.message.reply_text("❌ Gagal menambahkan premium.")
            else:
                await update.message.reply_text("❌ User manager tidak tersedia.")
                
        except Exception as e:
            logger.error(f"Error adding premium: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def initialize(self):
        if not self.config.TELEGRAM_BOT_TOKEN:
            logger.error("Telegram bot token not configured!")
            return False
        
        self.app = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
        
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("langganan", self.langganan_command))
        self.app.add_handler(CommandHandler("monitor", self.monitor_command))
        self.app.add_handler(CommandHandler("stopmonitor", self.stopmonitor_command))
        self.app.add_handler(CommandHandler("getsignal", self.getsignal_command))
        self.app.add_handler(CommandHandler("riwayat", self.riwayat_command))
        self.app.add_handler(CommandHandler("performa", self.performa_command))
        self.app.add_handler(CommandHandler("settings", self.settings_command))
        self.app.add_handler(CommandHandler("riset", self.riset_command))
        self.app.add_handler(CommandHandler("addpremium", self.addpremium_command))
        
        logger.info("Initializing Telegram bot...")
        await self.app.initialize()
        await self.app.start()
        logger.info("Telegram bot initialized and ready!")
        return True
    
    async def run(self):
        if not self.app:
            logger.error("Bot not initialized! Call initialize() first.")
            return
        
        logger.info("Starting Telegram bot polling...")
        await self.app.updater.start_polling()
        logger.info("Telegram bot is running!")
    
    async def stop(self):
        if not self.app:
            return
        
        logger.info("Stopping Telegram bot polling...")
        try:
            if self.app.updater and self.app.updater.running:
                await self.app.updater.stop()
                logger.info("Telegram bot polling stopped")
        except Exception as e:
            logger.error(f"Error stopping updater: {e}")
        
        try:
            await self.app.stop()
            logger.info("Telegram bot application stopped")
        except Exception as e:
            logger.error(f"Error stopping app: {e}")
        
        try:
            await self.app.shutdown()
            logger.info("Telegram bot application shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down app: {e}")
