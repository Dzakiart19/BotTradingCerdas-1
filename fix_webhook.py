#!/usr/bin/env python3
"""
Script untuk check dan fix Telegram webhook di Koyeb
Gunakan script ini jika bot tidak merespon command tapi bisa kirim sinyal
"""

import asyncio
import os
import sys
from telegram import Bot
from telegram.error import TelegramError
import aiohttp

async def check_and_fix_webhook():
    """Check current webhook dan set ulang jika perlu"""
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN tidak ditemukan!")
        print("Set environment variable TELEGRAM_BOT_TOKEN terlebih dahulu")
        return
    
    print("=" * 60)
    print("🔍 CHECKING TELEGRAM WEBHOOK")
    print("=" * 60)
    print()
    
    bot = Bot(token=token)
    
    try:
        print("1️⃣ Mendapatkan info webhook saat ini...")
        webhook_info = await bot.get_webhook_info()
        
        print(f"   URL: {webhook_info.url or '(tidak ada)'}")
        print(f"   Pending updates: {webhook_info.pending_update_count}")
        print(f"   Last error: {webhook_info.last_error_message or '(tidak ada)'}")
        if webhook_info.last_error_date:
            print(f"   Last error date: {webhook_info.last_error_date}")
        print()
        
        koyeb_domain = "noisy-kelsy-dzeckyete-f32b09c2.koyeb.app"
        correct_webhook_url = f"https://{koyeb_domain}/bot{token}"
        
        print("2️⃣ Webhook URL yang benar:")
        print(f"   {correct_webhook_url}")
        print()
        
        if webhook_info.url == correct_webhook_url:
            print("✅ Webhook sudah di-set dengan benar!")
            
            if webhook_info.pending_update_count > 0:
                print(f"⚠️ Ada {webhook_info.pending_update_count} pending updates")
                print("   Ini bisa jadi old updates yang belum diproses")
                print()
                
                response = input("   Hapus pending updates? (y/n): ")
                if response.lower() == 'y':
                    print("   Menghapus webhook dan set ulang...")
                    await bot.delete_webhook(drop_pending_updates=True)
                    await asyncio.sleep(1)
                    success = await bot.set_webhook(
                        url=correct_webhook_url,
                        drop_pending_updates=True,
                        max_connections=5
                    )
                    if success:
                        print("   ✅ Webhook di-set ulang dengan sukses!")
                    else:
                        print("   ❌ Gagal set webhook!")
            else:
                print("✅ Tidak ada pending updates")
                print()
                print("🔍 Testing webhook endpoint...")
                
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(f"https://{koyeb_domain}/health", timeout=10) as resp:
                            if resp.status == 200:
                                print(f"   ✅ Health check OK (status: {resp.status})")
                            else:
                                print(f"   ⚠️ Health check status: {resp.status}")
                    except Exception as e:
                        print(f"   ❌ Tidak bisa akses health check: {e}")
        
        else:
            print("❌ Webhook SALAH atau tidak di-set!")
            print()
            print("3️⃣ Memperbaiki webhook...")
            
            if webhook_info.url:
                print(f"   Menghapus webhook lama: {webhook_info.url}")
                await bot.delete_webhook(drop_pending_updates=True)
                await asyncio.sleep(1)
            
            print(f"   Setting webhook baru: {correct_webhook_url}")
            success = await bot.set_webhook(
                url=correct_webhook_url,
                drop_pending_updates=True,
                max_connections=5
            )
            
            if success:
                print("   ✅ Webhook berhasil di-set!")
                print()
                print("4️⃣ Verifying webhook...")
                await asyncio.sleep(2)
                
                new_info = await bot.get_webhook_info()
                print(f"   URL: {new_info.url}")
                print(f"   Pending updates: {new_info.pending_update_count}")
                
                if new_info.url == correct_webhook_url:
                    print()
                    print("✅✅✅ WEBHOOK SETUP BERHASIL! ✅✅✅")
                    print()
                    print("Sekarang coba kirim command ke bot:")
                    print("  /start")
                    print("  /help")
                    print()
                else:
                    print()
                    print("❌ Webhook masih belum benar, ada masalah!")
            else:
                print("   ❌ Gagal set webhook!")
        
        print()
        print("=" * 60)
        print("INFORMASI BOT")
        print("=" * 60)
        me = await bot.get_me()
        print(f"Bot username: @{me.username}")
        print(f"Bot name: {me.first_name}")
        print(f"Bot ID: {me.id}")
        print()
        print("Test bot dengan kirim command:")
        print(f"  https://t.me/{me.username}")
        print()
        
    except TelegramError as e:
        print(f"❌ Telegram Error: {e}")
        print()
        print("Kemungkinan penyebab:")
        print("1. Token salah atau expired")
        print("2. Bot di-delete dari Telegram")
        print("3. Koneksi internet bermasalah")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_webhook_endpoint():
    """Test apakah webhook endpoint bisa diakses"""
    print()
    print("=" * 60)
    print("🧪 TESTING WEBHOOK ENDPOINT")
    print("=" * 60)
    print()
    
    koyeb_domain = "noisy-kelsy-dzeckyete-f32b09c2.koyeb.app"
    token = os.getenv('TELEGRAM_BOT_TOKEN', 'test')
    webhook_url = f"https://{koyeb_domain}/bot{token}"
    
    print(f"Webhook endpoint: {webhook_url}")
    print()
    
    async with aiohttp.ClientSession() as session:
        print("Testing dengan POST request...")
        try:
            test_data = {
                "update_id": 999999999,
                "message": {
                    "message_id": 1,
                    "from": {
                        "id": 12345,
                        "first_name": "Test"
                    },
                    "chat": {
                        "id": 12345,
                        "type": "private"
                    },
                    "text": "/start"
                }
            }
            
            async with session.post(webhook_url, json=test_data, timeout=10) as resp:
                status = resp.status
                text = await resp.text()
                
                print(f"Status: {status}")
                print(f"Response: {text[:200]}")
                print()
                
                if status == 200:
                    print("✅ Webhook endpoint bisa diakses!")
                elif status == 503:
                    print("❌ Bot dalam limited mode - check environment variables")
                else:
                    print(f"⚠️ Status code: {status}")
                    
        except asyncio.TimeoutError:
            print("❌ Timeout - endpoint tidak merespon")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print()
    print("🔧 TELEGRAM WEBHOOK FIXER FOR KOYEB")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_webhook_endpoint())
    else:
        asyncio.run(check_and_fix_webhook())
