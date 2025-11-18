# 🚀 Deploy Trading Bot ke Koyeb

Panduan lengkap untuk deploy XAUUSD Trading Bot ke Koyeb.

## 📋 Prerequisites

1. **Akun Koyeb** (gratis): https://www.koyeb.com/
2. **Telegram Bot Token** dari @BotFather
3. **Telegram User ID** Anda

## 🔧 Step-by-Step Deployment

### 1. Persiapan Repository

Pastikan repository Anda sudah di GitHub/GitLab dan code sudah ter-push.

### 2. Buat Service di Koyeb

1. Login ke **Koyeb Dashboard**: https://app.koyeb.com/
2. Klik **"Create Service"**
3. Pilih **"GitHub"** atau **"GitLab"** sebagai source
4. Connect dan pilih repository trading bot Anda
5. Branch: **main** atau **master**

### 3. Konfigurasi Build

Di bagian **"Build"**:

- **Build command**: (kosongkan, atau isi `pip install -r requirements.txt`)
- **Run command**: `python main.py`

### 4. Environment Variables

Tambahkan environment variables berikut di Koyeb:

**WAJIB:**
```
TELEGRAM_BOT_TOKEN=<token dari @BotFather>
AUTHORIZED_USER_IDS=<user ID Telegram Anda>
```

**Optional (sudah ada default yang bagus):**
```
EMA_PERIODS=5,10,20
RSI_PERIOD=14
STOCH_K_PERIOD=14
ATR_PERIOD=14
SIGNAL_COOLDOWN_SECONDS=30
MAX_SPREAD_PIPS=10.0
SL_ATR_MULTIPLIER=1.0
TP_RR_RATIO=1.5
DEFAULT_SL_PIPS=20.0
DEFAULT_TP_PIPS=30.0
DAILY_LOSS_PERCENT=3.0
RISK_PER_TRADE_PERCENT=0.5
```

### 5. Instance Configuration

- **Instance type**: Pilih **"Nano"** atau **"Micro"** (gratis tier cukup)
- **Regions**: Pilih region terdekat (e.g., Frankfurt, Singapore)
- **Scaling**: 1 instance (cukup untuk bot)

### 6. Health Check (Optional tapi Recommended)

- **Health check port**: `8080`
- **Health check path**: `/health`
- **Health check protocol**: HTTP

### 7. Deploy!

1. Klik **"Deploy"**
2. Tunggu 2-5 menit untuk build & deploy
3. Status akan berubah jadi **"Healthy"** kalau berhasil

## ✅ Verifikasi Deployment

### Test Bot di Telegram

1. Buka Telegram, cari bot Anda
2. Ketik `/start` - harus ada respons
3. Ketik `/getsignal` - harus kirim sinyal trading dengan chart
4. Ketik `/monitor` - mulai monitoring otomatis
5. Ketik `/settings` - lihat konfigurasi

### Cek Logs di Koyeb

1. Buka service Anda di Koyeb Dashboard
2. Tab **"Logs"**
3. Harus lihat:
   ```
   ✅ Connected to Deriv WebSocket
   📡 Subscribed to frxXAUUSD
   Telegram bot is running!
   BOT IS NOW RUNNING
   ```

## 🔍 Troubleshooting

### Bot tidak response di Telegram

**Problem**: Bot tidak merespons command
**Solusi**:
1. Cek Koyeb logs untuk error
2. Pastikan `TELEGRAM_BOT_TOKEN` benar
3. Pastikan `AUTHORIZED_USER_IDS` sesuai dengan user ID Anda

### Database Error

**Problem**: "database is locked" atau error database
**Solusi**:
1. Koyeb menggunakan ephemeral storage
2. Data akan hilang saat redeploy
3. Untuk persistent data, gunakan PostgreSQL external (optional)

### WebSocket Connection Failed

**Problem**: "Failed to connect to Deriv WebSocket"
**Solusi**:
1. Biasanya temporary, tunggu beberapa detik
2. Cek internet connection Koyeb instance
3. Bot auto-reconnect setiap 3 detik

### Health Check Failed

**Problem**: Service status "Unhealthy"
**Solusi**:
1. Pastikan health check port `8080` sudah benar
2. Pastikan bot sudah fully started (tunggu 30 detik)
3. Check logs untuk error saat startup

## 📊 Commands Tersedia

```
/start       - Tampilkan menu utama
/help        - Bantuan lengkap
/monitor     - Mulai monitoring sinyal otomatis
/stopmonitor - Stop monitoring
/getsignal   - Generate sinyal manual sekarang
/riwayat     - Lihat riwayat trading
/performa    - Statistik performa
/settings    - Lihat konfigurasi bot
```

## 🎯 Fitur Bot

- ✅ **Real-time data** dari Deriv (XAUUSD/Gold)
- ✅ **Zero API key** required untuk market data
- ✅ **Automatic signals** dengan indikator EMA, RSI, Stochastic, ATR
- ✅ **Manual signals** on-demand via `/getsignal`
- ✅ **Chart visualization** setiap sinyal
- ✅ **Position tracking** hingga TP/SL tercapai
- ✅ **Risk management** dengan cooldown & daily loss limit
- ✅ **24/7 monitoring** tanpa henti

## 🆓 Free Tier Limits

Koyeb free tier:
- ✅ 1 web service gratis
- ✅ 24/7 uptime
- ✅ Cukup untuk bot trading
- ⚠️ Ephemeral storage (data hilang saat redeploy)

## 🔄 Update Bot

Untuk update bot setelah deployment:

1. Push code baru ke GitHub/GitLab
2. Koyeb auto-redeploy (jika auto-deploy enabled)
3. Atau manual redeploy di Dashboard

## 📞 Support

Jika ada masalah:
1. Cek Koyeb logs dulu
2. Cek Telegram bot dengan `/settings`
3. Restart service di Koyeb Dashboard

---

**Happy Trading! 🚀📈**
