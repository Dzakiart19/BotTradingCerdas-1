import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    AUTHORIZED_USER_IDS = [int(uid.strip()) for uid in os.getenv('AUTHORIZED_USER_IDS', '').split(',') if uid.strip()]
    
    POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')
    FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY', '')
    TWELVEDATA_API_KEY = os.getenv('TWELVEDATA_API_KEY', '')
    GOLDAPI_API_KEY = os.getenv('GOLDAPI_API_KEY', '')
    METALS_API_KEY = os.getenv('METALS_API_KEY', '')
    METALPRICE_API_KEY = os.getenv('METALPRICE_API_KEY', '')
    
    EMA_PERIODS = [int(p.strip()) for p in os.getenv('EMA_PERIODS', '5,10,20').split(',')]
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
    RSI_OVERSOLD_LEVEL = int(os.getenv('RSI_OVERSOLD_LEVEL', '30'))
    RSI_OVERBOUGHT_LEVEL = int(os.getenv('RSI_OVERBOUGHT_LEVEL', '70'))
    STOCH_K_PERIOD = int(os.getenv('STOCH_K_PERIOD', '14'))
    STOCH_D_PERIOD = int(os.getenv('STOCH_D_PERIOD', '3'))
    STOCH_SMOOTH_K = int(os.getenv('STOCH_SMOOTH_K', '3'))
    STOCH_OVERSOLD_LEVEL = int(os.getenv('STOCH_OVERSOLD_LEVEL', '20'))
    STOCH_OVERBOUGHT_LEVEL = int(os.getenv('STOCH_OVERBOUGHT_LEVEL', '80'))
    ATR_PERIOD = int(os.getenv('ATR_PERIOD', '14'))
    VOLUME_THRESHOLD_MULTIPLIER = float(os.getenv('VOLUME_THRESHOLD_MULTIPLIER', '1.5'))
    MAX_SPREAD_PIPS = float(os.getenv('MAX_SPREAD_PIPS', '5.0'))
    
    SL_ATR_MULTIPLIER = float(os.getenv('SL_ATR_MULTIPLIER', '1.0'))
    DEFAULT_SL_PIPS = float(os.getenv('DEFAULT_SL_PIPS', '20.0'))
    TP_RR_RATIO = float(os.getenv('TP_RR_RATIO', '1.5'))
    DEFAULT_TP_PIPS = float(os.getenv('DEFAULT_TP_PIPS', '30.0'))
    
    SIGNAL_COOLDOWN_SECONDS = int(os.getenv('SIGNAL_COOLDOWN_SECONDS', '120'))
    MAX_TRADES_PER_DAY = int(os.getenv('MAX_TRADES_PER_DAY', '5'))
    DAILY_LOSS_PERCENT = float(os.getenv('DAILY_LOSS_PERCENT', '3.0'))
    RISK_PER_TRADE_PERCENT = float(os.getenv('RISK_PER_TRADE_PERCENT', '0.5'))
    
    WS_DISCONNECT_ALERT_SECONDS = int(os.getenv('WS_DISCONNECT_ALERT_SECONDS', '30'))
    
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/bot.db')
    
    DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'
    
    HEALTH_CHECK_PORT = int(os.getenv('HEALTH_CHECK_PORT', '8080'))
    
    XAUUSD_PIP_VALUE = 10.0
    LOT_SIZE = 0.01
