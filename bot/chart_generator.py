import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf
from datetime import datetime
from typing import Optional
import json
import asyncio
import gc
from concurrent.futures import ThreadPoolExecutor
from bot.logger import setup_logger

logger = setup_logger('ChartGenerator')

class ChartGenerator:
    def __init__(self, config):
        self.config = config
        self.chart_dir = 'charts'
        os.makedirs(self.chart_dir, exist_ok=True)
        max_workers = 1 if self.config.FREE_TIER_MODE else 2
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="chart_gen")
        logger.info(f"ChartGenerator initialized dengan max_workers={max_workers} (FREE_TIER_MODE={self.config.FREE_TIER_MODE})")
    
    def generate_chart(self, df: pd.DataFrame, signal: Optional[dict] = None,
                      timeframe: str = 'M1') -> Optional[str]:
        try:
            if df is None or len(df) < 10:
                logger.warning("Insufficient data for chart generation")
                return None
            
            df_copy = df.copy()
            
            if not isinstance(df_copy.index, pd.DatetimeIndex):
                if 'timestamp' in df_copy.columns:
                    df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'])
                    df_copy.set_index('timestamp', inplace=True)
            
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df_copy.columns for col in required_cols):
                logger.error(f"Missing required columns. Have: {df_copy.columns.tolist()}")
                return None
            
            addplot = []
            
            from bot.indicators import IndicatorEngine
            indicator_engine = IndicatorEngine(self.config)
            
            ema_5 = df_copy['close'].ewm(span=self.config.EMA_PERIODS[0], adjust=False).mean().bfill().ffill()
            ema_10 = df_copy['close'].ewm(span=self.config.EMA_PERIODS[1], adjust=False).mean().bfill().ffill()
            ema_20 = df_copy['close'].ewm(span=self.config.EMA_PERIODS[2], adjust=False).mean().bfill().ffill()
            
            addplot.append(mpf.make_addplot(ema_5, color='blue', width=1.5, panel=0, label=f'EMA {self.config.EMA_PERIODS[0]}'))
            addplot.append(mpf.make_addplot(ema_10, color='orange', width=1.5, panel=0, label=f'EMA {self.config.EMA_PERIODS[1]}'))
            addplot.append(mpf.make_addplot(ema_20, color='red', width=1.5, panel=0, label=f'EMA {self.config.EMA_PERIODS[2]}'))
            
            delta = df_copy['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.config.RSI_PERIOD).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.config.RSI_PERIOD).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi = rsi.fillna(50)
            
            addplot.append(mpf.make_addplot(rsi, color='purple', width=1.5, panel=1, ylabel='RSI', ylim=(0, 100)))
            
            rsi_70 = pd.Series([70] * len(df_copy), index=df_copy.index)
            rsi_30 = pd.Series([30] * len(df_copy), index=df_copy.index)
            addplot.append(mpf.make_addplot(rsi_70, color='red', width=0.8, panel=1, linestyle='--', alpha=0.5))
            addplot.append(mpf.make_addplot(rsi_30, color='green', width=0.8, panel=1, linestyle='--', alpha=0.5))
            
            low_min = df_copy['low'].rolling(window=self.config.STOCH_K_PERIOD).min()
            high_max = df_copy['high'].rolling(window=self.config.STOCH_K_PERIOD).max()
            stoch_k = 100 * (df_copy['close'] - low_min) / (high_max - low_min)
            stoch_k = stoch_k.rolling(window=self.config.STOCH_SMOOTH_K).mean()
            stoch_d = stoch_k.rolling(window=self.config.STOCH_D_PERIOD).mean()
            stoch_k = stoch_k.fillna(50)
            stoch_d = stoch_d.fillna(50)
            
            addplot.append(mpf.make_addplot(stoch_k, color='blue', width=1.5, panel=2, ylabel='Stochastic', ylim=(0, 100)))
            addplot.append(mpf.make_addplot(stoch_d, color='orange', width=1.5, panel=2))
            
            stoch_80 = pd.Series([80] * len(df_copy), index=df_copy.index)
            stoch_20 = pd.Series([20] * len(df_copy), index=df_copy.index)
            addplot.append(mpf.make_addplot(stoch_80, color='red', width=0.8, panel=2, linestyle='--', alpha=0.5))
            addplot.append(mpf.make_addplot(stoch_20, color='green', width=0.8, panel=2, linestyle='--', alpha=0.5))
            
            if signal:
                entry_price = signal.get('entry_price')
                stop_loss = signal.get('stop_loss')
                take_profit = signal.get('take_profit')
                signal_type = signal.get('signal')
                
                if entry_price and signal_type:
                    marker_color = 'lime' if signal_type == 'BUY' else 'red'
                    marker_symbol = '^' if signal_type == 'BUY' else 'v'
                    
                    import numpy as np
                    marker_series = pd.Series(index=df_copy.index, data=[np.nan] * len(df_copy))
                    marker_series.iloc[-1] = entry_price
                    
                    addplot.append(
                        mpf.make_addplot(marker_series, type='scatter', 
                                        markersize=150, marker=marker_symbol, 
                                        color=marker_color, panel=0)
                    )
                
                if stop_loss:
                    sl_line = pd.Series(index=df_copy.index, data=[stop_loss] * len(df_copy))
                    addplot.append(
                        mpf.make_addplot(sl_line, type='line', 
                                        color='darkred', linestyle='--', 
                                        width=2.5, panel=0, 
                                        alpha=0.8)
                    )
                
                if take_profit:
                    tp_line = pd.Series(index=df_copy.index, data=[take_profit] * len(df_copy))
                    addplot.append(
                        mpf.make_addplot(tp_line, type='line', 
                                        color='darkgreen', linestyle='--', 
                                        width=2.5, panel=0, 
                                        alpha=0.8)
                    )
            
            mc = mpf.make_marketcolors(
                up='lime', down='red',
                edge='inherit',
                wick='inherit',
                volume='in'
            )
            
            style = mpf.make_mpf_style(
                marketcolors=mc,
                gridstyle=':',
                gridcolor='gray',
                gridaxis='both',
                y_on_right=False,
                rc={'font.size': 10}
            )
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'xauusd_{timeframe}_{timestamp}.png'
            filepath = os.path.join(self.chart_dir, filename)
            
            title = f'XAUUSD {timeframe} - Analisis Teknikal'
            if signal:
                title += f" ({signal.get('signal', 'SIGNAL')} Signal)"
            
            fig, axes = mpf.plot(
                df_copy,
                type='candle',
                style=style,
                title=title,
                ylabel='Price (USD)',
                volume=True,
                addplot=addplot if addplot else None,
                savefig=filepath,
                figsize=(14, 12),
                returnfig=True,
                panel_ratios=(3, 1, 1)
            )
            
            logger.info(f"Chart generated: {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            return None
    
    async def generate_chart_async(self, df: pd.DataFrame, signal: Optional[dict] = None,
                                   timeframe: str = 'M1') -> Optional[str]:
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self.generate_chart,
                df,
                signal,
                timeframe
            )
            return result
        except Exception as e:
            logger.error(f"Error in async chart generation: {e}")
            return None
    
    def delete_chart(self, filepath: str):
        try:
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Chart deleted: {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting chart: {e}")
            return False
    
    def shutdown(self):
        try:
            logger.info("Shutting down ChartGenerator executor...")
            self.executor.shutdown(wait=True, cancel_futures=True)
            logger.info("ChartGenerator executor shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down executor: {e}")
    
    def cleanup_old_charts(self, days: int = 7):
        try:
            now = datetime.now()
            for filename in os.listdir(self.chart_dir):
                filepath = os.path.join(self.chart_dir, filename)
                if os.path.isfile(filepath):
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if (now - file_time).days > days:
                        os.remove(filepath)
                        logger.info(f"Deleted old chart: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up charts: {e}")
