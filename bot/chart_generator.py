import os
import pandas as pd
import mplfinance as mpf
from datetime import datetime
from typing import Optional
from bot.logger import setup_logger

logger = setup_logger('ChartGenerator')

class ChartGenerator:
    def __init__(self, config):
        self.config = config
        self.chart_dir = 'charts'
        os.makedirs(self.chart_dir, exist_ok=True)
    
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
            markers = []
            
            if signal:
                entry_price = signal.get('entry_price')
                stop_loss = signal.get('stop_loss')
                take_profit = signal.get('take_profit')
                signal_type = signal.get('signal')
                
                if entry_price and signal_type:
                    marker_color = 'g' if signal_type == 'BUY' else 'r'
                    marker_symbol = '^' if signal_type == 'BUY' else 'v'
                    
                    marker_series = pd.Series(index=df_copy.index, data=[None] * len(df_copy))
                    marker_series.iloc[-1] = entry_price
                    
                    addplot.append(
                        mpf.make_addplot(marker_series, type='scatter', 
                                        markersize=100, marker=marker_symbol, 
                                        color=marker_color, panel=0)
                    )
                
                if stop_loss:
                    sl_line = pd.Series(index=df_copy.index, data=[stop_loss] * len(df_copy))
                    addplot.append(
                        mpf.make_addplot(sl_line, type='line', 
                                        color='red', linestyle='--', 
                                        width=2, panel=0, 
                                        alpha=0.7, label='Stop Loss')
                    )
                
                if take_profit:
                    tp_line = pd.Series(index=df_copy.index, data=[take_profit] * len(df_copy))
                    addplot.append(
                        mpf.make_addplot(tp_line, type='line', 
                                        color='green', linestyle='--', 
                                        width=2, panel=0, 
                                        alpha=0.7, label='Take Profit')
                    )
            
            mc = mpf.make_marketcolors(
                up='g', down='r',
                edge='inherit',
                wick='inherit',
                volume='in'
            )
            
            style = mpf.make_mpf_style(
                marketcolors=mc,
                gridstyle='--',
                y_on_right=True
            )
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'xauusd_{timeframe}_{timestamp}.png'
            filepath = os.path.join(self.chart_dir, filename)
            
            title = f'XAUUSD {timeframe}'
            if signal:
                title += f" - {signal.get('signal', 'SIGNAL')} Signal"
            
            fig, axes = mpf.plot(
                df_copy,
                type='candle',
                style=style,
                title=title,
                ylabel='Price',
                volume=True,
                addplot=addplot if addplot else None,
                savefig=filepath,
                figsize=(12, 8),
                returnfig=True
            )
            
            logger.info(f"Chart generated: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            return None
    
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
