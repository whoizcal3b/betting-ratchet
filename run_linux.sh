#!/bin/bash
# ==============================================================================
# Virtual Ratchet Bot - Linux VPS Runner Script
# ==============================================================================

cd "$(dirname "$0")"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

while true; do
    echo "[$(date)] Launching Virtual Ratchet Bot..."
    python3 bot.py
    echo "[$(date)] Bot process exited or interrupted. Auto-restarting in 5 seconds (Ctrl+C to cancel)..."
    sleep 5
done
