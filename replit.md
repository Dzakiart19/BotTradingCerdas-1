# XAUUSD Trading Bot Pro V2 - Full Featured Telegram Bot

## Overview
This project is an automated XAUUSD trading bot delivered via Telegram. It provides real-time trading signals, automatic position tracking, and notifications for trade outcomes. The bot offers unlimited 24/7 signals, robust risk management, a database for performance tracking, and a premium subscription system. Key features include advanced chart generation with technical indicators, admin commands for user management, and a refined dual-mode strategy (Auto/Manual signals) for improved precision and opportunity. The project aims to provide a professional and informative trading assistant for XAUUSD.

## User Preferences
- Bahasa komunikasi: **Bahasa Indonesia** (100% tidak ada bahasa Inggris)
- Data source: **Deriv WebSocket** (gratis, tanpa API key)
- Trading pair: **XAUUSD** (Gold)
- Notifikasi: **Telegram** dengan foto chart + indikator
- Tracking: **Real-time** sampai TP/SL
- Mode: **24/7 unlimited** untuk admin/premium
- Akurasi: Strategi multi-indicator dengan validasi ketat
- Chart: Menampilkan indikator EMA, RSI, Stochastic (tidak polos)
- Sistem Premium: Paket mingguan (Rp 15.000) dan bulanan (Rp 30.000)
- Kontak untuk langganan: @dzeckyete

## System Architecture
The bot's architecture is modular, designed for scalability and maintainability.

**Core Components:**
-   **Orchestrator (`main.py`):** Initializes and manages bot components.
-   **Configuration (`config.py`):** Centralized settings for strategy and risk management.

**Bot Modules:**
-   **Market Data:** Handles Deriv WebSocket connection and OHLC candle construction.
-   **Strategy:** Implements signal detection using multiple indicators with a dual-mode approach (Auto/Manual).
-   **Position Tracker:** Monitors real-time trade positions per user until TP/SL is hit.
-   **Telegram Bot:** Manages all Telegram command handling and notifications.
-   **Chart Generator:** Creates professional charts with integrated technical indicators.
-   **Risk Manager:** Calculates lot sizes, P/L, and enforces per-user risk limits (e.g., fixed SL, dynamic TP based on trend strength, daily loss limit, signal cooldown).
-   **Alert System:** Dispatches trade notifications.
-   **Database:** SQLite for persistent trade, user, and subscription tracking with auto-migration support.
-   **User Manager:** Handles user authentication, subscription management, and premium access control.

**UI/UX Decisions:**
-   Telegram serves as the primary user interface.
-   Signal messages are enriched with icons, source labels, and confidence reasons.
-   Charts display candlesticks, volume, EMA, RSI, and Stochastic in a multi-panel layout.
-   Exit charts (WIN/LOSE) are generated with entry, SL, and TP markers.

**Technical Implementations & Feature Specifications:**
-   **Dual Signal Strategy:** Auto Mode requires strict conditions (AND logic) for high precision, while Manual Mode allows for more opportunities with flexible conditions (OR logic). A balanced scoring system is used for signal detection.
-   **Indicators:** EMA (5, 10, 20), RSI (14), Stochastic (K=14, D=3), ATR (14), Volume (0.5x average confirmation).
-   **Risk Management:** Fixed Stop Loss ($1 per trade), dynamic Take Profit (1.45x-2.50x R:R based on trend strength), max spread (5 pips), signal cooldown (120s per user), daily loss limit (3% per user), risk per trade (0.5%).
-   **Dynamic SL/TP System (Nov 2025):**
    -   **Dynamic SL Tightening:** When loss reaches $1.00, SL automatically tightens by 50% to protect capital (e.g., $1.00 loss becomes $0.50 max loss).
    -   **Trailing Stop:** When profit reaches $1.00, trailing stop activates with 5 pips distance to lock in profits.
    -   **Dynamic TP Calculation:** TP ranges from $1.45 to $2.50 based on trend strength using formula: `base_tp_ratio = 1.45 + (trend_strength * 1.05)`.
    -   **Position Monitoring:** Automated task runs every 10 seconds to check all active positions and apply dynamic rules.
    -   **Tracking Fields:** Database tracks original_sl, sl_adjustment_count, max_profit_reached, last_price_update for each position.
    -   **/status Command:** Shows detailed position info including Original SL vs Current SL, Trailing Stop status, Max profit reached, and SL adjustment count.
