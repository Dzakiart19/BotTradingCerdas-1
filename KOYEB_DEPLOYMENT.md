# Panduan Deploy Trading Bot ke Koyeb

## Prerequisites
1. Akun GitHub dengan repository bot ini
2. Akun Koyeb (https://koyeb.com) - Free tier available
3. Telegram Bot Token dari @BotFather

## Persiapan

### 1. Push Code ke GitHub
```bash
git add .
git commit -m "Koyeb deployment ready"
git push origin main
```

### 2. Environment Variables yang Diperlukan
Di Koyeb dashboard, set environment variables berikut:

**Required:**
- `TELEGRAM_BOT_TOKEN` - Token dari @BotFather
- `AUTHORIZED_USER_IDS` - Telegram user ID (comma-separated, contoh: 123456789,987654321)
- `TELEGRAM_WEBHOOK_MODE` - Set ke `true` untuk webhook mode
- `WEBHOOK_URL` - URL webhook Koyeb Anda (contoh: https://your-app.koyeb.app/webhook)

**Optional:**
- `PORT` - Default 8080 (Koyeb auto-set ini, tidak perlu manual)
- `DRY_RUN` - Set ke `false` untuk trading live (default: true)

## Deployment Steps di Koyeb

### Step 1: Create New Web Service
1. Login ke Koyeb dashboard
2. Klik "Create Web Service"
3. Pilih "GitHub" sebagai deployment method
4. Connect GitHub account dan pilih repository bot ini

### Step 2: Configure Service
**Service Name:** `xauusd-trading-bot` (atau nama pilihan Anda)

**Build Settings:**
- Builder: Docker
- Dockerfile: `Dockerfile` (auto-detected)
- Branch: `main`

**Environment Variables:**
Tambahkan semua env variables yang diperlukan (lihat section di atas)

**Important untuk Webhook Mode:**
- Set `TELEGRAM_WEBHOOK_MODE=true`
- Set `WEBHOOK_URL` dengan format: `https://<your-app-name>.koyeb.app/webhook`
- Contoh: `https://xauusd-trading-bot-username.koyeb.app/webhook`

### Step 3: Health Check Settings
Koyeb akan otomatis detect healthcheck di `/` dan `/health`:
- **Health Check Path:** `/` atau `/health`
- **Port:** 8080 (auto-detected dari EXPOSE di Dockerfile)
- **Grace Period:** 60 seconds (waktu untuk bot startup)

### Step 4: Deploy
1. Klik "Deploy"
2. Wait 3-5 menit untuk build & deployment
3. Monitor logs di Koyeb dashboard

## Verifikasi Deployment

### 1. Check Health Endpoint
```bash
curl https://your-app-name.koyeb.app/health
```

Response yang diharapkan:
```json
{
  "status": "healthy",
  "market_data": "connected",
  "telegram_bot": "running",
  "scheduler": "running",
  "database": "connected",
  "webhook_mode": true
}
```

### 2. Check Logs di Koyeb
Cari log berikut yang menandakan sukses:
```
✅ Webhook configured successfully!
BOT IS NOW RUNNING
Market data connection established
```

### 3. Test Bot di Telegram
1. Buka chat dengan bot Anda di Telegram
2. Send `/start` command
3. Bot harus respond dengan welcome message
4. Coba `/help` untuk list semua commands

## Cara Mendapatkan WEBHOOK_URL

Setelah deploy pertama kali (tanpa WEBHOOK_URL):
1. Deploy dulu dengan `TELEGRAM_WEBHOOK_MODE=false` (polling mode)
2. Setelah deploy sukses, catat URL app Anda dari Koyeb: `https://your-app.koyeb.app`
3. Stop deployment
4. Tambahkan env variable:
   - `TELEGRAM_WEBHOOK_MODE=true`
   - `WEBHOOK_URL=https://your-app.koyeb.app/webhook`
5. Redeploy

**Atau** Anda bisa langsung set dari awal jika sudah tahu nama app Koyeb Anda.

## Troubleshooting

### Bot tidak responding
1. Check logs di Koyeb: Klik service → Logs
2. Verify environment variables sudah benar
3. Pastikan `WEBHOOK_URL` benar-benar accessible dari internet
4. Test manual: `curl https://your-app.koyeb.app/`

### Webhook setup gagal
Error: "Webhook setup failed"
- Pastikan `WEBHOOK_URL` menggunakan HTTPS (bukan HTTP)
- Verify URL benar: `https://your-app.koyeb.app/webhook`
- Check firewall atau network issues
- Koyeb URL harus publicly accessible

### Database error
Logs menunjukkan database connection failed:
- Bot menggunakan SQLite, tidak perlu external database
- Pastikan folder `/app/data` writable (sudah di-handle di Dockerfile)
- Check logs untuk error spesifik

### Market data tidak connect
Logs: "Market data not connected"
- Deriv WebSocket mungkin temporarily down
- Wait beberapa menit, bot akan auto-retry
- Check https://deriv.com status page

## Auto-Restart & Monitoring

Koyeb automatically:
- ✅ Restart on crash
- ✅ Health check setiap 30 detik
- ✅ Auto-deploy on git push (jika configured)
- ✅ Zero-downtime deployment

## Resource Usage (Free Tier)

Free tier Koyeb cukup untuk bot ini:
- **Memory:** ~200-300MB usage (512MB limit OK)
- **CPU:** Low usage, spike saat generate chart
- **Storage:** SQLite database < 100MB
- **Network:** Minimal (WebSocket + Telegram API)

## Update Bot

Push changes ke GitHub:
```bash
git add .
git commit -m "Update trading strategy"
git push origin main
```

Koyeb akan auto-deploy jika configured, atau manual trigger di dashboard.

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | - | Token dari @BotFather |
| `AUTHORIZED_USER_IDS` | ✅ | - | User IDs yang diizinkan |
| `TELEGRAM_WEBHOOK_MODE` | ✅ | false | Enable webhook (set `true` untuk Koyeb) |
| `WEBHOOK_URL` | ✅* | - | URL webhook (*required jika webhook mode) |
| `PORT` | ❌ | 8080 | Koyeb auto-set |
| `DRY_RUN` | ❌ | true | Simulation mode |
| `EMA_PERIODS` | ❌ | 5,10,20 | EMA indicator periods |
| `RSI_PERIOD` | ❌ | 14 | RSI indicator period |
| `FIXED_RISK_AMOUNT` | ❌ | 1 | Fixed SL amount ($) |

## Support

Jika ada masalah:
1. Check logs di Koyeb dashboard
2. Verify semua environment variables
3. Test healthcheck endpoint
4. Review dokumentasi di replit.md

---

**Note:** Bot ini sudah production-ready untuk Koyeb deployment dengan:
- ✅ Automatic webhook setup
- ✅ Health check endpoints (/ dan /health)
- ✅ Environment variable PORT support
- ✅ Robust error handling
- ✅ Auto-restart compatibility
