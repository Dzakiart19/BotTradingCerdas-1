from typing import Optional, Dict
import json
from bot.logger import setup_logger

logger = setup_logger('Strategy')

class TradingStrategy:
    def __init__(self, config):
        self.config = config
    
    def calculate_trend_strength(self, indicators: Dict) -> tuple[float, str]:
        """
        Calculate trend strength dari 0.0 (weak) sampai 1.0 (very strong)
        Returns: (strength_score, description)
        """
        score = 0.0
        factors = []
        
        try:
            ema_short = indicators.get(f'ema_{self.config.EMA_PERIODS[0]}')
            ema_mid = indicators.get(f'ema_{self.config.EMA_PERIODS[1]}')
            ema_long = indicators.get(f'ema_{self.config.EMA_PERIODS[2]}')
            macd_histogram = indicators.get('macd_histogram')
            rsi = indicators.get('rsi')
            atr = indicators.get('atr')
            close = indicators.get('close')
            volume = indicators.get('volume')
            volume_avg = indicators.get('volume_avg')
            
            if (ema_short is not None and ema_mid is not None and 
                ema_long is not None and close is not None and close > 0):
                ema_separation = abs(ema_short - ema_long) / close
                if ema_separation > 0.003:
                    score += 0.25
                    factors.append("EMA spread lebar")
                elif ema_separation > 0.0015:
                    score += 0.15
                    factors.append("EMA spread medium")
            
            if macd_histogram is not None:
                macd_strength = abs(macd_histogram)
                if macd_strength > 0.5:
                    score += 0.25
                    factors.append("MACD histogram kuat")
                elif macd_strength > 0.2:
                    score += 0.15
                    factors.append("MACD histogram medium")
            
            if rsi is not None:
                rsi_momentum = abs(rsi - 50) / 50
                if rsi_momentum > 0.4:
                    score += 0.25
                    factors.append("RSI momentum tinggi")
                elif rsi_momentum > 0.2:
                    score += 0.15
                    factors.append("RSI momentum medium")
            
            if volume is not None and volume_avg is not None and volume_avg > 0:
                volume_ratio = volume / volume_avg
                if volume_ratio > 1.5:
                    score += 0.25
                    factors.append("Volume sangat tinggi")
                elif volume_ratio > 1.0:
                    score += 0.15
                    factors.append("Volume tinggi")
            
            if score >= 0.75:
                description = "SANGAT KUAT 🔥"
            elif score >= 0.5:
                description = "KUAT 💪"
            elif score >= 0.3:
                description = "MEDIUM ⚡"
            else:
                description = "LEMAH 📊"
            
            return min(score, 1.0), description
            
        except Exception as e:
            logger.error(f"Error calculating trend strength: {e}")
            return 0.3, "MEDIUM ⚡"
        
    def detect_signal(self, indicators: Dict, timeframe: str = 'M1', signal_source: str = 'auto') -> Optional[Dict]:
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
            
            macd = indicators.get('macd')
            macd_signal = indicators.get('macd_signal')
            macd_histogram = indicators.get('macd_histogram')
            macd_prev = indicators.get('macd_prev')
            macd_signal_prev = indicators.get('macd_signal_prev')
            
            atr = indicators.get('atr')
            close = indicators.get('close')
            volume = indicators.get('volume')
            volume_avg = indicators.get('volume_avg')
            
            if None in [ema_short, ema_mid, ema_long, rsi, macd, macd_signal, atr, close]:
                logger.warning("Missing required indicators")
                return None
            
            signal = None
            confidence_reasons = []
            
            ema_trend_bullish = ema_short > ema_mid > ema_long
            ema_trend_bearish = ema_short < ema_mid < ema_long
            
            ema_crossover_bullish = (ema_short is not None and ema_mid is not None and 
                                     ema_short > ema_mid and 
                                     abs(ema_short - ema_mid) / ema_mid < 0.001)
            ema_crossover_bearish = (ema_short is not None and ema_mid is not None and 
                                     ema_short < ema_mid and 
                                     abs(ema_short - ema_mid) / ema_mid < 0.001)
            
            macd_bullish_crossover = False
            macd_bearish_crossover = False
            if macd_prev is not None and macd_signal_prev is not None:
                macd_bullish_crossover = (macd_prev <= macd_signal_prev and macd > macd_signal)
                macd_bearish_crossover = (macd_prev >= macd_signal_prev and macd < macd_signal)
            
            macd_bullish = macd > macd_signal
            macd_bearish = macd < macd_signal
            macd_above_zero = macd > 0
            macd_below_zero = macd < 0
            
            rsi_oversold_crossup = False
            rsi_overbought_crossdown = False
            if rsi_prev is not None:
                rsi_oversold_crossup = (rsi_prev < self.config.RSI_OVERSOLD_LEVEL and rsi >= self.config.RSI_OVERSOLD_LEVEL)
                rsi_overbought_crossdown = (rsi_prev > self.config.RSI_OVERBOUGHT_LEVEL and rsi <= self.config.RSI_OVERBOUGHT_LEVEL)
            
            rsi_bullish = rsi is not None and rsi > 50
            rsi_bearish = rsi is not None and rsi < 50
            
            stoch_bullish = False
            stoch_bearish = False
            if stoch_k_prev is not None and stoch_d_prev is not None:
                stoch_bullish = (stoch_k_prev < stoch_d_prev and stoch_k > stoch_d and 
                                stoch_k < self.config.STOCH_OVERBOUGHT_LEVEL)
                stoch_bearish = (stoch_k_prev > stoch_d_prev and stoch_k < stoch_d and 
                                stoch_k > self.config.STOCH_OVERSOLD_LEVEL)
            
            volume_strong = True
            if volume is not None and volume_avg is not None:
                volume_strong = volume > volume_avg * self.config.VOLUME_THRESHOLD_MULTIPLIER
            
            if signal_source == 'auto':
                bullish_score = 0
                bearish_score = 0
                
                if ema_trend_bullish:
                    bullish_score += 2
                if ema_trend_bearish:
                    bearish_score += 2
                
                if macd_bullish_crossover:
                    bullish_score += 2
                elif macd_bullish:
                    bullish_score += 1
                    
                if macd_bearish_crossover:
                    bearish_score += 2
                elif macd_bearish:
                    bearish_score += 1
                
                if rsi_bullish:
                    bullish_score += 1
                if rsi_bearish:
                    bearish_score += 1
                    
                if rsi_oversold_crossup:
                    bullish_score += 1
                if rsi_overbought_crossdown:
                    bearish_score += 1
                
                if stoch_bullish:
                    bullish_score += 1
                if stoch_bearish:
                    bearish_score += 1
                
                if volume_strong:
                    if bullish_score > bearish_score:
                        bullish_score += 1
                    elif bearish_score > bullish_score:
                        bearish_score += 1
                
                min_score_required = 4
                
                if bullish_score >= min_score_required and bullish_score > bearish_score:
                    signal = 'BUY'
                    if ema_trend_bullish:
                        confidence_reasons.append("EMA trend bullish")
                    if macd_bullish_crossover:
                        confidence_reasons.append("MACD bullish crossover (konfirmasi kuat)")
                    elif macd_bullish:
                        confidence_reasons.append("MACD bullish")
                    if rsi_oversold_crossup:
                        confidence_reasons.append("RSI keluar dari oversold")
                    elif rsi_bullish:
                        confidence_reasons.append("RSI di atas 50 (momentum bullish)")
                    if stoch_bullish:
                        confidence_reasons.append("Stochastic konfirmasi bullish")
                    if volume_strong:
                        confidence_reasons.append("Volume tinggi konfirmasi")
                    confidence_reasons.append(f"Signal score: {bullish_score}/{bearish_score}")
                        
                elif bearish_score >= min_score_required and bearish_score > bullish_score:
                    signal = 'SELL'
                    if ema_trend_bearish:
                        confidence_reasons.append("EMA trend bearish")
                    if macd_bearish_crossover:
                        confidence_reasons.append("MACD bearish crossover (konfirmasi kuat)")
                    elif macd_bearish:
                        confidence_reasons.append("MACD bearish")
                    if rsi_overbought_crossdown:
                        confidence_reasons.append("RSI keluar dari overbought")
                    elif rsi_bearish:
                        confidence_reasons.append("RSI di bawah 50 (momentum bearish)")
                    if stoch_bearish:
                        confidence_reasons.append("Stochastic konfirmasi bearish")
                    if volume_strong:
                        confidence_reasons.append("Volume tinggi konfirmasi")
                    confidence_reasons.append(f"Signal score: {bearish_score}/{bullish_score}")
            else:
                ema_condition_bullish = ema_trend_bullish or ema_crossover_bullish
                ema_condition_bearish = ema_trend_bearish or ema_crossover_bearish
                
                rsi_condition_bullish = rsi_oversold_crossup or rsi_bullish
                rsi_condition_bearish = rsi_overbought_crossdown or rsi_bearish
                
                if ema_condition_bullish and macd_bullish and rsi_condition_bullish:
                    signal = 'BUY'
                    confidence_reasons.append("Manual: EMA bullish")
                    confidence_reasons.append("MACD bullish (konfirmasi)")
                    if macd_bullish_crossover:
                        confidence_reasons.append("MACD fresh crossover")
                    if rsi_oversold_crossup:
                        confidence_reasons.append("RSI keluar dari oversold")
                    elif rsi_bullish:
                        confidence_reasons.append("RSI bullish")
                    if stoch_bullish:
                        confidence_reasons.append("Stochastic konfirmasi bullish")
                        
                elif ema_condition_bearish and macd_bearish and rsi_condition_bearish:
                    signal = 'SELL'
                    confidence_reasons.append("Manual: EMA bearish")
                    confidence_reasons.append("MACD bearish (konfirmasi)")
                    if macd_bearish_crossover:
                        confidence_reasons.append("MACD fresh crossover")
                    if rsi_overbought_crossdown:
                        confidence_reasons.append("RSI keluar dari overbought")
                    elif rsi_bearish:
                        confidence_reasons.append("RSI bearish")
                    if stoch_bearish:
                        confidence_reasons.append("Stochastic konfirmasi bearish")
            
            if signal:
                trend_strength, trend_desc = self.calculate_trend_strength(indicators)
                
                dynamic_tp_ratio = 1.45 + (trend_strength * 1.05)
                dynamic_tp_ratio = min(max(dynamic_tp_ratio, 1.45), 2.50)
                
                atr = indicators.get('atr', 1.0)
                
                if signal_source == 'auto':
                    sl_distance = max(atr * self.config.SL_ATR_MULTIPLIER, self.config.DEFAULT_SL_PIPS / self.config.XAUUSD_PIP_VALUE)
                else:
                    sl_distance = max(atr * 1.2, 1.0)
                
                tp_distance = sl_distance * dynamic_tp_ratio
                
                if signal == 'BUY':
                    stop_loss = close - sl_distance
                    take_profit = close + tp_distance
                else:
                    stop_loss = close + sl_distance
                    take_profit = close - tp_distance
                
                sl_pips = abs(stop_loss - close) * self.config.XAUUSD_PIP_VALUE
                tp_pips = abs(take_profit - close) * self.config.XAUUSD_PIP_VALUE
                
                lot_size = self.config.FIXED_RISK_AMOUNT / sl_pips if sl_pips > 0 else self.config.LOT_SIZE
                lot_size = max(0.01, min(lot_size, 1.0))
                
                expected_loss = self.config.FIXED_RISK_AMOUNT
                expected_profit = expected_loss * dynamic_tp_ratio
                
                logger.info(f"{signal} signal detected ({signal_source}) on {timeframe}")
                logger.info(f"Trend Strength: {trend_desc} (score: {trend_strength:.2f})")
                logger.info(f"Dynamic TP Ratio: {dynamic_tp_ratio:.2f}x (Expected profit: ${expected_profit:.2f})")
                logger.info(f"Risk: ${expected_loss:.2f} | Reward: ${expected_profit:.2f} | R:R = 1:{dynamic_tp_ratio:.2f}")
                
                return {
                    'signal': signal,
                    'signal_source': signal_source,
                    'entry_price': float(close),
                    'stop_loss': float(stop_loss),
                    'take_profit': float(take_profit),
                    'timeframe': timeframe,
                    'trend_strength': trend_strength,
                    'trend_description': trend_desc,
                    'expected_profit': expected_profit,
                    'expected_loss': expected_loss,
                    'rr_ratio': dynamic_tp_ratio,
                    'lot_size': lot_size,
                    'sl_pips': sl_pips,
                    'tp_pips': tp_pips,
                    'indicators': json.dumps({
                        'ema_short': float(ema_short) if ema_short is not None else None,
                        'ema_mid': float(ema_mid) if ema_mid is not None else None,
                        'ema_long': float(ema_long) if ema_long is not None else None,
                        'rsi': float(rsi) if rsi is not None else None,
                        'macd': float(macd) if macd is not None else None,
                        'macd_signal': float(macd_signal) if macd_signal is not None else None,
                        'macd_histogram': float(macd_histogram) if macd_histogram is not None else None,
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