-   **Subscription System:** Weekly and Monthly premium packages with automatic expiry. Admin access is unlimited.
-   **Admin Commands:** `/riset` (reset trading database + monitoring state), `/addpremium <user_id/@username> <duration>`, `/status` (detailed position tracking).
-   **User Commands:** `/premium` & `/beli` untuk informasi subscription, `/langganan` untuk check status.
-   **Anti-Duplicate Protection:** Prevents new signals if an active position exists for a user.
-   **Auto-Monitoring & Auto-Build Candles:** Bot automatically starts monitoring and ensures sufficient historical candles are built at startup.
-   **Chart Generation:** Uses `mplfinance` and `matplotlib` for multi-panel charts.
-   **Database Migration:** Auto-migration system checks and adds new columns on startup, ensuring backward compatibility. Includes backfill logic for existing positions.
-   **Multi-User Support:** Implements per-user position tracking, risk management, and separate data storage within the database.
-   **Deployment:** Designed for Koyeb and Replit deployments, featuring an HTTP server for health checks and webhooks with `/bot<token>` endpoint format, PORT environment variable support, and automatic webhook setup.
-   **Webhook Mode (Nov 2025):** Full webhook support untuk Telegram dengan auto-detect domain, endpoint `/bot<token>`, dan auto-setup saat start. Enable dengan `TELEGRAM_WEBHOOK_MODE=true`.
-   **Free Tier Optimization (Nov 2025):** Optimized untuk Koyeb free tier dengan FREE_TIER_MODE, tick logging sampling (30x reduction), single-threaded chart generation, dan periodic garbage collection untuk reduce CPU/memory usage.

## Recent Changes (November 19, 2025)
**V2.6 - Graceful Shutdown Fix untuk Koyeb** (Latest)

1. ✅ **Signal Handler Perbaikan** (main.py):
   - Menggunakan `asyncio.Event()` untuk shutdown signal (kompatibel Linux/Koyeb)
   - Mengganti `loop.call_soon_threadsafe()` yang bermasalah dengan SIGTERM
   - Shutdown sequence yang lebih clean dan reliable

2. ✅ **Task Tracking & Cancellation** (main.py):
   - Menambahkan `tracked_tasks[]` untuk melacak semua async tasks
   - Proper cancellation untuk market_task, position_task, bot_task dengan timeout
   - Semua tasks di-await sampai selesai atau timeout

3. ✅ **Timeout Shutdown Diperpanjang** (main.py):
   - Meningkatkan timeout dari 10 detik → **28 detik** (sesuai standar Koyeb 30s)
   - Per-component timeout: 5-8 detik per operasi
   - Total shutdown maksimal: 28 detik sebelum force exit

4. ✅ **Force Exit Mechanism** (main.py):
   - Menambahkan `os._exit(0)` jika graceful shutdown melebihi timeout
   - Mencegah zombie process dan hanging di Koyeb
   - Bot pasti keluar dengan clean exit code 0

5. ✅ **Telegram Bot Shutdown** (bot/telegram_bot.py):
   - Tracking `monitoring_tasks[]` untuk semua monitoring loops
   - Proper cancellation monitoring tasks sebelum stop app
   - Webhook cleanup dengan `delete_webhook(drop_pending_updates=True)` + timeout 5s
   - Sequential shutdown: Cancel monitoring → Delete webhook → Stop app → Shutdown app

6. ✅ **Task Scheduler Shutdown** (bot/task_scheduler.py):
   - Tracking `active_task_executions[]` untuk semua running tasks
   - Cancel scheduler loop dengan proper timeout (3s)
   - Cancel semua active tasks dengan timeout (5s)
   - Clean callback system untuk auto-remove completed tasks

