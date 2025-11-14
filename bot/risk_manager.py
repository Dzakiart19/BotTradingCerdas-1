from datetime import datetime, timedelta
from typing import Optional
import pytz
from bot.logger import setup_logger

logger = setup_logger('RiskManager')

class RiskManager:
    def __init__(self, config, db_manager):
        self.config = config
        self.db = db_manager
        self.last_signal_time = None
        self.daily_stats = {}
        
    def can_trade(self, signal_type: str) -> tuple[bool, Optional[str]]:
        utc_now = datetime.now(pytz.UTC)
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        jakarta_time = utc_now.astimezone(jakarta_tz)
        today_str = jakarta_time.strftime('%Y-%m-%d')
        
        if self.last_signal_time:
            time_since_last = (utc_now - self.last_signal_time).total_seconds()
            if time_since_last < self.config.SIGNAL_COOLDOWN_SECONDS:
                remaining = self.config.SIGNAL_COOLDOWN_SECONDS - time_since_last
                return False, f"Cooldown aktif. Tunggu {int(remaining)} detik lagi"
        
        session = self.db.get_session()
        try:
            from bot.database import Trade
            
            today_start = jakarta_time.replace(hour=0, minute=0, second=0, microsecond=0)
            today_start_utc = today_start.astimezone(pytz.UTC)
            
            trades_today = session.query(Trade).filter(
                Trade.signal_time >= today_start_utc
            ).count()
            
            if trades_today >= self.config.MAX_TRADES_PER_DAY:
                return False, f"Batas maksimal {self.config.MAX_TRADES_PER_DAY} trade per hari tercapai"
            
            daily_pl = session.query(Trade).filter(
                Trade.signal_time >= today_start_utc,
                Trade.actual_pl.isnot(None)
            ).with_entities(Trade.actual_pl).all()
            
            total_daily_pl = sum([pl[0] for pl in daily_pl if pl[0] is not None])
            
            if total_daily_pl < 0:
                loss_percent = abs(total_daily_pl)
                if loss_percent >= self.config.DAILY_LOSS_PERCENT:
                    return False, f"Batas kerugian harian {self.config.DAILY_LOSS_PERCENT}% tercapai"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking trade eligibility: {e}")
            return False, f"Error: {str(e)}"
        finally:
            session.close()
    
    def record_signal(self):
        self.last_signal_time = datetime.now(pytz.UTC)
        logger.info("Signal recorded, cooldown timer started")
    
    def calculate_position_size(self, account_balance: float, entry_price: float, 
                               stop_loss: float, signal_type: str) -> float:
        risk_amount = account_balance * (self.config.RISK_PER_TRADE_PERCENT / 100)
        
        pips_at_risk = abs(entry_price - stop_loss) * self.config.XAUUSD_PIP_VALUE
        
        if pips_at_risk > 0:
            lot_size = risk_amount / pips_at_risk
        else:
            lot_size = self.config.LOT_SIZE
        
        lot_size = max(0.01, min(lot_size, 1.0))
        
        logger.info(f"Calculated position size: {lot_size} lots (Risk: ${risk_amount:.2f})")
        return lot_size
    
    def calculate_pl(self, entry_price: float, exit_price: float, 
                    signal_type: str, lot_size: Optional[float] = None) -> float:
        if lot_size is None:
            lot_size = self.config.LOT_SIZE
        
        if signal_type == 'BUY':
            price_diff = exit_price - entry_price
        else:
            price_diff = entry_price - exit_price
        
        pips = price_diff * self.config.XAUUSD_PIP_VALUE
        pl = pips * lot_size
        
        return pl
