# XAUUSD Trading Bot - Replit Project

## Gambaran Proyek
Real-time streaming XAUUSD (Gold) prices menggunakan Deriv WebSocket tanpa API key.

## Perubahan Terbaru (17 November 2025 - Latest)

### Complete Rewrite: Deriv WebSocket Client
- **DIHAPUS**: Complex trading bot dengan multi-component architecture
- **DIHAPUS**: Semua API key dependencies (Exness, Polygon, Finnhub, etc)
- **DITAMBAHKAN**: Simple production-ready WebSocket client
- **Data Source**: Deriv WebSocket API (public demo app_id=1089)
- **URL**: `wss://ws.derivws.com/websockets/v3?app_id=1089`
- **Subscribe**: `{"ticks": "frxXAUUSD"}`
- **Output**: `[epoch] timestamp | bid=X, ask=X, quote=X`

### Architecture
**Simple Single-File Design:**
- `main.py`: Complete WebSocket client (~200 lines)
  - `connect()`: Establish WebSocket connection
  - `subscribe_ticks()`: Subscribe ke frxXAUUSD
  - `send_heartbeat()`: Ping/pong every 20 seconds
  - `handle_ticks()`: Print tick data to console
  - `run()`: Infinite loop dengan auto-reconnect
  - Error handling: ConnectionClosed, TimeoutError, gaierror, etc

**Libraries:**
- asyncio (built-in)
- websockets
- json (built-in)
- time (built-in)
- datetime (built-in)

### File Changes
- `main.py`: Complete rewrite - simple WebSocket client
- `main_old_backup.py`: Backup of old complex bot
- `README.md`: Updated documentation
- `replit.md`: Updated project notes
- Workflow: `deriv-websocket` runs `python main.py`

## Struktur Proyek

**Active Files (Production):**
- `main.py`: Complete Deriv WebSocket client (~200 lines)
- `requirements.txt`: Dependencies (websockets==12.0)
- `README.md`: Documentation
- `replit.md`: Project notes
- Workflow: `deriv-websocket` runs `python main.py`

**Archived Files (Backup Only):**
- `old_trading_bot/`: Legacy trading bot code (tidak dipakai)
- `main_old_backup.py`: Old orchestrator backup
- `README_old_backup.md`: Old documentation backup
- `data/`, `logs/`, `charts/`: Old data folders (bisa dihapus)

**Dependencies (Active):**
- asyncio (built-in)
- websockets==12.0 (external)
- json, time, datetime (built-in)

**Note:** Hanya `main.py` yang aktif digunakan. Semua files di `old_trading_bot/` adalah backup untuk reference saja.

## Configuration

All configuration in `main.py`:

```python
DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"
SYMBOL = "frxXAUUSD"
HEARTBEAT_INTERVAL = 20  # seconds
RECONNECT_DELAY = 3      # seconds
```

## Known Issues

None - WebSocket berfungsi dengan baik dan stabil.

## Preferensi User
- Bahasa komunikasi: Bahasa Indonesia
- NO API KEY - bot 100% gratis
- Data source: Deriv WebSocket only
- Trading pair: XAUUSD
- Output: Console streaming (epoch, bid, ask, quote)
- Mode: 24/7 unlimited streaming

## Deployment
- Platform: Replit / Koyeb
- Port: None (console app)
- Restart policy: Auto-restart on failure
- Workflow: `deriv-websocket` runs `python main.py`

## Catatan Penting
Ini adalah simple WebSocket client untuk streaming realtime XAUUSD prices. Tidak ada trading logic, Telegram, atau database.
