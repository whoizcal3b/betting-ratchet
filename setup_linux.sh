#!/bin/bash
# ==============================================================================
# Virtual Ratchet Bot - Linux VPS Setup & Deployment Script
# ==============================================================================

set -e

echo "=========================================================="
echo "    VIRTUAL RATCHET BOT: LINUX VPS INSTALLATION"
echo "=========================================================="

# 1. Update system packages
echo "[*] Updating system packages..."
sudo apt update && sudo apt install -y python3 python3-pip python3-venv curl git

# 2. Set up Python virtual environment
echo "[*] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 3. Install Python dependencies
echo "[*] Installing required Python packages..."
pip install --upgrade pip
pip install playwright python-dotenv pandas beautifulsoup4

# 4. Install Playwright Chromium & system libraries
echo "[*] Installing Playwright Chromium and system dependencies..."
playwright install --with-deps chromium

# 5. Set executable permissions
chmod +x run_linux.sh

echo ""
echo "=========================================================="
echo "  INSTALLATION COMPLETE!"
echo "  1. Edit settings in:  nano .env"
echo "  2. Start the bot:     ./run_linux.sh"
echo "=========================================================="
