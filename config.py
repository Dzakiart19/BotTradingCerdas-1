import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    AUTHORIZED_USER_IDS = [int(uid.strip()) for uid in os.getenv('AUTHORIZED_USER_IDS', '').split(',') if uid.strip()]
    
    EMA_PERIODS = [int(p.strip()) for p in os.getenv('EMA_PERIODS', '2,3,4').split(',')]
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', '3'))
    RSI_OVERSOLD_LEVEL = int(os.getenv('RSI_OVERSOLD_LEVEL', '30'))
    RSI_OVERBOUGHT_LEVEL = int(os.getenv('RSI_OVERBOUGHT_LEVEL', '70'))
    STOCH_K_PERIOD = int(os.getenv('STOCH_K_PERIOD', '3'))
    STOCH_D_PERIOD = int(os.getenv('STOCH_D_PERIOD', '2'))
    STOCH_SMOOTH_K = int(os.getenv('STOCH_SMOOTH_K', '2'))
    STOCH_OVERSOLD_LEVEL = int(os.getenv('STOCH_OVERSOLD_LEVEL', '20'))
    STOCH_OVERBOUGHT_LEVEL = int(os.getenv('STOCH_OVERBOUGHT_LEVEL', '80'))
    ATR_PERIOD = int(os.getenv('ATR_PERIOD', '4'))
    VOLUME_THRESHOLD_MULTIPLIER = float(os.getenv('VOLUME_THRESHOLD_MULTIPLIER', '0.5'))
    MAX_SPREAD_PIPS = float(os.getenv('MAX_SPREAD_PIPS', '10.0'))
    
    SL_ATR_MULTIPLIER = float(os.getenv('SL_ATR_MULTIPLIER', '1.0'))
    DEFAULT_SL_PIPS = float(os.getenv('DEFAULT_SL_PIPS', '20.0'))
    TP_RR_RATIO = float(os.getenv('TP_RR_RATIO', '1.5'))
    DEFAULT_TP_PIPS = float(os.getenv('DEFAULT_TP_PIPS', '30.0'))
    
    SIGNAL_COOLDOWN_SECONDS = int(os.getenv('SIGNAL_COOLDOWN_SECONDS', '30'))
    MAX_TRADES_PER_DAY = int(os.getenv('MAX_TRADES_PER_DAY', '999999'))
    DAILY_LOSS_PERCENT = float(os.getenv('DAILY_LOSS_PERCENT', '3.0'))
    RISK_PER_TRADE_PERCENT = float(os.getenv('RISK_PER_TRADE_PERCENT', '0.5'))
    
    CHART_AUTO_DELETE = os.getenv('CHART_AUTO_DELETE', 'true').lower() == 'true'
    CHART_EXPIRY_MINUTES = int(os.getenv('CHART_EXPIRY_MINUTES', '60'))
    
    WS_DISCONNECT_ALERT_SECONDS = int(os.getenv('WS_DISCONNECT_ALERT_SECONDS', '30'))
    
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/bot.db')
    
    DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'
    
    HEALTH_CHECK_PORT = int(os.getenv('HEALTH_CHECK_PORT', '8080'))
    
    XAUUSD_PIP_VALUE = 10.0
    LOT_SIZE = 0.01
