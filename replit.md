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
    -   **Fallback Logic:** Manual mode gracefully handles missing historical data (rsi_prev, stoch_prev) by using current values only.
-   **Indicators:** EMA (5, 10, 20), RSI (14), Stochastic (K=14, D=3), ATR (14), Volume (0.5x average confirmation).
-   **Risk Management:** Fixed SL ($1 per trade), dynamic TP (1.0x-2.5x R:R based on trend strength), max spread (5 pips), signal cooldown (120s), daily loss limit (3%), risk per trade (0.5%).
-   **Subscription System:**
    -   Weekly (Rp 15,000) and Monthly (Rp 30,000) premium packages.
    -   Automatic expiry.
    -   Admin access is unlimited.
-   **Admin Commands:** `/riset` (reset trading database), `/addpremium <user_id> <duration>`.
-   **Anti-Duplicate Protection:** Prevents new signals if an active position exists, using `asyncio.Lock()` and active position checks.
-   **Auto-Monitoring & Auto-Build Candles:** Bot automatically starts monitoring and ensures enough historical candles (min 30) are built at startup.
-   **Chart Generation:** Uses `mplfinance` and `matplotlib` to render multi-panel charts with indicators, handling numpy type conversions, timezone consistency, and NaN values.
-   **Database Migration:** Auto-migration system checks and adds new columns (e.g., `signal_source`) on startup, ensuring backward compatibility without data loss.

**System Design Choices:**
-   **Real-time Processing:** Utilizes WebSocket for live tick data from Deriv.
-   **Asynchronous Operations:** Leverages `asyncio` for efficient handling of concurrent tasks (WebSocket, Telegram, position tracking).
-   **Database:** SQLite for lightweight, embedded data storage with auto-migration support.
-   **Deployment:** Designed for Koyeb and Replit, with Dockerfile using Debian Trixie compatible libraries (`libgl1` instead of `libgl1-mesa-glx`).

## Recent Changes (V2.4 - Dynamic Profit System)
**Date:** November 18, 2025

**Major Enhancement: Dynamic Take Profit Based on Trend Strength**
1. **Intelligent Trend Strength Analysis:**
   - Added `calculate_trend_strength()` function that scores market conditions from 0.0 (weak) to 1.0 (very strong)
   - Analyzes 4 key factors with equal weighting (25% each):
     - **EMA Separation:** Distance between short and long EMA relative to price
     - **MACD Histogram:** Strength of momentum indicator
     - **RSI Momentum:** Distance from neutral zone (50)
     - **Volume Ratio:** Current volume vs average volume
   - Returns descriptive labels: WEAK ⚠️, MEDIUM ⚡, STRONG 💪, VERY STRONG 🔥

2. **Dynamic Take Profit Ratio:**
   - **Formula:** `TP Ratio = 1.0 + (trend_strength × 1.5)`, capped at 2.5x maximum
   - **Fixed Stop Loss:** Always $1 per trade for consistent risk management
   - **Variable Profit Target:**
     - Weak trend (0.0-0.3): R:R 1:1.0-1.45 → Profit $1.00-$1.45
     - Medium trend (0.3-0.5): R:R 1:1.45-1.75 → Profit $1.45-$1.75
     - Strong trend (0.5-0.75): R:R 1:1.75-2.125 → Profit $1.75-$2.12
     - Very Strong trend (0.75-1.0): R:R 1:2.125-2.5 → Profit $2.12-$2.50

3. **Enhanced Signal Messages:**
   - Now displays trend strength with emoji indicators
   - Shows expected profit and loss in dollars
   - Displays calculated R:R ratio for transparency
   - Educational value: helps users understand why each signal has different profit targets

4. **Critical Infrastructure Fixes:**
   - Added explicit `is not None` checks for all indicator comparisons (prevents TypeError)
   - Added zero-division guards (`close > 0`, `volume_avg > 0`)
   - Robust None handling throughout trend strength calculation
   - Production-ready error handling for missing or incomplete indicator data

**V2.3 Changes:**
1. **Fixed Koyeb Deployment Error:** Replaced `libgl1-mesa-glx` with `libgl1` for Debian Trixie compatibility.
2. **Dual-Mode Signal Strategy:** Separated automatic (strict) and manual (relaxed) signal generation to prevent spam/conflicts.
3. **Enhanced Scalping Strategy:** Implemented RSI crossover detection, EMA trend/crossover analysis, Stochastic confirmation, and volume filtering based on proven GitHub strategies (GioxTom RSI Scalping, Alpaca Bot, M1 Countertrend).
4. **Database Schema Update:** Added `signal_source` field to track auto vs manual signals separately for performance analysis.
5. **Auto-Migration System:** Database automatically migrates to add new columns without data loss on bot restart.
6. **Manual Signal Bug Fix:** Added fallback logic to handle missing `rsi_prev` and `stoch_prev` data gracefully, allowing manual signals to work with current values only.
7. **Enhanced Signal Messages:** Added source icons (🤖 auto / 👤 manual), confidence reasons for educational value.

## External Dependencies
-   **Deriv WebSocket API:** For real-time market data (ticks, OHLC candles) for XAUUSD.
-   **Telegram Bot API (`python-telegram-bot`):** For all bot interactions, sending messages, charts, and receiving commands.
-   **SQLAlchemy:** ORM for database interactions with SQLite.
-   **Pandas & NumPy:** For data manipulation and numerical operations, especially in market data processing and indicator calculations.
-   **mplfinance & Matplotlib:** For generating comprehensive financial charts with technical indicators.
-   **pytz:** For robust timezone handling.
-   **aiohttp:** Asynchronous HTTP client, potentially used for external API calls if any (not explicitly detailed but common with `websockets`).
-   **python-dotenv:** For managing environment variables (e.g., `TELEGRAM_BOT_TOKEN`, `AUTHORIZED_USER_IDS`).