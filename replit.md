# XAUUSD Trading Bot - Project Documentation

## Overview
Bot Telegram untuk memberikan sinyal trading XAUUSD (Emas) dengan strategi scalping M1/M5. Bot menggunakan multiple indikator teknikal (EMA, RSI, Stochastic, ATR) dan mengirimkan notifikasi ke Telegram.

**PENTING**: Bot ini HANYA memberikan sinyal, TIDAK mengeksekusi trade otomatis.

## Current State (November 2025)
- ✅ Fully functional trading signal bot
- ✅ All modules implemented and tested
- ✅ Workflow running successfully
- ✅ Ready for deployment to Koyeb.com

## Recent Changes (November 14, 2025)
1. ✅ **Unlimited Trades Per Day**: Removed MAX_TRADES_PER_DAY limit (set to 999999 for unlimited 24/7 trading)
2. ✅ **Auto Chart Cleanup**: Implemented auto-delete chart feature setelah terkirim ke Telegram untuk menghemat storage
3. ✅ **7 New Modules Created**:
   - `bot/utils.py` - Helper functions (formatting, validation, caching, rate limiting)
   - `bot/pair_config.py` - Trading pair configuration dengan dataclass
   - `bot/error_handler.py` - Advanced error handling dengan decorators, circuit breaker, retry mechanism
   - `bot/alert_system.py` - Alert system untuk berbagai event (entry, exit, daily summary, risk warning)
   - `bot/user_manager.py` - Multi-user management dengan SQLAlchemy models
   - `bot/task_scheduler.py` - Task scheduler untuk automated tasks (cleanup, health check, daily summary)
   - `bot/backtester.py` - Backtesting engine untuk test strategi dengan historical data
4. ✅ **Full Integration**: Semua modul baru sudah terintegrasi dengan TradingBot dan PositionTracker
5. ✅ **Alert System Wired**: Alert notifications untuk trade entry, exit (TP/SL hit), daily summary, system errors
6. ✅ **User Manager Integration**: User activity tracking dan stats updates otomatis
7. ✅ **Error Handler Integration**: Advanced error handling dengan logging dan retry mechanism
8. ✅ **Documentation Updated**: README.md updated dengan fitur-fitur baru

## Project Architecture

### Core Modules
- `config.py` - Configuration management via environment variables
- `main.py` - Main orchestrator with async event loop and health check server
- `bot/database.py` - SQLAlchemy models and session management
- `bot/indicators.py` - Technical indicators (EMA, RSI, Stochastic, ATR)
- `bot/market_data.py` - WebSocket and REST API client for market data
- `bot/strategy.py` - Signal detection logic (BUY/SELL)
- `bot/risk_manager.py` - Risk management and position sizing
- `bot/position_tracker.py` - Position monitoring until TP/SL
- `bot/chart_generator.py` - Chart generation for Telegram
- `bot/telegram_bot.py` - Telegram bot handlers
- `bot/logger.py` - Logging configuration

### Database Schema
- **Trade**: Historical trade records
- **Position**: Active positions being tracked
- **SignalLog**: All generated signals
- **Performance**: Daily performance metrics

### API Integration
1. **Polygon.io** (Primary): WebSocket + REST for XAUUSD OHLCV data
2. **Finnhub** (Fallback): WebSocket + REST backup
3. **Twelve Data** (Tertiary): REST only fallback
4. **GoldAPI/Metals-API** (Last resort): Spot price only

### Strategy Logic
**BUY Signal Conditions:**
- M5 trend: EMA(5) > EMA(10) > EMA(20)
- M1 momentum: RSI < 30 and rising
- M1 stochastic: %K crossing above %D from oversold
- Volume > 1.5x average
- Spread < max threshold

**SELL Signal**: Inverse conditions

## Environment Variables Required

### Essential
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `AUTHORIZED_USER_IDS` - Comma-separated user IDs
- `POLYGON_API_KEY` - Polygon.io API key
- `FINNHUB_API_KEY` - Finnhub API key

### Strategy Parameters (All Configurable)
- EMA_PERIODS, RSI_PERIOD, RSI_OVERSOLD_LEVEL, RSI_OVERBOUGHT_LEVEL
- STOCH_K_PERIOD, STOCH_D_PERIOD, STOCH_SMOOTH_K
- STOCH_OVERSOLD_LEVEL, STOCH_OVERBOUGHT_LEVEL
- ATR_PERIOD, VOLUME_THRESHOLD_MULTIPLIER, MAX_SPREAD_PIPS
- SL_ATR_MULTIPLIER, DEFAULT_SL_PIPS, TP_RR_RATIO, DEFAULT_TP_PIPS
- SIGNAL_COOLDOWN_SECONDS, MAX_TRADES_PER_DAY, DAILY_LOSS_PERCENT

## Deployment

### Replit (Development)
```bash
python main.py
```

### Koyeb (Production 24/7)
1. Push to GitHub
2. Create app on Koyeb
3. Connect GitHub repository
4. Set build type to Dockerfile
5. Configure environment variables
6. Mount persistent volume to `/app/data`
7. Deploy!

### Health Check
- Endpoint: `http://localhost:8080/health`
- Returns JSON with service status

## User Preferences
- Language: **Indonesian**
- Target: Modal kecil 100rb-500rb IDR
- Lot size: 0.01 lot
- Risk per trade: 0.5-1%
- Max trades per day: 5
- Daily loss limit: 3%

## Next Phase Features
- Integrasi API tambahan (Twelve Data, GoldAPI, Metals-API)
- Unit tests untuk semua modul
- Backtesting module dengan data historis
- PostgreSQL migration untuk scalability
- Web dashboard untuk monitoring
- Export riwayat ke CSV/Excel
- Multi-ticker support

## Known Issues
- LSP showing import errors (false positives - all libraries installed)
- pandas_ta not available (using manual indicator calculations)

## Security Notes
- Bot only responds to AUTHORIZED_USER_IDS
- No trade execution capabilities
- All secrets via environment variables
- Database in WAL mode for concurrent access
- Rate limiting on Telegram commands

## Support & Troubleshooting
- Check logs in `logs/bot.log`
- Health check: `curl http://localhost:8080/health`
- Telegram bot status: Send `/start` command
- Database location: `data/bot.db`
