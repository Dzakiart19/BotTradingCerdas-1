# XAUUSD Trading Bot Pro V2 - Full Featured Telegram Bot

## Overview
This project is an automated XAUUSD trading bot with comprehensive features, delivered via Telegram. It provides real-time trading signals, automatic position tracking (until Take Profit/Stop Loss is hit), and notifications for trade outcomes (WIN/LOSE). The bot offers unlimited 24/7 signals, robust risk management, and a database for performance tracking. Key enhancements in Version 2 and 2.3 include a premium subscription system (weekly/monthly), advanced chart generation with technical indicators (EMA, RSI, Stochastic), admin commands for user management, and access control based on subscription status. The latest version also features a refined dual-mode strategy (Auto/Manual signals) for improved precision and opportunity, alongside enhanced signal messages for better clarity and educational value. The project aims to provide a professional and informative trading assistant for XAUUSD.

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
-   **Orchestrator (`main.py`):** Initializes and manages all bot components.
-   **Configuration (`config.py`):** Centralized strategy and risk management settings.

**Bot Modules (`bot/` folder):**
-   **Market Data:** Handles Deriv WebSocket connection and OHLC candle construction.
-   **Strategy:** Implements signal detection using multiple indicators.
-   **Position Tracker:** Monitors real-time trade positions until TP/SL.
-   **Telegram Bot:** Manages all Telegram command handling and notifications.
-   **Chart Generator:** Creates professional charts with integrated technical indicators.
-   **Risk Manager:** Calculates lot sizes, P/L, and enforces risk limits.
-   **Alert System:** Dispatches trade notifications.
-   **Database:** SQLite for persistent trade and user tracking.
-   **User Manager:** Handles user authentication, subscription management, and premium access control.

**UI/UX Decisions:**
-   Telegram serves as the primary user interface.
-   Signal messages are enriched with icons (🤖 for auto, 👤 for manual), source labels, and confidence reasons.
-   Chart generation is a key UI feature, displaying candlesticks, volume, EMA, RSI, and Stochastic in a multi-panel layout for comprehensive visual analysis.
-   Exit charts (WIN/LOSE) are generated with entry, SL, and TP markers.
-   Subscription status and available commands are clearly communicated via the `/start` message.

**Technical Implementations & Feature Specifications:**
-   **Dual Signal Strategy (V2.3):**
    -   **Auto Mode (Strict):** Requires all conditions (EMA trend/crossover, RSI >/< 50, Stochastic confirmation, high volume) to be met (AND logic) for high precision.
    -   **Manual Mode (Relaxed):** Allows for more opportunities with flexible conditions (EMA trend OR crossover, RSI crossover zone OR bullish/bearish, optional Stochastic/Volume) (OR logic).
-   **Indicators:** EMA (5, 10, 20), RSI (14), Stochastic (K=14, D=3), ATR (14), Volume (0.5x average confirmation).
-   **Risk Management:** Dynamic SL (1.0x ATR, min 20 pips), dynamic TP (1.5x R:R, min 30 pips), max spread (5 pips), signal cooldown (120s), daily loss limit (3%), risk per trade (0.5%).
-   **Subscription System:**
    -   Weekly (Rp 15,000) and Monthly (Rp 30,000) premium packages.
    -   Automatic expiry.
    -   Admin access is unlimited.
-   **Admin Commands:** `/riset` (reset trading database), `/addpremium <user_id> <duration>`.
-   **Anti-Duplicate Protection:** Prevents new signals if an active position exists, using `asyncio.Lock()` and active position checks.
-   **Auto-Monitoring & Auto-Build Candles:** Bot automatically starts monitoring and ensures enough historical candles (min 30) are built at startup.
-   **Chart Generation:** Uses `mplfinance` and `matplotlib` to render multi-panel charts with indicators, handling numpy type conversions, timezone consistency, and NaN values.

**System Design Choices:**
-   **Real-time Processing:** Utilizes WebSocket for live tick data from Deriv.
-   **Asynchronous Operations:** Leverages `asyncio` for efficient handling of concurrent tasks (WebSocket, Telegram, position tracking).
-   **Database:** SQLite for lightweight, embedded data storage.
-   **Deployment:** Designed for Replit, with environment variables managed via Replit Secrets.

## External Dependencies
-   **Deriv WebSocket API:** For real-time market data (ticks, OHLC candles) for XAUUSD.
-   **Telegram Bot API (`python-telegram-bot`):** For all bot interactions, sending messages, charts, and receiving commands.
-   **SQLAlchemy:** ORM for database interactions with SQLite.
-   **Pandas & NumPy:** For data manipulation and numerical operations, especially in market data processing and indicator calculations.
-   **mplfinance & Matplotlib:** For generating comprehensive financial charts with technical indicators.
-   **pytz:** For robust timezone handling.
-   **aiohttp:** Asynchronous HTTP client, potentially used for external API calls if any (not explicitly detailed but common with `websockets`).
-   **python-dotenv:** For managing environment variables (e.g., `TELEGRAM_BOT_TOKEN`, `AUTHORIZED_USER_IDS`).