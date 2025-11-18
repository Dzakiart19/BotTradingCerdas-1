import pandas as pd
import numpy as np
from typing import Dict, Optional

class IndicatorEngine:
    def __init__(self, config):
        self.config = config
        self.ema_periods = config.EMA_PERIODS
        self.rsi_period = config.RSI_PERIOD
        self.stoch_k_period = config.STOCH_K_PERIOD
        self.stoch_d_period = config.STOCH_D_PERIOD
        self.stoch_smooth_k = config.STOCH_SMOOTH_K
        self.atr_period = config.ATR_PERIOD
        self.macd_fast = config.MACD_FAST
        self.macd_slow = config.MACD_SLOW
        self.macd_signal = config.MACD_SIGNAL
    
    def calculate_ema(self, df: pd.DataFrame, period: int) -> pd.Series:
        return df['close'].ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, df: pd.DataFrame, period: int) -> pd.Series:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_stochastic(self, df: pd.DataFrame, k_period: int, d_period: int, smooth_k: int) -> tuple:
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        
        stoch_k = 100 * (df['close'] - low_min) / (high_max - low_min)
        stoch_k = stoch_k.rolling(window=smooth_k).mean()
        stoch_d = stoch_k.rolling(window=d_period).mean()
        
        return stoch_k, stoch_d
    
    def calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def calculate_volume_average(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        return df['volume'].rolling(window=period).mean()
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
        macd_histogram = macd_line - macd_signal
        return macd_line, macd_signal, macd_histogram
    
    def get_indicators(self, df: pd.DataFrame) -> Optional[Dict]:
        min_required = max(30, max(self.ema_periods + [self.rsi_period, self.stoch_k_period, self.atr_period]) + 10)
        if len(df) < min_required:
            return None
        
        indicators = {}
        
        for period in self.ema_periods:
            indicators[f'ema_{period}'] = self.calculate_ema(df, period).iloc[-1]
        
        indicators['rsi'] = self.calculate_rsi(df, self.rsi_period).iloc[-1]
        indicators['rsi_prev'] = self.calculate_rsi(df, self.rsi_period).iloc[-2]
        
        stoch_k, stoch_d = self.calculate_stochastic(
            df, self.stoch_k_period, self.stoch_d_period, self.stoch_smooth_k
        )
        indicators['stoch_k'] = stoch_k.iloc[-1]
        indicators['stoch_d'] = stoch_d.iloc[-1]
        indicators['stoch_k_prev'] = stoch_k.iloc[-2]
        indicators['stoch_d_prev'] = stoch_d.iloc[-2]
        
        indicators['atr'] = self.calculate_atr(df, self.atr_period).iloc[-1]
        
        macd_line, macd_signal, macd_histogram = self.calculate_macd(
            df, self.macd_fast, self.macd_slow, self.macd_signal
        )
        indicators['macd'] = macd_line.iloc[-1]
        indicators['macd_signal'] = macd_signal.iloc[-1]
        indicators['macd_histogram'] = macd_histogram.iloc[-1]
        indicators['macd_prev'] = macd_line.iloc[-2]
        indicators['macd_signal_prev'] = macd_signal.iloc[-2]
        
        indicators['volume'] = df['volume'].iloc[-1]
        indicators['volume_avg'] = self.calculate_volume_average(df).iloc[-1]
        
        indicators['close'] = df['close'].iloc[-1]
        indicators['high'] = df['high'].iloc[-1]
        indicators['low'] = df['low'].iloc[-1]
        
        return indicators
