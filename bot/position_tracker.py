import asyncio
from datetime import datetime
from typing import Dict, Optional
import pytz
from bot.logger import setup_logger
from bot.database import Position, Trade

logger = setup_logger('PositionTracker')

class PositionTracker:
    def __init__(self, config, db_manager, risk_manager, alert_system=None, user_manager=None):
        self.config = config
        self.db = db_manager
        self.risk_manager = risk_manager
        self.alert_system = alert_system
        self.user_manager = user_manager
        self.active_positions = {}
        self.monitoring = False
        
    async def add_position(self, trade_id: int, signal_type: str, entry_price: float,
                          stop_loss: float, take_profit: float):
        session = self.db.get_session()
        try:
            position = Position(
                trade_id=trade_id,
                ticker='XAUUSD',
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                current_price=entry_price,
                unrealized_pl=0.0,
                status='ACTIVE'
            )
            session.add(position)
            session.commit()
            
            self.active_positions[position.id] = {
                'trade_id': trade_id,
                'signal_type': signal_type,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            
            logger.info(f"Position added: ID={position.id}, Type={signal_type}, Entry={entry_price}")
            return position.id
            
        except Exception as e:
            logger.error(f"Error adding position: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    async def update_position(self, position_id: int, current_price: float) -> Optional[str]:
        if position_id not in self.active_positions:
            return None
        
        pos = self.active_positions[position_id]
        signal_type = pos['signal_type']
        entry_price = pos['entry_price']
        stop_loss = pos['stop_loss']
        take_profit = pos['take_profit']
        
        unrealized_pl = self.risk_manager.calculate_pl(entry_price, current_price, signal_type)
        
        session = self.db.get_session()
        try:
            position = session.query(Position).filter(Position.id == position_id).first()
            if position:
                position.current_price = current_price
                position.unrealized_pl = unrealized_pl
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
            await self.close_position(position_id, current_price, 'TP_HIT')
            return 'TP_HIT'
        elif hit_sl:
            await self.close_position(position_id, current_price, 'SL_HIT')
            return 'SL_HIT'
        
        return None
    
    async def close_position(self, position_id: int, exit_price: float, reason: str):
        if position_id not in self.active_positions:
            return
        
        pos = self.active_positions[position_id]
        trade_id = pos['trade_id']
        signal_type = pos['signal_type']
        entry_price = pos['entry_price']
        
        actual_pl = self.risk_manager.calculate_pl(entry_price, exit_price, signal_type)
        
        session = self.db.get_session()
        try:
            position = session.query(Position).filter(Position.id == position_id).first()
            if position:
                position.status = 'CLOSED'
                position.current_price = exit_price
                position.unrealized_pl = actual_pl
                position.closed_at = datetime.now(pytz.UTC)
                
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.status = 'CLOSED'
                trade.exit_price = exit_price
                trade.actual_pl = actual_pl
                trade.close_time = datetime.now(pytz.UTC)
                trade.result = 'WIN' if actual_pl > 0 else 'LOSS'
                
            session.commit()
            
            logger.info(f"Position closed: ID={position_id}, Reason={reason}, P/L=${actual_pl:.2f}")
            
            if self.alert_system and trade:
                await self.alert_system.send_trade_exit_alert({
                    'signal_type': signal_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'actual_pl': actual_pl
                }, trade.result)
            
            if self.user_manager and trade:
                for user_id in self.config.AUTHORIZED_USER_IDS:
                    self.user_manager.update_user_stats(user_id, actual_pl)
            
            del self.active_positions[position_id]
            
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def monitor_positions(self, market_data_client):
        tick_queue = await market_data_client.subscribe_ticks('position_tracker')
        logger.info("Position tracker subscribed ke tick feed - monitoring real-time aktif")
        
        self.monitoring = True
        
        try:
            while self.monitoring:
                try:
                    tick = await tick_queue.get()
                    
                    if self.active_positions:
                        mid_price = tick['quote']
                        
                        for position_id in list(self.active_positions.keys()):
                            result = await self.update_position(position_id, mid_price)
                            if result:
                                logger.info(f"✅ Position {position_id} ditutup: {result}")
                    
                except Exception as e:
                    logger.error(f"Error processing tick dalam position monitoring: {e}")
                    await asyncio.sleep(1)
                    
        finally:
            await market_data_client.unsubscribe_ticks('position_tracker')
            logger.info("Position tracker unsubscribed dari tick feed")
    
    def stop_monitoring(self):
        self.monitoring = False
        logger.info("Position monitoring stopped")
    
    def get_active_positions(self) -> Dict:
        return self.active_positions.copy()
    
    def has_active_position(self) -> bool:
        return len(self.active_positions) > 0
    
    def get_active_position_count(self) -> int:
        return len(self.active_positions)
