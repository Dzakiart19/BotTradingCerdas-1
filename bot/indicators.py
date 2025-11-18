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
    
    def get_indicators(self, df: pd.DataFrame) -> Optional[Dict]:
        if len(df) < max(self.ema_periods + [self.rsi_period, self.stoch_k_period, self.atr_period]) + 2:
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
        
        indicators['volume'] = df['volume'].iloc[-1]
        indicators['volume_avg'] = self.calculate_volume_average(df).iloc[-1]
        
        indicators['close'] = df['close'].iloc[-1]
        indicators['high'] = df['high'].iloc[-1]
        indicators['low'] = df['low'].iloc[-1]
        
        return indicators
