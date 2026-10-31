import os
import sys
from dotenv import load_dotenv

def check_environment():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")

    print("\n" + "=" * 65)
    print("   🕌 SISTEM BOT TELEGRAM - LAPORAN PELAKSANAAN AMANAH   ")
    print("=" * 65)

    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("\n⚠️  BOT_TOKEN belum dikonfigurasi!")
        print("-" * 65)
        print("Langkah cepat untuk mengaktifkan bot:")
        print("1. Buka Telegram dan cari akun @BotFather")
        print("2. Kirim perintah /newbot dan ikuti petunjuk hingga mendapatkan token API.")
        print("3. Buka file '.env' di folder project ini.")
        print("4. Masukkan token Anda: BOT_TOKEN=123456789:ABCdefGhIjkLmNoPqRsTuVwXyZ")
        print("5. Jalankan kembali: python run.py\n")
        print("=" * 65 + "\n")
        sys.exit(1)

    print("✅ Konfigurasi BOT_TOKEN ditemukan.")
    print("🚀 Memulai Bot Telegram...")
    print("=" * 65 + "\n")

    import bot
    bot.main()

if __name__ == "__main__":
    check_environment()
