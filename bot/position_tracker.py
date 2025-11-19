import asyncio
from datetime import datetime
from typing import Dict, Optional
import pytz
from bot.logger import setup_logger
from bot.database import Position, Trade

logger = setup_logger('PositionTracker')

class PositionTracker:
    def __init__(self, config, db_manager, risk_manager, alert_system=None, user_manager=None, 
                 chart_generator=None, market_data=None, telegram_app=None):
        self.config = config
        self.db = db_manager
        self.risk_manager = risk_manager
        self.alert_system = alert_system
        self.user_manager = user_manager
        self.chart_generator = chart_generator
        self.market_data = market_data
        self.telegram_app = telegram_app
        self.active_positions = {}
        self.monitoring = False
    
    def _normalize_position_dict(self, pos: Dict) -> Dict:
        """Ensure all required keys exist in position dict with safe defaults"""
        if 'original_sl' not in pos or pos['original_sl'] is None:
            pos['original_sl'] = pos.get('stop_loss', 0.0)
        if 'sl_adjustment_count' not in pos or pos['sl_adjustment_count'] is None:
            pos['sl_adjustment_count'] = 0
        if 'max_profit_reached' not in pos or pos['max_profit_reached'] is None:
            pos['max_profit_reached'] = 0.0
        if 'last_price_update' not in pos:
            pos['last_price_update'] = datetime.now(pytz.UTC)
        return pos
        
    async def add_position(self, user_id: int, trade_id: int, signal_type: str, entry_price: float,
                          stop_loss: float, take_profit: float):
        session = self.db.get_session()
        try:
            position = Position(
                user_id=user_id,
                trade_id=trade_id,
                ticker='XAUUSD',
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                current_price=entry_price,
                unrealized_pl=0.0,
                status='ACTIVE',
                original_sl=stop_loss,
                sl_adjustment_count=0,
                max_profit_reached=0.0,
                last_price_update=datetime.now(pytz.UTC)
            )
            session.add(position)
            session.commit()
            
            if user_id not in self.active_positions:
                self.active_positions[user_id] = {}
            
            self.active_positions[user_id][position.id] = {
                'trade_id': trade_id,
                'signal_type': signal_type,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'original_sl': stop_loss,
                'sl_adjustment_count': 0,
                'max_profit_reached': 0.0
            }
            
            logger.info(f"Position added - User:{user_id} ID:{position.id} {signal_type} @${entry_price:.2f}")
            return position.id
            
        except Exception as e:
            logger.error(f"Error adding position: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    async def apply_dynamic_sl(self, user_id: int, position_id: int, current_price: float, unrealized_pl: float) -> tuple[bool, Optional[float]]:
        """Apply dynamic SL tightening when loss >= threshold
        
        Returns:
            tuple[bool, Optional[float]]: (sl_adjusted, new_stop_loss)
        """
        if user_id not in self.active_positions or position_id not in self.active_positions[user_id]:
            return False, None
        
        pos = self._normalize_position_dict(self.active_positions[user_id][position_id])
        signal_type = pos['signal_type']
        entry_price = pos['entry_price']
        stop_loss = pos['stop_loss']
        original_sl = pos.get('original_sl')
        
        if original_sl is None:
            original_sl = stop_loss
            pos['original_sl'] = stop_loss
            logger.warning(f"original_sl was None for position {position_id}, using current stop_loss")
        
        if unrealized_pl >= 0 or abs(unrealized_pl) < self.config.DYNAMIC_SL_LOSS_THRESHOLD:
            return False, None
        
        original_sl_distance = abs(entry_price - original_sl)
        new_sl_distance = original_sl_distance * self.config.DYNAMIC_SL_TIGHTENING_MULTIPLIER
        
        new_stop_loss = None
        sl_adjusted = False
        
        if signal_type == 'BUY':
            new_stop_loss = entry_price - new_sl_distance
            if new_stop_loss > stop_loss:
                pos['stop_loss'] = new_stop_loss
                pos['sl_adjustment_count'] = pos.get('sl_adjustment_count', 0) + 1
                sl_adjusted = True
                logger.info(f"🛡️ Dynamic SL activated! Loss ${abs(unrealized_pl):.2f} >= ${self.config.DYNAMIC_SL_LOSS_THRESHOLD}. SL tightened from ${stop_loss:.2f} → ${new_stop_loss:.2f} (protect capital)")
                
                if self.telegram_app:
                    try:
                        msg = (
                            f"🛡️ *Dynamic SL Activated*\n\n"
                            f"Position ID: {position_id}\n"
                            f"Type: {signal_type}\n"
                            f"Current Loss: ${abs(unrealized_pl):.2f}\n"
                            f"SL Updated: ${stop_loss:.2f} → ${new_stop_loss:.2f}\n"
                            f"Protection: Capital preservation mode"
                        )
                        await self.telegram_app.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Failed to send dynamic SL notification: {e}")
        else:
            new_stop_loss = entry_price + new_sl_distance
            if new_stop_loss < stop_loss:
                pos['stop_loss'] = new_stop_loss
                pos['sl_adjustment_count'] = pos.get('sl_adjustment_count', 0) + 1
                sl_adjusted = True
                logger.info(f"🛡️ Dynamic SL activated! Loss ${abs(unrealized_pl):.2f} >= ${self.config.DYNAMIC_SL_LOSS_THRESHOLD}. SL tightened from ${stop_loss:.2f} → ${new_stop_loss:.2f} (protect capital)")
                
                if self.telegram_app:
                    try:
                        msg = (
                            f"🛡️ *Dynamic SL Activated*\n\n"
                            f"Position ID: {position_id}\n"
                            f"Type: {signal_type}\n"
                            f"Current Loss: ${abs(unrealized_pl):.2f}\n"
                            f"SL Updated: ${stop_loss:.2f} → ${new_stop_loss:.2f}\n"
                            f"Protection: Capital preservation mode"
                        )
                        await self.telegram_app.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Failed to send dynamic SL notification: {e}")
        
        return sl_adjusted, new_stop_loss if sl_adjusted else None
    
    async def apply_trailing_stop(self, user_id: int, position_id: int, current_price: float, unrealized_pl: float) -> tuple[bool, Optional[float]]:
        """Apply trailing stop when profit >= threshold
        
        Returns:
            tuple[bool, Optional[float]]: (sl_adjusted, new_stop_loss)
        """
        if user_id not in self.active_positions or position_id not in self.active_positions[user_id]:
            return False, None
        
        pos = self._normalize_position_dict(self.active_positions[user_id][position_id])
        signal_type = pos['signal_type']
        stop_loss = pos['stop_loss']
        
        if unrealized_pl <= 0 or unrealized_pl < self.config.TRAILING_STOP_PROFIT_THRESHOLD:
            return False, None
        
        max_profit = pos.get('max_profit_reached', 0.0)
        if max_profit is None:
            max_profit = 0.0
        
        if unrealized_pl > max_profit:
            pos['max_profit_reached'] = unrealized_pl
        
        trailing_distance = self.config.TRAILING_STOP_DISTANCE_PIPS / self.config.XAUUSD_PIP_VALUE
        
        new_trailing_sl = None
        sl_adjusted = False
        
        if signal_type == 'BUY':
            new_trailing_sl = current_price - trailing_distance
            if new_trailing_sl > stop_loss:
                pos['stop_loss'] = new_trailing_sl
                pos['sl_adjustment_count'] = pos.get('sl_adjustment_count', 0) + 1
                sl_adjusted = True
                logger.info(f"💎 Trailing stop activated! Profit ${unrealized_pl:.2f}. SL moved to ${new_trailing_sl:.2f} (lock-in profit)")
                
                if self.telegram_app:
                    try:
                        msg = (
                            f"💎 *Trailing Stop Active*\n\n"
                            f"Position ID: {position_id}\n"
                            f"Type: {signal_type}\n"
                            f"Current Profit: ${unrealized_pl:.2f}\n"
                            f"Max Profit: ${pos['max_profit_reached']:.2f}\n"
                            f"SL Updated: ${stop_loss:.2f} → ${new_trailing_sl:.2f}\n"
                            f"Status: Profit locked-in!"
                        )
                        await self.telegram_app.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Failed to send trailing stop notification: {e}")
        else:
            new_trailing_sl = current_price + trailing_distance
            if new_trailing_sl < stop_loss:
                pos['stop_loss'] = new_trailing_sl
                pos['sl_adjustment_count'] = pos.get('sl_adjustment_count', 0) + 1
                sl_adjusted = True
                logger.info(f"💎 Trailing stop activated! Profit ${unrealized_pl:.2f}. SL moved to ${new_trailing_sl:.2f} (lock-in profit)")
                
                if self.telegram_app:
                    try:
                        msg = (
                            f"💎 *Trailing Stop Active*\n\n"
                            f"Position ID: {position_id}\n"
                            f"Type: {signal_type}\n"
                            f"Current Profit: ${unrealized_pl:.2f}\n"
                            f"Max Profit: ${pos['max_profit_reached']:.2f}\n"
                            f"SL Updated: ${stop_loss:.2f} → ${new_trailing_sl:.2f}\n"
                            f"Status: Profit locked-in!"
                        )
                        await self.telegram_app.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Failed to send trailing stop notification: {e}")
        
        return sl_adjusted, new_trailing_sl if sl_adjusted else None
    
    async def update_position(self, user_id: int, position_id: int, current_price: float) -> Optional[str]:
        """Update position with current price and apply dynamic SL/TP logic"""
        if user_id not in self.active_positions or position_id not in self.active_positions[user_id]:
            return None
        
        pos = self.active_positions[user_id][position_id]
        signal_type = pos['signal_type']
        entry_price = pos['entry_price']
        stop_loss = pos['stop_loss']
        take_profit = pos['take_profit']
        
        unrealized_pl = self.risk_manager.calculate_pl(entry_price, current_price, signal_type)
        
        sl_adjusted = False
        
        dynamic_sl_applied, new_sl = await self.apply_dynamic_sl(user_id, position_id, current_price, unrealized_pl)
        if dynamic_sl_applied:
            sl_adjusted = True
            stop_loss = new_sl
        
        if not dynamic_sl_applied:
            trailing_applied, new_sl = await self.apply_trailing_stop(user_id, position_id, current_price, unrealized_pl)
            if trailing_applied:
                sl_adjusted = True
                stop_loss = new_sl
        
        stop_loss = pos['stop_loss']
        
        session = self.db.get_session()
        try:
            position = session.query(Position).filter(Position.id == position_id, Position.user_id == user_id).first()
            if position:
                position.current_price = current_price
                position.unrealized_pl = unrealized_pl
                position.last_price_update = datetime.now(pytz.UTC)
                
                current_max_profit = position.max_profit_reached if position.max_profit_reached is not None else 0.0
                if unrealized_pl > 0 and unrealized_pl > current_max_profit:
                    position.max_profit_reached = unrealized_pl
                
                if sl_adjusted:
                    position.stop_loss = stop_loss
                    position.sl_adjustment_count = pos['sl_adjustment_count']
                
                session.commit()
        except Exception as e:
            logger.error(f"Error updating position {position_id}: {e}")
            session.rollback()
        finally:
            session.close()
        
        hit_tp = False
        hit_sl = False
        
        if signal_type == 'BUY':
            hit_tp = current_price >= take_profit
            hit_sl = current_price <= stop_loss
        else:
            hit_tp = current_price <= take_profit
            hit_sl = current_price >= stop_loss
        
        if hit_tp:
            await self.close_position(user_id, position_id, current_price, 'TP_HIT')
            return 'TP_HIT'
        elif hit_sl:
            reason = 'DYNAMIC_SL_HIT' if sl_adjusted else 'SL_HIT'
            await self.close_position(user_id, position_id, current_price, reason)
            return reason
        
        return None
    
    async def close_position(self, user_id: int, position_id: int, exit_price: float, reason: str):
        if user_id not in self.active_positions or position_id not in self.active_positions[user_id]:
            return
        
        pos = self.active_positions[user_id][position_id]
        trade_id = pos['trade_id']
        signal_type = pos['signal_type']
        entry_price = pos['entry_price']
        
        actual_pl = self.risk_manager.calculate_pl(entry_price, exit_price, signal_type)
        
        session = self.db.get_session()
        try:
            position = session.query(Position).filter(Position.id == position_id, Position.user_id == user_id).first()
            if position:
                position.status = 'CLOSED'
                position.current_price = exit_price
                position.unrealized_pl = actual_pl
                position.closed_at = datetime.now(pytz.UTC)
                
            trade = session.query(Trade).filter(Trade.id == trade_id, Trade.user_id == user_id).first()
            if trade:
                trade.status = 'CLOSED'
                trade.exit_price = exit_price
                trade.actual_pl = actual_pl
                trade.close_time = datetime.now(pytz.UTC)
                trade.result = 'WIN' if actual_pl > 0 else 'LOSS'
                
            session.commit()
            
            logger.info(f"Position closed - User:{user_id} ID:{position_id} {reason} P/L:${actual_pl:.2f}")
            
            if self.telegram_app and self.chart_generator and self.market_data:
                try:
                    df_m1 = await self.market_data.get_historical_data('M1', 100)
                    
                    if df_m1 is not None and len(df_m1) >= 30:
                        exit_signal = {
                            'signal': signal_type,
                            'entry_price': entry_price,
                            'stop_loss': pos['stop_loss'],
                            'take_profit': pos['take_profit'],
                            'timeframe': 'M1'
                        }
                        
                        chart_path = await self.chart_generator.generate_chart_async(df_m1, exit_signal, 'M1')
                        
                        result_emoji = '✅' if trade.result == 'WIN' else '❌'
                        exit_label = "TRADE_EXIT" if reason == "TP_HIT" else "Trade LOSS"
                        
                        exit_msg = (
                            f"{result_emoji} *{exit_label}*\n\n"
                            f"Type: {signal_type}\n"
                            f"Entry: ${entry_price:.2f}\n"
                            f"Exit: ${exit_price:.2f}\n"
                            f"P/L: ${actual_pl:.2f}"
                        )
                        
                        try:
                            await self.telegram_app.bot.send_message(
                                chat_id=user_id,
                                text=exit_msg,
                                parse_mode='Markdown'
                            )
                            
                            if chart_path:
                                with open(chart_path, 'rb') as photo:
                                    await self.telegram_app.bot.send_photo(
                                        chat_id=user_id, 
                                        photo=photo,
                                        caption=f"Chart Exit - {signal_type} @ ${exit_price:.2f}"
                                    )
                                
                                if self.config.CHART_AUTO_DELETE:
                                    await asyncio.sleep(2)
                                    self.chart_generator.delete_chart(chart_path)
                                    logger.info(f"Auto-deleted exit chart: {chart_path}")
                        except Exception as e:
                            logger.error(f"Failed to send exit notification to user {user_id}: {e}")
                    else:
                        logger.warning(f"Not enough candles for exit chart: {len(df_m1) if df_m1 else 0}")
                        
                        if self.alert_system and trade:
                            await self.alert_system.send_trade_exit_alert({
                                'signal_type': signal_type,
                                'entry_price': entry_price,
                                'exit_price': exit_price,
                                'actual_pl': actual_pl
                            }, trade.result)
                except Exception as e:
                    logger.error(f"Error sending exit chart: {e}")
                    
                    if self.alert_system and trade:
                        await self.alert_system.send_trade_exit_alert({
                            'signal_type': signal_type,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'actual_pl': actual_pl
                        }, trade.result)
            elif self.alert_system and trade:
                await self.alert_system.send_trade_exit_alert({
                    'signal_type': signal_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'actual_pl': actual_pl
                }, trade.result)
            
            if self.user_manager and trade:
                self.user_manager.update_user_stats(user_id, actual_pl)
            
            del self.active_positions[user_id][position_id]
            if not self.active_positions[user_id]:
                del self.active_positions[user_id]
            
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def monitor_active_positions(self):
        """Monitor all active positions and apply dynamic SL/TP
        
        This method is called by the scheduler every 10 seconds.
        Returns a list of updated positions.
        """
        if not self.active_positions:
            return []
        
        if not self.market_data:
            logger.warning("Market data not available for position monitoring")
            return []
        
        updated_positions = []
        
        try:
            current_price = await self.market_data.get_current_price()
            
            if not current_price:
                logger.warning("No current price available for position monitoring")
                return []
            
            for user_id in list(self.active_positions.keys()):
                for position_id in list(self.active_positions[user_id].keys()):
                    try:
                        result = await self.update_position(user_id, position_id, current_price)
                        if result:
                            updated_positions.append({
                                'user_id': user_id,
                                'position_id': position_id,
                                'result': result,
                                'price': current_price
                            })
                            logger.info(f"Position {position_id} User:{user_id} closed: {result} at ${current_price:.2f}")
                    except Exception as e:
                        logger.error(f"Error monitoring position {position_id} for user {user_id}: {e}")
            
            return updated_positions
            
        except Exception as e:
            logger.error(f"Error in monitor_active_positions: {e}")
            return []
    
    async def monitor_positions(self, market_data_client):
        tick_queue = await market_data_client.subscribe_ticks('position_tracker')
        logger.info("Position tracker monitoring started")
        
        self.monitoring = True
        
        try:
            while self.monitoring:
                try:
                    tick = await tick_queue.get()
                    
                    if self.active_positions:
                        mid_price = tick['quote']
                        
                        for user_id in list(self.active_positions.keys()):
                            for position_id in list(self.active_positions[user_id].keys()):
                                result = await self.update_position(user_id, position_id, mid_price)
                                if result:
                                    logger.info(f"Position {position_id} User:{user_id} closed: {result}")
                    
                except Exception as e:
                    logger.error(f"Error processing tick dalam position monitoring: {e}")
                    await asyncio.sleep(1)
                    
        finally:
            await market_data_client.unsubscribe_ticks('position_tracker')
            logger.info("Position tracker monitoring stopped")
    
    def stop_monitoring(self):
        self.monitoring = False
        logger.info("Position monitoring stopped")
    
    def get_active_positions(self, user_id: Optional[int] = None) -> Dict:
        if user_id is not None:
            return self.active_positions.get(user_id, {}).copy()
        return self.active_positions.copy()
    
    def has_active_position(self, user_id: int) -> bool:
        return user_id in self.active_positions and len(self.active_positions[user_id]) > 0
    
    def get_active_position_count(self, user_id: Optional[int] = None) -> int:
        if user_id is not None:
            return len(self.active_positions.get(user_id, {}))
        return sum(len(positions) for positions in self.active_positions.values())
