# XAUUSD Trading Bot - Deriv WebSocket Client

Real-time streaming harga XAUUSD (Gold) menggunakan WebSocket Deriv tanpa API key.

## 🚀 Features

- ✅ **Real-time streaming** tick data XAUUSD dari Deriv
- ✅ **Zero API key** required (100% gratis)
- ✅ **Auto-reconnect** dengan error handling lengkap
- ✅ **Heartbeat mechanism** (ping/pong setiap 20 detik)
- ✅ **Production-ready** untuk Replit & Koyeb
- ✅ **Simple & clean** code (hanya asyncio + websockets)
- ✅ **Unlimited streaming** (24/7 no limits)

## 📊 Data Source

**WebSocket Provider:** Deriv  
**URL:** `wss://ws.derivws.com/websockets/v3?app_id=1089`  
**Symbol:** `frxXAUUSD` (Gold vs USD)  
**Subscribe Payload:** `{"ticks": "frxXAUUSD"}`

## 🛠️ Tech Stack

- **Python 3.11+**
- **asyncio** - Async/await operations
- **websockets** - WebSocket client library

## 📦 Installation & Usage

### Replit (Recommended)

1. Fork atau clone repository ini
2. Bot otomatis running dengan workflow `deriv-websocket`
3. View logs di Console tab untuk melihat tick streaming

### Koyeb

1. Deploy dari GitHub repository
2. Set build command: (none)
3. Set run command: `python main.py`
4. Port: tidak perlu (console app)

### Local Development

```bash
# Install dependencies
pip install websockets

# Run
python main.py
```

### Logika Sinyal
**Sinyal BUY:**
- Tren naik di M5 (EMA cepat > EMA sedang > EMA lambat)
- RSI di M1 di bawah oversold level dan mulai naik
- Stochastic %K crossing di atas %D dari area oversold
- Volume > 1.5x rata-rata volume historis
- Spread < threshold maksimum

**Sinyal SELL:** (Kebalikan dari BUY)

### Manajemen Risiko
- **Stop Loss**: Dinamis berdasarkan ATR atau fixed pips
- **Take Profit**: Berdasarkan Risk-Reward Ratio yang dapat dikonfigurasi
- **Cooldown**: Jeda antar sinyal untuk menghindari overtrading
- **Max Trades/Day**: **UNLIMITED (24/7)** - Tidak ada batasan jumlah sinyal
- **Daily Loss Limit**: Bot berhenti jika drawdown melebihi threshold
- **Auto Chart Cleanup**: Chart otomatis dihapus setelah terkirim untuk menghemat storage

### Notifikasi Telegram
- **Sinyal Entry**: Ticker, tipe (BUY/SELL), entry price, TP, SL, spread, estimasi P/L
- **Screenshot Chart**: M1/M5 dengan marker Entry/TP/SL dan nilai indikator (auto-delete)
- **Hasil Trade**: WIN/LOSE notification saat TP/SL tercapai
- **Alert System**: Notifikasi untuk berbagai event (daily summary, risk warning, system error, dll)
- **Timezone**: UTC dan Asia/Jakarta (WIB)

### Fitur Advanced
- **Task Scheduler**: Automated tasks seperti cleanup chart, daily summary, health check
- **Alert System**: Sistem notifikasi advanced untuk berbagai event trading
- **User Manager**: Manajemen multi-user dengan preferences individual
- **Error Handler**: Advanced error handling dengan retry mechanism
- **Backtester**: Engine untuk backtest strategi dengan historical data
- **Pair Config**: Konfigurasi multi-pair trading (XAUUSD, XAGUSD, EURUSD, GBPUSD)

### Perintah Bot
- `/start` - Pesan selamat datang
- `/help` - Daftar perintah dan deskripsi
- `/monitor` - Mulai memantau XAUUSD
- `/stopmonitor` - Hentikan pemantauan
- `/riwayat` - Tampilkan 10 riwayat trading terakhir
- `/performa` - Statistik lengkap (Win Rate, P/L, Profit Factor, dll)
- `/settings` - Lihat/ubah parameter strategi (admin only)

## 🚀 Setup & Installation

