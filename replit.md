# XAUUSD Trading Bot Pro V2

## Overview
This project is an automated XAUUSD trading bot accessible via Telegram. It delivers real-time trading signals, automatic position tracking, and trade outcome notifications. The bot offers 24/7 unlimited signals, robust risk management, a database for performance tracking, and a premium subscription system. Key features include advanced chart generation with technical indicators, admin commands for user management, and a refined dual-mode strategy (Auto/Manual signals) for enhanced precision and opportunity. The project aims to be a professional and informative trading assistant for XAUUSD.

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
- **Orchestrator:** Initializes and manages bot components.
- **Configuration:** Centralized settings for strategy and risk management.
- **Market Data:** Handles Deriv WebSocket connection and OHLC candle construction.
- **Strategy:** Implements signal detection using multiple indicators with a dual-mode approach (Auto/Manual).
- **Position Tracker:** Monitors real-time trade positions per user until Take Profit (TP) or Stop Loss (SL) is hit.
- **Telegram Bot:** Manages all Telegram command handling and notifications.
- **Chart Generator:** Creates professional charts with integrated technical indicators.
- **Risk Manager:** Calculates lot sizes, P/L, and enforces per-user risk limits (e.g., fixed SL, dynamic TP, daily loss limit, signal cooldown).
- **Alert System:** Dispatches trade notifications.
- **Database:** SQLite for persistent trade, user, and subscription tracking with auto-migration.
- **User Manager:** Handles user authentication, subscription management, and premium access control.

**UI/UX Decisions:**
- Telegram serves as the primary user interface.
- Signal messages are enriched with icons, source labels, and confidence reasons.
- Charts display candlesticks, volume, EMA, RSI, and Stochastic in a multi-panel layout.
- Exit charts (WIN/LOSE) are generated with entry, SL, and TP markers.

**Technical Implementations & Feature Specifications:**
- **Dual Signal Strategy:** Auto Mode requires strict conditions for high precision; Manual Mode allows more opportunities. Uses a balanced scoring system.
- **Indicators:** EMA (5, 10, 20), RSI (14), Stochastic (K=14, D=3), ATR (14), Volume (0.5x average confirmation).
- **Risk Management:** Fixed SL ($1 per trade), dynamic TP (1.45x-2.50x R:R based on trend strength), max spread (5 pips), signal cooldown (120s per user), daily loss limit (3% per user), risk per trade (0.5%).
- **Dynamic SL/TP System:** Includes dynamic SL tightening, trailing stop activation, and dynamic TP calculation based on trend strength. Automated monitoring every 10 seconds.
- **Subscription System:** Weekly and Monthly premium packages with automatic expiry; admin access is unlimited.
- **Admin Commands:** `/riset` (reset trading database + monitoring state), `/addpremium <user_id/@username> <duration>`, `/status` (detailed position tracking).
- **User Commands:** `/premium`, `/beli`, `/langganan` for subscription information and status.
- **Anti-Duplicate Protection:** Prevents new signals if an active position exists for a user.
- **Auto-Monitoring & Auto-Build Candles:** Bot automatically starts monitoring and builds sufficient historical candles at startup.
- **Chart Generation:** Uses `mplfinance` and `matplotlib` for multi-panel charts, configured for headless operation (`matplotlib.use('Agg')`).
- **Database Migration:** Auto-migration system checks and adds new columns on startup, ensuring backward compatibility.
- **Multi-User Support:** Implements per-user position tracking, risk management, and separate data storage.
- **Deployment:** Designed for Koyeb and Replit, featuring an HTTP server for health checks and webhooks with `/bot<token>` endpoint, PORT environment variable support, and automatic webhook setup.
- **Free Tier Optimization (`FREE_TIER_MODE`):** Reduces tick logging frequency, uses single-threaded chart generation, and includes periodic garbage collection to optimize CPU/memory usage for platforms like Koyeb's free tier.
- **Limited Mode:** Bot can run in a "limited mode" even with incomplete configuration (e.g., missing Telegram token), providing a health check endpoint and clear warnings about missing environment variables.
- **Graceful Shutdown:** Implements robust signal handling, task tracking, and webhook cleanup for clean shutdowns on platforms like Koyeb.

## External Dependencies
- **Deriv WebSocket API:** For real-time XAUUSD market data.
- **Telegram Bot API (`python-telegram-bot`):** For all Telegram interactions.
- **SQLAlchemy:** ORM for SQLite database interactions.
- **Pandas & NumPy:** For data manipulation and numerical operations.
- **mplfinance & Matplotlib:** For generating financial charts.
- **pytz:** For timezone handling.
- **aiohttp:** For asynchronous HTTP server and client operations (health checks, webhooks).
- **python-dotenv:** For managing environment variables.