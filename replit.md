# XAUUSD Trading Bot - Replit Project

## Gambaran Proyek
Bot trading otomatis untuk XAUUSD (Gold) yang mengirimkan sinyal trading ke Telegram berdasarkan analisis teknikal multi-indikator.

## Perubahan Terbaru (17 November 2025)

### Refactoring Data Source
- **DIHAPUS**: Semua dependensi API berbayar (Polygon.io, Finnhub, TwelveData, GoldAPI)
- **DITAMBAHKAN**: WebSocket realtime dari broker Exness
- **URL WebSocket**: `wss://ws-json.exness.com/realtime`
- **OHLC Builder**: Candle M1/M5 dibuild otomatis dari tick feed
- **Volume Proxy**: Menggunakan tick count sebagai proxy volume
- **TIDAK PERLU API KEY**: Bot sepenuhnya gratis tanpa API key

### Arsitektur Data Feed
1. **WebSocket Connection**: Koneksi persistent ke `wss://ws-json.exness.com/realtime`
2. **Tick Processing**: Setiap tick (bid/ask) diproses realtime
3. **OHLC Building**: 
   - M1 candles: Built from tick feed setiap menit
   - M5 candles: Built from tick feed setiap 5 menit
4. **Auto-Reconnect**: Reconnect otomatis dengan unlimited attempts
5. **Zero Dependencies**: Tidak ada API key yang diperlukan

### File yang Dimodifikasi
- `bot/market_data.py`: Complete rewrite untuk WebSocket Exness + OHLC builder
- `config.py`: Removed semua API key fields
- `requirements.txt`: Updated websockets library
- `main.py`: Added WebSocket connection startup
- `bot/telegram_bot.py`: Updated untuk menggunakan spread dari WebSocket
- `README.md`: Updated dokumentasi

## Struktur Proyek

### Core Components
- **main.py**: Orchestrator utama
- **config.py**: Konfigurasi environment (NO API KEYS)
- **bot/market_data.py**: WebSocket client + OHLC builder
- **bot/strategy.py**: Trading strategy logic
- **bot/indicators.py**: Technical indicators (EMA, RSI, Stochastic, ATR)
- **bot/risk_manager.py**: Risk management
- **bot/position_tracker.py**: Position monitoring
- **bot/telegram_bot.py**: Telegram interface
- **bot/database.py**: SQLite database models

### Data Flow
1. WebSocket receives bid/ask ticks from Exness
2. OHLCBuilder builds M1/M5 candles from ticks
3. IndicatorEngine calculates technical indicators
4. TradingStrategy detects BUY/SELL signals
5. RiskManager validates signals
6. Telegram sends notifications to users
7. PositionTracker monitors TP/SL

## Environment Variables Penting

```bash
# Telegram (WAJIB)
TELEGRAM_BOT_TOKEN=your_bot_token
AUTHORIZED_USER_IDS=123456789,987654321

# Trading Parameters
EMA_PERIODS=5,10,20
RSI_PERIOD=14
RSI_OVERSOLD_LEVEL=30
RSI_OVERBOUGHT_LEVEL=70
MAX_TRADES_PER_DAY=999999
SIGNAL_COOLDOWN_SECONDS=120
DAILY_LOSS_PERCENT=3.0

# Mode
DRY_RUN=false
```

## Known Issues

### WebSocket Connection
- URL `wss://ws-json.exness.com/realtime` tidak terdokumentasi publik
- Mungkin tidak dapat diakses dari beberapa environment
- Auto-reconnect akan terus mencoba jika gagal

## Preferensi User
- Bahasa komunikasi: Bahasa Indonesia
- NO API KEY - bot harus 100% gratis
- Data source: WebSocket broker realtime only
- Trading pair: XAUUSD
- Timeframe: M1 dan M5
- Mode: 24/7 unlimited trades

## Deployment
- Platform: Replit / Koyeb
- Database: SQLite dengan persistent storage
- Port: 8080 (health check)
- Restart policy: Always

## Catatan Penting
Bot ini HANYA memberikan sinyal trading via Telegram. TIDAK ada eksekusi trading otomatis. User bertanggung jawab penuh atas semua keputusan trading.