### 1. Requirements
- Python 3.11+
- **HANYA** Telegram Bot Token (via [@BotFather](https://t.me/botfather))
- **TIDAK PERLU** API Key lainnya!

### 2. Instalasi Lokal (Development)

```bash
# Clone repository
git clone <repository-url>
cd trading-bot

# Install dependencies
pip install -r requirements.txt

# Buat file .env dari template
cp .env.example .env

# Edit .env dan isi dengan Telegram Bot Token Anda
nano .env
```

### 3. Konfigurasi Environment Variables

Edit file `.env`:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
AUTHORIZED_USER_IDS=123456789,987654321

# Strategi (Opsional - gunakan default atau custom)
EMA_PERIODS=5,10,20
RSI_PERIOD=14
RSI_OVERSOLD_LEVEL=30
RSI_OVERBOUGHT_LEVEL=70
MAX_TRADES_PER_DAY=999999  # Unlimited
CHART_AUTO_DELETE=true  # Auto-delete chart setelah terkirim
# ... dll (lihat .env.example untuk semua opsi)
```

**CATATAN PENTING**: Tidak ada API key yang diperlukan! Bot menggunakan WebSocket broker gratis.

### 4. Jalankan Bot

```bash
# Mode normal
python main.py

# Mode dry-run (tidak tracking posisi aktual)
DRY_RUN=true python main.py
```

### 5. Test Bot
1. Buka Telegram dan cari bot Anda
2. Kirim `/start` untuk memulai
3. Kirim `/monitor` untuk mulai monitoring
4. Bot akan mengirim sinyal saat kondisi terpenuhi

## 🐳 Deployment ke Koyeb.com (24/7)

### 1. Build Docker Image

```bash
docker build -t xauusd-trading-bot .
docker run -p 8080:8080 --env-file .env xauusd-trading-bot
```

### 2. Deploy ke Koyeb

1. **Push ke GitHub**:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo>
git push -u origin main
```

2. **Koyeb Dashboard**:
   - Login ke https://app.koyeb.com
   - Create New App
   - Pilih GitHub repository Anda
   - Build Type: **Dockerfile**
   - Port: **8080**
   - Environment Variables: Tambahkan semua dari `.env`
   - Persistent Storage: Mount ke `/app/data` untuk database
   - Deploy!

3. **Health Check**:
   - Koyeb akan ping `http://your-app:8080/health`
   - Pastikan health check passing

## 📊 Monitoring & Logs

### Logs Lokal
```bash
# Lihat logs real-time
tail -f logs/marketdata.log

# Cari error
grep ERROR logs/*.log
```

### Logs Koyeb
- Akses via Koyeb Dashboard > App > Logs
- Monitor health checks dan restart otomatis

## 🔧 Konfigurasi Lanjutan

### Parameter Strategi (via Environment Variables)

| Variable | Default | Deskripsi |
|----------|---------|-----------|
| `EMA_PERIODS` | 5,10,20 | Periode EMA untuk tren |
| `RSI_PERIOD` | 14 | Periode RSI |
| `RSI_OVERSOLD_LEVEL` | 30 | Level oversold RSI |
| `RSI_OVERBOUGHT_LEVEL` | 70 | Level overbought RSI |
| `STOCH_K_PERIOD` | 14 | Periode %K Stochastic |
| `STOCH_D_PERIOD` | 3 | Periode %D Stochastic |
| `ATR_PERIOD` | 14 | Periode ATR |
| `SL_ATR_MULTIPLIER` | 1.0 | Multiplier ATR untuk SL |
| `DEFAULT_SL_PIPS` | 20.0 | SL fallback (pips) |
| `TP_RR_RATIO` | 1.5 | Risk-Reward ratio |
| `MAX_TRADES_PER_DAY` | 999999 | Batas sinyal per hari (unlimited) |
| `SIGNAL_COOLDOWN_SECONDS` | 120 | Cooldown antar sinyal |
| `DAILY_LOSS_PERCENT` | 3.0 | Max drawdown harian (%) |

### Database

Bot menggunakan SQLite dengan WAL mode untuk performa optimal:
- Path: `/app/data/bot.db` (production) atau `data/bot.db` (local)
- Backup: Gunakan volume persisten di Koyeb
- Migration: Auto-create schema saat startup

### Data Feed Architecture

1. **WebSocket Connection**: Koneksi persistent ke Exness broker
2. **Tick Processing**: Setiap tick (bid/ask) diproses realtime
3. **OHLC Building**: Candle M1/M5 dibangun dari tick feed
4. **Auto-Reconnect**: Reconnect otomatis jika koneksi terputus
5. **No API Key**: Tidak perlu API key apapun!

## ⚠️ Disclaimer & Risk Warning

**PERINGATAN PENTING:**

1. **Tidak Ada Jaminan Profit**: Trading forex/emas memiliki risiko tinggi. Past performance tidak menjamin hasil di masa depan.

2. **Bot Hanya Memberikan Sinyal**: Bot ini TIDAK mengeksekusi trade otomatis. Anda harus melakukan eksekusi manual di platform trading Anda.

3. **Tanggung Jawab User**:
   - Anda bertanggung jawab penuh atas semua keputusan trading
   - Verifikasi setiap sinyal sebelum eksekusi
   - Gunakan lot size dan leverage yang sesuai dengan risk tolerance Anda
   - Jangan trading dengan uang yang Anda tidak mampu untuk kehilangan

4. **Backtesting Dianjurkan**: Test strategi dengan mode dry-run atau backtest sebelum live trading.

5. **Modal Kecil**: Meskipun dirancang untuk modal kecil (100rb-500rb IDR), tetap gunakan manajemen risiko yang ketat (max 1-2% per trade).

## 📞 Support & Issues

Jika menemukan bug atau memiliki pertanyaan:
- Buka issue di GitHub repository
- Periksa logs untuk troubleshooting
- Pastikan koneksi WebSocket stabil

## 📄 License

MIT License - Gunakan dengan risiko Anda sendiri.

---

**Happy Trading! 📈**

*Bot ini adalah tools untuk membantu analisis, bukan financial advice. Selalu lakukan riset sendiri dan trading dengan bijak.*
