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
            
            rsi_bullish_signal = (rsi is not None and rsi < 50)
            rsi_bearish_signal = (rsi is not None and rsi > 50)
            
            stoch_bullish_signal = (stoch_k is not None and stoch_d is not None and stoch_k > stoch_d)
            stoch_bearish_signal = (stoch_k is not None and stoch_d is not None and stoch_k < stoch_d)
            
            high_volume = volume > (volume_avg * self.config.VOLUME_THRESHOLD_MULTIPLIER)
            
            signal = None
            confidence_reasons = []
            
            if ema_aligned_bullish and (rsi_bullish_signal or stoch_bullish_signal):
                signal = 'BUY'
                confidence_reasons.append("EMA trend bullish")
                if rsi_bullish_signal:
                    confidence_reasons.append("RSI bullish zone")
                if stoch_bullish_signal:
                    confidence_reasons.append("Stochastic bullish")
                if high_volume:
                    confidence_reasons.append("High volume")
                    
            elif ema_aligned_bearish and (rsi_bearish_signal or stoch_bearish_signal):
                signal = 'SELL'
                confidence_reasons.append("EMA trend bearish")
                if rsi_bearish_signal:
                    confidence_reasons.append("RSI bearish zone")
                if stoch_bearish_signal:
                    confidence_reasons.append("Stochastic bearish")
                if high_volume:
                    confidence_reasons.append("High volume")
            
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
                    'entry_price': close,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'timeframe': timeframe,
                    'indicators': json.dumps({
                        'ema_short': ema_short,
                        'ema_mid': ema_mid,
                        'ema_long': ema_long,
                        'rsi': rsi,
                        'stoch_k': stoch_k,
                        'stoch_d': stoch_d,
                        'atr': atr,
                        'volume': volume,
                        'volume_avg': volume_avg
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
