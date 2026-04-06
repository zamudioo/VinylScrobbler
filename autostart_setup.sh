#!/usr/bin/env bash
set -e

USER_NAME="$(whoami)"
USER_UID="$(id -u)"
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

BACKEND_SCRIPT="$BASE_DIR/backend.sh"

echo "
██  ██ ▄▄ ▄▄  ▄▄ ▄▄ ▄▄ ▄▄    ▄█████  ▄▄▄▄ ▄▄▄▄   ▄▄▄  ▄▄▄▄  ▄▄▄▄  ▄▄    ▄▄▄▄▄ ▄▄▄▄
██▄▄██ ██ ███▄██ ▀███▀ ██    ▀▀▀▄▄▄ ██▀▀▀ ██▄█▄ ██▀██ ██▄██ ██▄██ ██    ██▄▄  ██▄█▄
 ▀██▀  ██ ██ ▀██   █   ██▄▄▄ █████▀ ▀████ ██ ██ ▀███▀ ██▄█▀ ██▄█▀ ██▄▄▄ ██▄▄▄ ██ ██

(autostart setup — headless)
"

if [ ! -f "$BACKEND_SCRIPT" ]; then
  echo "Error: backend.sh not found. Run setup.sh first."
  exit 1
fi

chmod +x "$BACKEND_SCRIPT"
mkdir -p ~/logs "$SYSTEMD_USER_DIR"

cat > "$SYSTEMD_USER_DIR/VinylScrobbler.service" <<EOF
[Unit]
Description=VinylScrobbler
After=network.target sound.target

[Service]
Type=simple
WorkingDirectory=$BASE_DIR
ExecStart=$BACKEND_SCRIPT
Restart=on-failure
RestartSec=5
Environment=HOME=$HOME
Environment=USER=$USER_NAME
Environment=UID=$USER_UID
StandardOutput=append:%h/logs/vinylscrobbler.log
StandardError=append:%h/logs/vinylscrobbler.log

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable VinylScrobbler.service
systemctl --user start  VinylScrobbler.service

echo ""
echo "Service started: VinylScrobbler"
echo ""
echo "Logs:"
echo "  tail -f ~/logs/vinylscrobbler.log"
echo ""
echo "Status:"
echo "  systemctl --user status VinylScrobbler"
echo ""
echo "IMPORTANT — run once with sudo to keep service alive without login:"
echo "  sudo loginctl enable-linger $USER_NAME"
echo ""

LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
PORT=$(python3 -c "import json; d=json.load(open('$BASE_DIR/backend/config.json')); print(d.get('STATS_PORT',8000))" 2>/dev/null || echo 8000)

echo "Stats dashboard:"
echo "  http://${LOCAL_IP}:${PORT}   (from any device on your network)"
echo ""
