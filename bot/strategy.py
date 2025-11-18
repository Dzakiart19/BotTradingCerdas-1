from typing import Optional, Dict
import json
from bot.logger import setup_logger

logger = setup_logger('Strategy')

class TradingStrategy:
    def __init__(self, config):
        self.config = config
        
    def detect_signal(self, indicators: Dict, timeframe: str = 'M1') -> Optional[Dict]:
        if not indicators:
            return None
        
        try:
            ema_short = indicators.get(f'ema_{self.config.EMA_PERIODS[0]}')
            ema_mid = indicators.get(f'ema_{self.config.EMA_PERIODS[1]}')
            ema_long = indicators.get(f'ema_{self.config.EMA_PERIODS[2]}')
            
            rsi = indicators.get('rsi')
            rsi_prev = indicators.get('rsi_prev')
            
            stoch_k = indicators.get('stoch_k')
            stoch_d = indicators.get('stoch_d')
            stoch_k_prev = indicators.get('stoch_k_prev')
            stoch_d_prev = indicators.get('stoch_d_prev')
            
            atr = indicators.get('atr')
            close = indicators.get('close')
            volume = indicators.get('volume')
            volume_avg = indicators.get('volume_avg')
            
            if None in [ema_short, ema_mid, ema_long, rsi, stoch_k, stoch_d, atr, close]:
                logger.warning("Missing required indicators")
                return None
            
            ema_aligned_bullish = (ema_short is not None and ema_long is not None and ema_short > ema_long)
            ema_aligned_bearish = (ema_short is not None and ema_long is not None and ema_short < ema_long)
            
            rsi_bullish_signal = True
            rsi_bearish_signal = True
            
            stoch_bullish_signal = (stoch_k is not None and stoch_d is not None and stoch_k > stoch_d)
            stoch_bearish_signal = (stoch_k is not None and stoch_d is not None and stoch_k < stoch_d)
            
            high_volume = True
            
            signal = None
            confidence_reasons = []
            
            if ema_aligned_bullish:
                signal = 'BUY'
                confidence_reasons.append("EMA trend bullish (TEST MODE)")
                confidence_reasons.append("Quick test signal")
                    
            elif ema_aligned_bearish:
                signal = 'SELL'
                confidence_reasons.append("EMA trend bearish (TEST MODE)")
                confidence_reasons.append("Quick test signal")
            
            if signal:
                sl_distance = atr * self.config.SL_ATR_MULTIPLIER
                tp_distance = sl_distance * self.config.TP_RR_RATIO
                
                if signal == 'BUY':
                    stop_loss = close - sl_distance
                    take_profit = close + tp_distance
                else:
                    stop_loss = close + sl_distance
                    take_profit = close - tp_distance
                
                logger.info(f"{signal} signal detected on {timeframe}: {', '.join(confidence_reasons)}")
                
                return {
                    'signal': signal,
                    'entry_price': float(close),
                    'stop_loss': float(stop_loss),
                    'take_profit': float(take_profit),
                    'timeframe': timeframe,
                    'indicators': json.dumps({
                        'ema_short': float(ema_short) if ema_short is not None else None,
                        'ema_mid': float(ema_mid) if ema_mid is not None else None,
                        'ema_long': float(ema_long) if ema_long is not None else None,
                        'rsi': float(rsi) if rsi is not None else None,
                        'stoch_k': float(stoch_k) if stoch_k is not None else None,
                        'stoch_d': float(stoch_d) if stoch_d is not None else None,
                        'atr': float(atr) if atr is not None else None,
                        'volume': int(volume) if volume is not None else None,
                        'volume_avg': float(volume_avg) if volume_avg is not None else None
                    }),
                    'confidence_reasons': confidence_reasons
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting signal: {e}")
            return None
    
    def validate_signal(self, signal: Dict, current_spread: float = 0) -> tuple[bool, Optional[str]]:
        spread_pips = current_spread * self.config.XAUUSD_PIP_VALUE
        
        if spread_pips > self.config.MAX_SPREAD_PIPS:
            return False, f"Spread too high: {spread_pips:.2f} pips (max: {self.config.MAX_SPREAD_PIPS})"
        
        entry = signal['entry_price']
        sl = signal['stop_loss']
        tp = signal['take_profit']
        
        sl_pips = abs(entry - sl) * self.config.XAUUSD_PIP_VALUE
        tp_pips = abs(entry - tp) * self.config.XAUUSD_PIP_VALUE
        
        if sl_pips < 5:
            return False, "Stop loss too tight (< 5 pips)"
        
        if tp_pips < 10:
            return False, "Take profit too tight (< 10 pips)"
        
        return True, None
