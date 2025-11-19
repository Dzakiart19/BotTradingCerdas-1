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

**WEBHOOK MODE (Recommended untuk Koyeb):**
```
TELEGRAM_WEBHOOK_MODE=true
WEBHOOK_URL=https://<your-koyeb-domain>/bot<TELEGRAM_BOT_TOKEN>
```

**Catatan Webhook:**
- ✅ Webhook mode lebih efisien dan reliable untuk deployment cloud
- ✅ Bot akan auto-detect Koyeb domain jika `WEBHOOK_URL` tidak diset
- ✅ Pastikan `TELEGRAM_WEBHOOK_MODE=true` untuk enable webhook
- ✅ Server otomatis listen ke PORT dari environment Koyeb
- ✅ Healthcheck endpoint: `/health` (port 8080)
- ✅ Webhook endpoint: `/bot<token>` (auto-registered)

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
FIXED_RISK_AMOUNT=1.0
```

### 5. Instance Configuration

- **Instance type**: Pilih **"Nano"** atau **"Micro"** (gratis tier cukup)
- **Regions**: Pilih region terdekat (e.g., Frankfurt, Singapore)
- **Scaling**: 1 instance (cukup untuk bot)

### 6. Health Check (Wajib)

- **Health check port**: `8080`
- **Health check path**: `/health`
- **Health check protocol**: HTTP

**Status yang dicek:**
- ✅ Market data connection
- ✅ Database status
- ✅ Telegram bot status
- ✅ Task scheduler status
- ✅ Webhook mode status

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

### Webhook Mode Tidak Aktif

**Problem**: Logs menunjukkan "Webhook mode: FALSE" di health check
**Solusi:**
1. Pastikan environment variable `TELEGRAM_WEBHOOK_MODE=true` sudah diset
2. Set `WEBHOOK_URL` atau biarkan auto-detect Koyeb domain
3. Restart service di Koyeb Dashboard
4. Check logs untuk konfirmasi: "✅ Webhook configured successfully!"
5. Test dengan mengirim pesan ke bot di Telegram

**Verifikasi webhook aktif:**
```
curl https://<your-koyeb-domain>/health
```
Response harus menunjukkan `"webhook_mode": true`

### Docker Build Failed - libgl1-mesa-glx Error

**Problem**: Error saat build Docker - "Package 'libgl1-mesa-glx' has no installation candidate"
**Solusi**: ✅ **SUDAH DIPERBAIKI!**
- Dockerfile sudah diupdate untuk menggunakan `libgl1` (Debian Trixie compatible)
- Package dependencies sudah dioptimalkan
- Build sekarang lebih cepat dan lebih kecil

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

## 🎯 Fitur Bot (UPDATED v2.4)

- ✅ **Webhook Mode** - Telegram webhook untuk Koyeb deployment
- ✅ **Auto-detect domain** - Otomatis detect Koyeb/Replit domain
- ✅ **Real-time data** dari Deriv (XAUUSD/Gold)
- ✅ **Zero API key** required untuk market data
- ✅ **Dual signal modes**: 🤖 Auto (strict) & 👤 Manual (relaxed)
- ✅ **Enhanced strategy**: RSI crossover + EMA trend + volume confirmation
- ✅ **No signal spam**: Pemisahan jelas auto vs manual
- ✅ **Chart visualization** setiap sinyal
- ✅ **Position tracking** hingga TP/SL tercapai
- ✅ **Risk management** dengan cooldown & daily loss limit
- ✅ **24/7 monitoring** tanpa henti
- ✅ **Signal source tracking**: Setiap sinyal ter-label sumbernya
- ✅ **Premium subscription**: Weekly & Monthly packages
- ✅ **Admin commands**: User management & database control

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
