#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────
# INSTALL SCRIPT - Poker Game
# Jalankan: bash install.sh
# ─────────────────────────────────────────────

echo "======================================"
echo "  POKER GAME - INSTALL SCRIPT"
echo "======================================"

echo ""
echo "[1/4] Update package..."
pkg update -y

echo ""
echo "[2/4] Install Python & dependensi..."
pkg install python python-kivy -y

echo ""
echo "[3/4] Install pip packages..."
pip install kivy --quiet

echo ""
echo "[4/4] Selesai!"
echo ""
echo "======================================"
echo "  CARA MAIN:"
echo "  python main.py"
echo "======================================"
