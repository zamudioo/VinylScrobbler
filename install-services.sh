
set -e

USER_NAME="$(whoami)"
USER_UID="$(id -u)"
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

BACKEND_SCRIPT="$BASE_DIR/backend.sh"
FRONTEND_SCRIPT="$BASE_DIR/frontend.sh"

echo "                                                                                    
                                                                                    
██  ██ ▄▄ ▄▄  ▄▄ ▄▄ ▄▄ ▄▄    ▄█████  ▄▄▄▄ ▄▄▄▄   ▄▄▄  ▄▄▄▄  ▄▄▄▄  ▄▄    ▄▄▄▄▄ ▄▄▄▄  
██▄▄██ ██ ███▄██ ▀███▀ ██    ▀▀▀▄▄▄ ██▀▀▀ ██▄█▄ ██▀██ ██▄██ ██▄██ ██    ██▄▄  ██▄█▄ 
 ▀██▀  ██ ██ ▀██   █   ██▄▄▄ █████▀ ▀████ ██ ██ ▀███▀ ██▄█▀ ██▄█▀ ██▄▄▄ ██▄▄▄ ██ ██ 
                                                                                    
(autostart config)"

if [[ ! -f "$BACKEND_SCRIPT" || ! -f "$FRONTEND_SCRIPT" ]]; then
  echo "Error: backend.sh or frontend.sh not found."
  echo "Run setup.sh first to generate them."
  exit 1
fi

chmod +x "$BACKEND_SCRIPT" "$FRONTEND_SCRIPT"

mkdir -p "$SYSTEMD_USER_DIR"

# Backend

cat > "$SYSTEMD_USER_DIR/VSBackend.service" <<EOF
[Unit]
Description=VS Backend
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$BASE_DIR
ExecStart=$BACKEND_SCRIPT
Restart=on-failure
Environment=HOME=$HOME
Environment=USER=$USER_NAME
Environment=UID=$USER_UID

[Install]
WantedBy=default.target
EOF

#Frontend

cat > "$SYSTEMD_USER_DIR/VSFrontend.service" <<EOF
[Unit]
Description=VS Frontend
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$BASE_DIR
ExecStart=$FRONTEND_SCRIPT
Restart=on-failure
Environment=HOME=$HOME
Environment=USER=$USER_NAME
Environment=UID=$USER_UID

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable VSBackend.service VSFrontend.service
systemctl --user start VSBackend.service VSFrontend.service

echo ""
echo "Services created and started:"
echo "   - VSBackend"
echo "   - VSFrontend"
echo ""
echo "To view logs:"
echo "   journalctl --user -u VSBackend -f"
echo "   journalctl --user -u VSFrontend -f"
echo ""
echo "Important (run only once with sudo):"
echo "   sudo loginctl enable-linger $USER_NAME"