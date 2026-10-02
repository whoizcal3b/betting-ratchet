#!/bin/bash
# ==============================================================================
# Virtual Ratchet 24/7 External Supervisor & Fail-Safe Watchdog
# ==============================================================================
# Runs independently from systemd to monitor:
# 1. Engine Heartbeat freshness (/tmp/virtual_ratchet_heartbeat)
# 2. WireGuard VPN tunnel status (wg0)
# 3. Zombie headless Chromium process cleanup
# ==============================================================================

HEARTBEAT_FILE="/tmp/virtual_ratchet_heartbeat"
MAX_STALE_SECONDS=90
SERVICE_NAME="virtual_ratchet"

echo "[$(date)] Starting Virtual Ratchet 24/7 Watchdog Supervisor..."

while true; do
    sleep 30

    NOW=$(date +%s)

    # 1. Check if the systemd service is marked active
    IS_ACTIVE=$(systemctl is-active $SERVICE_NAME 2>/dev/null || echo "inactive")
    if [ "$IS_ACTIVE" != "active" ]; then
        echo "[$(date)] [WATCHDOG] Service '$SERVICE_NAME' is $IS_ACTIVE. Attempting restart..."
        sudo pkill -9 -f chrome-headless || true
        sudo systemctl restart $SERVICE_NAME
        sleep 10
        continue
    fi

    # 2. Check Engine Heartbeat Freshness
    if [ -f "$HEARTBEAT_FILE" ]; then
        LAST_BEAT=$(stat -c %Y "$HEARTBEAT_FILE" 2>/dev/null || stat -f %m "$HEARTBEAT_FILE" 2>/dev/null || echo "$NOW")
        DIFF=$((NOW - LAST_BEAT))

        if [ "$DIFF" -gt "$MAX_STALE_SECONDS" ]; then
            echo "[$(date)] [WATCHDOG CRITICAL] Engine heartbeat is ${DIFF}s old (exceeds ${MAX_STALE_SECONDS}s threshold)! Force-restarting..."
            sudo pkill -9 -f chrome-headless || true
            sudo rm -f "$HEARTBEAT_FILE"
            sudo systemctl restart $SERVICE_NAME
            sleep 15
            continue
        fi
    fi

    # 3. Check WireGuard VPN Health & Active Nigerian Geo-Lock
    if command -v wg >/dev/null 2>&1; then
        IS_NG=$(curl -s --max-time 4 ip-api.com/json 2>/dev/null | grep -i "Nigeria" || echo "")
        if [ -z "$IS_NG" ]; then
            echo "[$(date)] [WATCHDOG CRITICAL] VPN tunnel not routing through Nigeria! Self-healing WireGuard wg0..."
            sudo ip link delete wg0 2>/dev/null || true
            sudo wg-quick up wg0 2>/dev/null || true
            sudo ip link set dev wg0 mtu 1360 2>/dev/null || true
            sleep 3
            # Restart bot to reload fresh Nigerian session
            sudo systemctl restart $SERVICE_NAME
        fi
    fi

done
