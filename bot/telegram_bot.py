import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, timedelta
import pytz
import pandas as pd
from typing import Optional, List
from bot.logger import setup_logger, mask_user_id, mask_token, sanitize_log_message
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
        self.monitoring_tasks = []
        
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
            task = asyncio.create_task(self._monitoring_loop(chat_id))
            self.monitoring_tasks.append(task)
    
    async def auto_start_monitoring(self, chat_ids: List[int]):
        if not self.monitoring:
            self.monitoring = True
        
        for chat_id in chat_ids:
            if chat_id not in self.monitoring_chats:
                self.monitoring_chats.append(chat_id)
                logger.info(f"Auto-starting monitoring for chat {mask_user_id(chat_id)}")
                task = asyncio.create_task(self._monitoring_loop(chat_id))
                self.monitoring_tasks.append(task)
    
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
        logger.debug(f"Monitoring started for user {mask_user_id(chat_id)}")
        
        last_signal_check = datetime.now() - timedelta(seconds=self.config.SIGNAL_COOLDOWN_SECONDS)
        
        try:
            while self.monitoring and chat_id in self.monitoring_chats:
                try:
                    tick = await tick_queue.get()
                    
                    now = datetime.now()
                    time_since_last_check = (now - last_signal_check).total_seconds()
                    
                    if time_since_last_check < self.config.SIGNAL_COOLDOWN_SECONDS:
                        continue
                    
                    df_m1 = await self.market_data.get_historical_data('M1', 100)
                    
                    if df_m1 is None:
                        continue
                    
                    candle_count = len(df_m1)
                    
                    if candle_count >= 30:
                        from bot.indicators import IndicatorEngine
                        indicator_engine = IndicatorEngine(self.config)
                        indicators = indicator_engine.get_indicators(df_m1)
                        
                        if indicators:
                            signal = self.strategy.detect_signal(indicators, 'M1', signal_source='auto')
                            
                            if signal:
                                can_trade, rejection_reason = self.risk_manager.can_trade(chat_id, signal['signal'])
                                
                                if can_trade:
                                    current_price = await self.market_data.get_current_price()
                                    spread_value = await self.market_data.get_spread()
                                    spread = spread_value if spread_value else 0.5
                                    
                                    is_valid, validation_msg = self.strategy.validate_signal(signal, spread)
                                    
                                    if is_valid:
                                        async with self.signal_lock:
                                            if self.position_tracker.has_active_position(chat_id):
                                                continue
                                            
                                            await self._send_signal(chat_id, chat_id, signal, df_m1)
                                        
                                        self.risk_manager.record_signal(chat_id)
                                        last_signal_check = now
                                        
                                        if self.user_manager:
                                            self.user_manager.update_user_activity(chat_id)
                    
                except asyncio.CancelledError:
                    logger.info(f"Monitoring loop cancelled for user {mask_user_id(chat_id)}")
                    break
                except Exception as e:
                    logger.error(f"Error processing tick dalam monitoring loop: {e}")
                    await asyncio.sleep(1)
                    
        finally:
            await self.market_data.unsubscribe_ticks(f'telegram_bot_{chat_id}')
            logger.debug(f"Monitoring stopped for user {mask_user_id(chat_id)}")
    
    async def _send_signal(self, user_id: int, chat_id: int, signal: dict, df: Optional[pd.DataFrame] = None):
        try:
            session = self.db.get_session()
            
            signal_source = signal.get('signal_source', 'auto')
            
            trade = Trade(
                user_id=user_id,
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
            
            sl_pips = signal.get('sl_pips', abs(signal['entry_price'] - signal['stop_loss']) * self.config.XAUUSD_PIP_VALUE)
            tp_pips = signal.get('tp_pips', abs(signal['entry_price'] - signal['take_profit']) * self.config.XAUUSD_PIP_VALUE)
            lot_size = signal.get('lot_size', self.config.LOT_SIZE)
            
            source_icon = "🤖" if signal_source == 'auto' else "👤"
            source_text = "OTOMATIS" if signal_source == 'auto' else "MANUAL"
            
            trend_desc = signal.get('trend_description', 'MEDIUM ⚡')
            expected_profit = signal.get('expected_profit', 1.5)
            expected_loss = signal.get('expected_loss', 1.0)
            rr_ratio = signal.get('rr_ratio', 1.5)
            
            msg = (
                f"🚨 *SINYAL {signal['signal']}* {source_icon}\n\n"
                f"*Source:* {source_text}\n"
                f"*Ticker:* XAUUSD\n"
                f"*Timeframe:* {signal['timeframe']}\n"
                f"*Trend Strength:* {trend_desc}\n\n"
                f"*Entry:* ${signal['entry_price']:.2f}\n"
                f"*Stop Loss:* ${signal['stop_loss']:.2f} ({sl_pips:.1f} pips)\n"
                f"*Take Profit:* ${signal['take_profit']:.2f} ({tp_pips:.1f} pips)\n"
                f"*Lot Size:* {lot_size:.2f} lot\n\n"
                f"💰 *Risk Management:*\n"
                f"• Max Loss: ${expected_loss:.2f}\n"
                f"• Target Profit: ${expected_profit:.2f}\n"
                f"• R:R Ratio: 1:{rr_ratio:.2f}\n"
            )
            
            if 'confidence_reasons' in signal and signal['confidence_reasons']:
                msg += f"\n*Alasan Teknikal:*\n"
                for reason in signal['confidence_reasons']:
                    msg += f"• {reason}\n"
            
            if self.app and self.app.bot:
                await self.app.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
                
                if df is not None and len(df) >= 30:
                    chart_path = await self.chart_generator.generate_chart_async(df, signal, signal['timeframe'])
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
                user_id,
                trade_id,
                signal['signal'],
                signal['entry_price'],
                signal['stop_loss'],
                signal['take_profit']
            )
            logger.info(f"Trade {trade_id} User:{mask_user_id(user_id)} {signal['signal']} @${signal['entry_price']:.2f}")
            
        except Exception as e:
            logger.error(f"Error sending signal: {e}")
            if self.error_handler:
                self.error_handler.log_exception(e, "send_signal")
            if self.alert_system:
                await self.alert_system.send_system_error(f"Error sending signal: {str(e)}")
    
    async def riwayat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        user_id = update.effective_user.id
        
        try:
            session = self.db.get_session()
            trades = session.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.signal_time.desc()).limit(10).all()
            
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
        
        user_id = update.effective_user.id
        
        try:
            session = self.db.get_session()
            
            all_trades = session.query(Trade).filter(Trade.user_id == user_id, Trade.status == 'CLOSED').all()
            
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
                Trade.user_id == user_id,
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
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show active positions with dynamic SL/TP tracking info"""
        if not self.is_authorized(update.effective_user.id):
            return
        
        user_id = update.effective_user.id
        
        try:
            if not self.position_tracker:
                await update.message.reply_text("❌ Position tracker tidak tersedia.")
                return
            
            active_positions = self.position_tracker.get_active_positions(user_id)
            
            if not active_positions:
                await update.message.reply_text(
                    "📊 *Position Status*\n\n"
                    "Tidak ada posisi aktif saat ini.\n"
                    "Gunakan /getsignal untuk membuat sinyal baru.",
                    parse_mode='Markdown'
                )
                return
            
            session = self.db.get_session()
            
            msg = f"📊 *Active Positions* ({len(active_positions)})\n\n"
            
            for pos_id, pos_data in active_positions.items():
                position_db = session.query(Position).filter(
                    Position.id == pos_id,
                    Position.user_id == user_id
                ).first()
                
                if not position_db:
                    continue
                
                signal_type = pos_data['signal_type']
                entry_price = pos_data['entry_price']
                current_sl = pos_data['stop_loss']
                original_sl = pos_data.get('original_sl', current_sl)
                take_profit = pos_data['take_profit']
                sl_count = pos_data.get('sl_adjustment_count', 0)
                max_profit = pos_data.get('max_profit_reached', 0.0)
                
                unrealized_pl = position_db.unrealized_pl or 0.0
                current_price = position_db.current_price or entry_price
                
                pl_emoji = "🟢" if unrealized_pl > 0 else "🔴" if unrealized_pl < 0 else "⚪"
                
                msg += f"*Position #{pos_id}* - {signal_type} {pl_emoji}\n"
                msg += f"Entry: ${entry_price:.2f}\n"
                msg += f"Current: ${current_price:.2f}\n"
                msg += f"P/L: ${unrealized_pl:.2f}\n\n"
                
                msg += f"*Take Profit:* ${take_profit:.2f}\n"
                
                if sl_count > 0:
                    msg += f"*Original SL:* ${original_sl:.2f}\n"
                    msg += f"*Current SL:* ${current_sl:.2f} ✅\n"
                    msg += f"*SL Adjusted:* {sl_count}x\n"
                else:
                    msg += f"*Stop Loss:* ${current_sl:.2f}\n"
                
                if max_profit > 0:
                    msg += f"*Max Profit:* ${max_profit:.2f}\n"
                    if unrealized_pl >= self.config.TRAILING_STOP_PROFIT_THRESHOLD:
                        msg += f"*Trailing Stop:* Active 💎\n"
                
                if position_db.last_price_update:
                    jakarta_tz = pytz.timezone('Asia/Jakarta')
                    last_update = position_db.last_price_update.replace(tzinfo=pytz.UTC).astimezone(jakarta_tz)
                    msg += f"Last Update: {last_update.strftime('%H:%M:%S')}\n"
                
                msg += "\n"
            
            session.close()
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error fetching position status: {e}")
            await update.message.reply_text("❌ Error mengambil status posisi.")
    
    async def getsignal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        user_id = update.effective_user.id
        
        try:
            if self.position_tracker and self.position_tracker.has_active_position(user_id):
                await update.message.reply_text(
                    "⏳ *Tidak Dapat Membuat Sinyal Baru*\n\n"
                    "Saat ini Anda memiliki posisi aktif yang sedang berjalan.\n"
                    "Bot akan tracking hingga TP/SL tercapai.\n\n"
                    "Tunggu hasil posisi Anda saat ini sebelum request sinyal baru.",
                    parse_mode='Markdown'
                )
                return
            
            can_trade, rejection_reason = self.risk_manager.can_trade(user_id, 'ANY')
            
            if not can_trade:
                await update.message.reply_text(
                    f"⛔ *Tidak Bisa Trading*\n\n{rejection_reason}",
                    parse_mode='Markdown'
                )
                return
            
            df_m1 = await self.market_data.get_historical_data('M1', 100)
            
            if df_m1 is None or len(df_m1) < 30:
                await update.message.reply_text(
                    "⚠️ *Data Tidak Cukup*\n\n"
                    "Belum cukup data candle untuk analisis.\n"
                    f"Candles: {len(df_m1) if df_m1 is not None else 0}/30\n\n"
                    "Tunggu beberapa saat dan coba lagi.",
                    parse_mode='Markdown'
                )
                return
            
            from bot.indicators import IndicatorEngine
            indicator_engine = IndicatorEngine(self.config)
            indicators = indicator_engine.get_indicators(df_m1)
            
            if not indicators:
                await update.message.reply_text(
                    "⚠️ *Analisis Gagal*\n\n"
                    "Tidak dapat menghitung indikator.\n"
                    "Coba lagi nanti.",
                    parse_mode='Markdown'
                )
                return
            
            signal = self.strategy.detect_signal(indicators, 'M1', signal_source='manual')
            
            if not signal:
                trend_strength = indicators.get('trend_strength', 'UNKNOWN')
                current_price = await self.market_data.get_current_price()
                
                msg = (
                    "⚠️ *Tidak Ada Sinyal*\n\n"
                    "Kondisi market saat ini tidak memenuhi kriteria trading.\n\n"
                    f"*Market Info:*\n"
                    f"Price: ${current_price:.2f}\n"
                    f"Trend: {trend_strength}\n\n"
                    "Gunakan /monitor untuk auto-detect sinyal."
                )
                await update.message.reply_text(msg, parse_mode='Markdown')
                return
            
            current_price = await self.market_data.get_current_price()
            spread_value = await self.market_data.get_spread()
            spread = spread_value if spread_value else 0.5
            
            is_valid, validation_msg = self.strategy.validate_signal(signal, spread)
            
            if not is_valid:
                await update.message.reply_text(
                    f"⚠️ *Sinyal Tidak Valid*\n\n{validation_msg}",
                    parse_mode='Markdown'
                )
                return
            
            await self._send_signal(user_id, update.effective_chat.id, signal, df_m1)
            self.risk_manager.record_signal(user_id)
            
            if self.user_manager:
                self.user_manager.update_user_activity(user_id)
            
        except Exception as e:
            logger.error(f"Error generating manual signal: {e}")
            await update.message.reply_text("❌ Error membuat sinyal. Coba lagi nanti.")
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_authorized(update.effective_user.id):
            return
        
        msg = (
            "⚙️ *Bot Configuration*\n\n"
            f"*Mode:* {'DRY RUN' if self.config.DRY_RUN else 'LIVE'}\n"
            f"*Lot Size:* {self.config.LOT_SIZE:.2f}\n"
            f"*Fixed Risk:* ${self.config.FIXED_RISK_AMOUNT:.2f}\n"
            f"*Daily Loss Limit:* {self.config.DAILY_LOSS_PERCENT}%\n"
            f"*Signal Cooldown:* {self.config.SIGNAL_COOLDOWN_SECONDS}s\n"
            f"*Trailing Stop Threshold:* ${self.config.TRAILING_STOP_PROFIT_THRESHOLD:.2f}\n"
            f"*Breakeven Threshold:* ${self.config.BREAKEVEN_PROFIT_THRESHOLD:.2f}\n\n"
            f"*EMA Periods:* {', '.join(map(str, self.config.EMA_PERIODS))}\n"
            f"*RSI Period:* {self.config.RSI_PERIOD}\n"
            f"*ATR Period:* {self.config.ATR_PERIOD}\n"
        )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def langganan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not self.user_manager:
            msg = "📊 *Status Langganan*\n\nUser management tidak tersedia."
            await update.message.reply_text(msg, parse_mode='Markdown')
            return
        
        user = self.user_manager.get_user(user_id)
        
        if not user:
            msg = (
                "⚠️ *User Tidak Terdaftar*\n\n"
                "Gunakan /start untuk mendaftar.\n"
            )
            await update.message.reply_text(msg, parse_mode='Markdown')
            return
        
        if user.is_admin:
            msg = (
                "👑 *Status Langganan*\n\n"
                "Tipe: ADMIN (Unlimited)\n"
                "Akses: Penuh & Permanen\n"
            )
        elif user.access_level == 'premium':
            expires_at = user.subscription_expires_at
            if expires_at:
                jakarta_tz = pytz.timezone('Asia/Jakarta')
                expires_local = expires_at.replace(tzinfo=pytz.UTC).astimezone(jakarta_tz)
                days_left = (expires_at - datetime.utcnow()).days
                
                msg = (
                    "💎 *Status Langganan*\n\n"
                    f"Tipe: PREMIUM\n"
                    f"Berakhir: {expires_local.strftime('%d/%m/%Y %H:%M')}\n"
                    f"Sisa: {days_left} hari\n"
                )
            else:
                msg = "💎 *Status Langganan*\n\nTipe: PREMIUM (Tanpa batas waktu)\n"
        else:
            msg = (
                "⛔ *Status Langganan*\n\n"
                "Tipe: FREE (Expired)\n\n"
                "Hubungi @dzeckyete untuk upgrade:\n"
                "• 1 Minggu: Rp 15.000\n"
                "• 1 Bulan: Rp 30.000\n"
            )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = (
            "💎 *Paket Premium*\n\n"
            "Dapatkan akses penuh ke XAUUSD Trading Bot:\n\n"
            "*Harga:*\n"
            "• 1 Minggu: Rp 15.000\n"
            "• 1 Bulan: Rp 30.000\n\n"
            "*Fitur Premium:*\n"
            "✅ Auto-monitoring 24/7\n"
            "✅ Sinyal trading real-time\n"
            "✅ Position tracking otomatis\n"
            "✅ Analisis multi-timeframe\n"
            "✅ Chart & statistik lengkap\n\n"
            "*Cara Berlangganan:*\n"
            "Hubungi: @dzeckyete\n"
        )
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def beli_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.premium_command(update, context)
    
    async def riset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Perintah ini hanya untuk admin.")
            return
        
        try:
            session = self.db.get_session()
            
            deleted_trades = session.query(Trade).delete()
            deleted_positions = session.query(Position).delete()
            deleted_performance = session.query(Performance).delete()
            
            session.commit()
            session.close()
            
            msg = (
                "✅ *Database Reset Berhasil*\n\n"
                f"Trades dihapus: {deleted_trades}\n"
                f"Positions dihapus: {deleted_positions}\n"
                f"Performance dihapus: {deleted_performance}\n"
            )
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            logger.info(f"Database reset by admin {mask_user_id(update.effective_user.id)}")
            
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            await update.message.reply_text("❌ Error reset database.")
    
    async def addpremium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Perintah ini hanya untuk admin.")
            return
        
        if not self.user_manager:
            await update.message.reply_text("❌ User manager tidak tersedia.")
            return
        
        if not context.args or len(context.args) < 2:
            msg = (
                "📝 *Cara Menggunakan:*\n\n"
                "/addpremium <user_id> <durasi_hari>\n\n"
                "*Contoh:*\n"
                "/addpremium 123456789 7\n"
                "/addpremium 123456789 30\n"
            )
            await update.message.reply_text(msg, parse_mode='Markdown')
            return
        
        try:
            target_user_id = int(context.args[0])
            duration_days = int(context.args[1])
            
            success = self.user_manager.grant_premium(target_user_id, duration_days)
            
            if success:
                msg = (
                    "✅ *Premium Berhasil Ditambahkan*\n\n"
                    f"User ID: {target_user_id}\n"
                    f"Durasi: {duration_days} hari\n"
                )
            else:
                msg = "❌ Gagal menambahkan premium. User mungkin belum terdaftar."
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            logger.info(f"Premium added to {target_user_id} for {duration_days} days by admin {mask_user_id(update.effective_user.id)}")
            
        except ValueError:
            await update.message.reply_text("❌ Format salah. Gunakan: /addpremium <user_id> <durasi_hari>")
        except Exception as e:
            logger.error(f"Error adding premium: {e}")
            await update.message.reply_text("❌ Error menambahkan premium.")
    
    async def initialize(self):
        if not self.config.TELEGRAM_BOT_TOKEN:
            logger.error("Telegram bot token not configured!")
            return False
        
        self.app = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
        
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("langganan", self.langganan_command))
        self.app.add_handler(CommandHandler("premium", self.premium_command))
        self.app.add_handler(CommandHandler("beli", self.beli_command))
        self.app.add_handler(CommandHandler("monitor", self.monitor_command))
        self.app.add_handler(CommandHandler("stopmonitor", self.stopmonitor_command))
        self.app.add_handler(CommandHandler("getsignal", self.getsignal_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
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
    
    async def setup_webhook(self, webhook_url: str, max_retries: int = 3):
        if not self.app:
            logger.error("Bot not initialized! Call initialize() first.")
            return False
        
        if not webhook_url or not webhook_url.strip():
            logger.error("Invalid webhook URL provided - empty or None")
            return False
        
        webhook_url = webhook_url.strip()
        
        if not (webhook_url.startswith('http://') or webhook_url.startswith('https://')):
            logger.error(f"Invalid webhook URL format: {webhook_url[:50]}... (must start with http:// or https://)")
            return False
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Setting up webhook (attempt {attempt}/{max_retries}): {webhook_url}")
                
                await self.app.bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=['message', 'callback_query', 'edited_message'],
                    drop_pending_updates=True
                )
                
                webhook_info = await self.app.bot.get_webhook_info()
                
                if webhook_info.url == webhook_url:
                    logger.info(f"✅ Webhook configured successfully!")
                    logger.info(f"Webhook URL: {webhook_info.url}")
                    logger.info(f"Pending updates: {webhook_info.pending_update_count}")
                    return True
                else:
                    logger.warning(f"Webhook URL mismatch - Expected: {webhook_url}, Got: {webhook_info.url}")
                    if attempt < max_retries:
                        logger.info(f"Retrying in {attempt * 2} seconds...")
                        await asyncio.sleep(attempt * 2)
                        continue
                    return False
                    
            except Exception as e:
                error_type = type(e).__name__
                logger.error(f"Failed to setup webhook (attempt {attempt}/{max_retries}): [{error_type}] {e}")
                
                if self.error_handler:
                    self.error_handler.log_exception(e, f"setup_webhook_attempt_{attempt}")
                
                if attempt < max_retries:
                    wait_time = attempt * 2
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("❌ All webhook setup attempts failed!")
                    logger.error("Please check:")
                    logger.error("  1. Webhook URL is publicly accessible")
                    logger.error("  2. SSL certificate is valid (for HTTPS)")
                    logger.error("  3. Telegram Bot API can reach your server")
                    logger.error("  4. No firewall blocking incoming connections")
                    return False
        
        return False
    
    async def run_webhook(self):
        if not self.app:
            logger.error("Bot not initialized! Call initialize() first.")
            return
        
        logger.info("Telegram bot running in webhook mode...")
        logger.info("Bot is ready to receive webhook updates")
    
    async def process_update(self, update_data):
        if not self.app:
            logger.error("Bot not initialized! Cannot process update.")
            return
        
        if not update_data:
            logger.error("Received empty update data")
            return
        
        try:
            from telegram import Update
            import json
            
            if isinstance(update_data, Update):
                update = update_data
                logger.debug(f"Received native telegram.Update object: {update.update_id}")
            else:
                parsed_data = update_data
                
                if isinstance(update_data, str):
                    try:
                        parsed_data = json.loads(update_data)
                        logger.debug("Parsed webhook update from JSON string")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON string update: {e}")
                        return
                elif hasattr(update_data, 'to_dict') and callable(update_data.to_dict):
                    try:
                        parsed_data = update_data.to_dict()
                        logger.debug(f"Converted update data via to_dict(): {type(update_data)}")
                    except Exception as e:
                        logger.warning(f"Failed to convert via to_dict: {e}")
                elif not hasattr(update_data, '__getitem__'):
                    logger.warning(f"Update data is not dict-like: {type(update_data)}")
                    logger.debug(f"Attempting to use as-is: {str(update_data)[:200]}")
                
                update = Update.de_json(parsed_data, self.app.bot)
            
            if update:
                update_id = update.update_id
                logger.debug(f"Processing webhook update: {update_id}")
                
                await self.app.process_update(update)
                
                logger.debug(f"✅ Successfully processed update: {update_id}")
            else:
                logger.warning("Received invalid or malformed update data")
                from collections.abc import Mapping
                if isinstance(parsed_data, Mapping):
                    logger.debug(f"Update data keys: {list(parsed_data.keys())}")
                
        except ValueError as e:
            logger.error(f"ValueError parsing update data: {e}")
            logger.debug(f"Problematic update data: {str(update_data)[:200]}...")
        except AttributeError as e:
            logger.error(f"AttributeError processing update: {e}")
            if self.error_handler:
                self.error_handler.log_exception(e, "process_webhook_update_attribute")
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Unexpected error processing webhook update: [{error_type}] {e}")
            if self.error_handler:
                self.error_handler.log_exception(e, "process_webhook_update")
            
            if hasattr(e, '__traceback__'):
                import traceback
                tb_str = ''.join(traceback.format_tb(e.__traceback__)[:3])
                logger.debug(f"Traceback: {tb_str}")
    
    async def run(self):
        if not self.app:
            logger.error("Bot not initialized! Call initialize() first.")
            return
        
        if self.config.TELEGRAM_WEBHOOK_MODE:
            if not self.config.WEBHOOK_URL:
                logger.error("WEBHOOK_URL not configured! Cannot use webhook mode.")
                logger.error("Please set WEBHOOK_URL environment variable or disable webhook mode.")
                return
            
            webhook_set = await self.setup_webhook(self.config.WEBHOOK_URL)
            if not webhook_set:
                logger.error("Failed to setup webhook! Bot cannot start in webhook mode.")
                return
            
            await self.run_webhook()
        else:
            logger.info("Starting Telegram bot polling...")
            await self.app.updater.start_polling()
            logger.info("Telegram bot is running!")
    
    async def stop(self):
        logger.info("=" * 50)
        logger.info("STOPPING TELEGRAM BOT")
        logger.info("=" * 50)
        
        if not self.app:
            logger.warning("Bot app not initialized, nothing to stop")
            return
        
        self.monitoring = False
        
        logger.info(f"Cancelling {len(self.monitoring_tasks)} monitoring tasks...")
        for task in self.monitoring_tasks:
            if not task.done():
                task.cancel()
        
        if self.monitoring_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.monitoring_tasks, return_exceptions=True),
                    timeout=5
                )
                logger.info("All monitoring tasks cancelled")
            except asyncio.TimeoutError:
                logger.warning("Some monitoring tasks did not complete within timeout")
        
        self.monitoring_tasks.clear()
        self.monitoring_chats.clear()
        
        if self.config.TELEGRAM_WEBHOOK_MODE:
            logger.info("Deleting Telegram webhook...")
            try:
                await asyncio.wait_for(
                    self.app.bot.delete_webhook(drop_pending_updates=True),
                    timeout=5
                )
                logger.info("✅ Webhook deleted successfully")
            except asyncio.TimeoutError:
                logger.warning("Webhook deletion timed out after 5s")
            except Exception as e:
                logger.error(f"Error deleting webhook: {e}")
        else:
            logger.info("Stopping Telegram bot polling...")
            try:
                if self.app.updater and self.app.updater.running:
                    await asyncio.wait_for(
                        self.app.updater.stop(),
                        timeout=5
                    )
                    logger.info("✅ Telegram bot polling stopped")
            except asyncio.TimeoutError:
                logger.warning("Updater stop timed out after 5s")
            except Exception as e:
                logger.error(f"Error stopping updater: {e}")
        
        logger.info("Stopping Telegram application...")
        try:
            await asyncio.wait_for(self.app.stop(), timeout=5)
            logger.info("✅ Telegram application stopped")
        except asyncio.TimeoutError:
            logger.warning("App stop timed out after 5s")
        except Exception as e:
            logger.error(f"Error stopping app: {e}")
        
        logger.info("Shutting down Telegram application...")
        try:
            await asyncio.wait_for(self.app.shutdown(), timeout=5)
            logger.info("✅ Telegram application shutdown complete")
        except asyncio.TimeoutError:
            logger.warning("App shutdown timed out after 5s")
        except Exception as e:
            logger.error(f"Error shutting down app: {e}")
        
        logger.info("=" * 50)
        logger.info("TELEGRAM BOT STOPPED")
        logger.info("=" * 50)
