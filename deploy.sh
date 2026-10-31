#!/bin/bash
# ==============================================================================
# Script Otomatis Deploy Bot Laporan Amanah di VPS (Ubuntu / Debian)
# ==============================================================================

set -e

echo "=================================================================="
echo "🚀 Memulai Setup & Deploy Bot Telegram Laporan Pelaksanaan Amanah"
echo "=================================================================="

# 1. Update dan install paket sistem yang diperlukan
echo "📦 1. Memperbarui paket sistem dan menginstall dependensi..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv fonts-dejavu git

# 2. Setup Virtual Environment
echo "🐍 2. Menyiapkan Python Virtual Environment (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment berhasil dibuat."
else
    echo "ℹ️ Folder venv sudah ada."
fi

# 3. Upgrade pip dan install dependensi
echo "📥 3. Menginstall library Python dari requirements.txt..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 4. Pengecekan file .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️ File .env dibuat dari .env.example."
        echo "❗ PENTING: Silakan edit file .env dan masukkan BOT_TOKEN Anda:"
        echo "   nano .env"
    fi
else
    echo "✅ File .env ditemukan."
fi

# 5. Dapatkan direktori saat ini dan username
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

echo "⚙️ 4. Menyiapkan Systemd Service (agar bot berjalan otomatis 24/7)..."
SERVICE_FILE="/etc/systemd/system/bot-amanah.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Telegram Bot Laporan Pelaksanaan Amanah
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "✅ File systemd service dibuat di $SERVICE_FILE"

# 6. Reload daemon dan enable service
sudo systemctl daemon-reload
sudo systemctl enable bot-amanah

echo ""
echo "=================================================================="
echo "🎉 DEPLOYMENT SELESAI!"
echo "=================================================================="
echo "Langkah selanjutnya:"
echo "1. Pastikan BOT_TOKEN di file .env sudah diisi:"
echo "   nano .env"
echo ""
echo "2. Jalankan bot sebagai background service 24/7:"
echo "   sudo systemctl start bot-amanah"
echo ""
echo "3. Cek status bot:"
echo "   sudo systemctl status bot-amanah"
echo ""
echo "4. Melihat log realtime bot:"
echo "   sudo journalctl -u bot-amanah -f"
echo "=================================================================="