7. ✅ **Logging Detail untuk Debugging**:
   - Setiap tahap shutdown tercatat dengan jelas
   - Logging durasi shutdown actual vs timeout
   - Warning jika ada operasi yang timeout
   - Error logs dengan context lengkap

**Impact:** Bot sekarang shutdown dengan benar di Koyeb, merespons SIGTERM, cancel semua tasks, hapus webhook, dan exit dengan clean tanpa zombie process.

---

**V2.5 - Free Tier Optimization**

1. ✅ **FREE_TIER_MODE Configuration** (config.py):
   - Added `FREE_TIER_MODE` flag (default: true) untuk optimize resource usage
   - Added `TICK_LOG_SAMPLE_RATE` (default: 30) untuk control logging frequency
   - Automatic resource optimization when enabled

2. ✅ **Tick Logging Optimization** (bot/market_data.py):
   - Reduced tick logging frequency dari setiap tick → setiap 30 ticks (30x reduction)
   - Centralized tick logging method untuk consistency
   - Changed tick logs dari INFO → DEBUG level untuk reduce I/O overhead
   - Result: Massive reduction in CPU usage dari logging operations

3. ✅ **Chart Generation Optimization** (bot/chart_generator.py):
   - ThreadPoolExecutor max_workers: 1 when FREE_TIER_MODE (vs 2 for normal mode)
   - Single-threaded chart generation untuk reduce CPU spikes
   - Removed per-operation garbage collection untuk avoid excessive pause time

4. ✅ **Smart Position Monitoring** (bot/task_scheduler.py):
   - Position monitoring always runs untuk ghost position reconciliation
   - Logs "Tidak ada active positions" hanya di DEBUG level (not INFO)
   - Prevents missed stale positions while reducing logging noise

5. ✅ **Periodic Garbage Collection** (bot/task_scheduler.py):
   - Added periodic GC task running every 300 seconds (5 minutes)
   - Explicit memory cleanup untuk prevent memory creep
   - Single periodic GC instead of per-operation untuk avoid overhead

**Impact:** CPU usage expected to drop significantly (target: <60%), bot should run stable di Koyeb free tier tanpa shutdown.

---

**V2.4 - Webhook Mode & Documentation Sync**

1. ✅ **Webhook Mode Implementation**:
   - Added full Telegram webhook support untuk Koyeb deployment
   - Auto-detect webhook URL dari environment (Koyeb/Replit domains)
   - Server otomatis listen ke PORT dari environment
   - Webhook endpoint `/bot<token>` dan healthcheck `/health` tersedia
   - Enable dengan environment variable `TELEGRAM_WEBHOOK_MODE=true`

2. ✅ **New Commands**:
   - `/premium` - Alias untuk `/langganan` (cek status subscription)
   - `/beli` - Instruksi lengkap cara berlangganan premium

3. ✅ **Enhanced Admin Commands**:
   - `/riset` sekarang juga reset monitoring state dan active signals
   - Clear monitoring_chats, monitoring flag, dan active_positions
   - Response message lebih informatif tentang apa saja yang direset

4. ✅ **Documentation Updates**:
   - README.md: Dokumentasi lengkap command /premium, /beli, /riset dengan contoh
   - DEPLOYMENT_KOYEB.md: Panduan webhook mode untuk Koyeb dengan troubleshooting
   - Admin commands section dengan format dan contoh penggunaan lengkap
   - Pricing konsisten di semua dokumentasi: 1 Minggu Rp 15.000, 1 Bulan Rp 30.000

## External Dependencies
-   **Deriv WebSocket API:** For real-time XAUUSD market data.
-   **Telegram Bot API (`python-telegram-bot`):** For all Telegram interactions.
-   **SQLAlchemy:** ORM for SQLite database interactions.
-   **Pandas & NumPy:** For data manipulation and numerical operations.
-   **mplfinance & Matplotlib:** For generating financial charts.
-   **pytz:** For timezone handling.
-   **aiohttp:** For asynchronous HTTP server and client operations (e.g., health checks, webhooks).
-   **python-dotenv:** For managing environment variables.