set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$BASE_DIR/venv"
BACKEND_DIR="$BASE_DIR/backend"
FRONTEND_DIR="$BASE_DIR/frontend"
CONFIG_FILE="$BACKEND_DIR/config.py"

echo "                                                                                    
                                                                                    
██  ██ ▄▄ ▄▄  ▄▄ ▄▄ ▄▄ ▄▄    ▄█████  ▄▄▄▄ ▄▄▄▄   ▄▄▄  ▄▄▄▄  ▄▄▄▄  ▄▄    ▄▄▄▄▄ ▄▄▄▄  
██▄▄██ ██ ███▄██ ▀███▀ ██    ▀▀▀▄▄▄ ██▀▀▀ ██▄█▄ ██▀██ ██▄██ ██▄██ ██    ██▄▄  ██▄█▄ 
 ▀██▀  ██ ██ ▀██   █   ██▄▄▄ █████▀ ▀████ ██ ██ ▀███▀ ██▄█▀ ██▄█▀ ██▄▄▄ ██▄▄▄ ██ ██ 
                                                                                    
(user config)"
echo "Run this script WITHOUT sudo."

if [ -z "$XDG_RUNTIME_DIR" ] || [ ! -d "$XDG_RUNTIME_DIR" ]; then
  echo "No graphical session detected."
  echo "Run this script WITHOUT sudo, or start a graphical session"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3 first."
  exit 1
fi

echo "Python found: $(python3 --version)"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

if [ ! -f "$BASE_DIR/requirements.txt" ]; then
  echo "requirements.txt not found"
  exit 1
fi

pip install --upgrade pip
pip install -r "$BASE_DIR/requirements.txt"

read -p "Edit advanced audio settings? (y/N): " ADVANCED

SAMPLE_RATE=44100
CHUNK_SECONDS=10
RETRY_DELAY=15
SILENCE_TIMEOUT=30
VOLUME_THRESHOLD=0.05
MONITOR_IDLE_SECONDS=300

if [[ "$ADVANCED" =~ ^[Yy]$ ]]; then
  read -p "SAMPLE_RATE [$SAMPLE_RATE]: " v && SAMPLE_RATE=${v:-$SAMPLE_RATE}
  read -p "CHUNK_SECONDS [$CHUNK_SECONDS]: " v && CHUNK_SECONDS=${v:-$CHUNK_SECONDS}
  read -p "RETRY_DELAY [$RETRY_DELAY]: " v && RETRY_DELAY=${v:-$RETRY_DELAY}
  read -p "SILENCE_TIMEOUT [$SILENCE_TIMEOUT]: " v && SILENCE_TIMEOUT=${v:-$SILENCE_TIMEOUT}
  read -p "VOLUME_THRESHOLD [$VOLUME_THRESHOLD]: " v && VOLUME_THRESHOLD=${v:-$VOLUME_THRESHOLD}
  read -p "MONITOR_IDLE_SECONDS [$MONITOR_IDLE_SECONDS]: " v && MONITOR_IDLE_SECONDS=${v:-$MONITOR_IDLE_SECONDS}
fi

echo
echo "Detecting audio input devices..."

mapfile -t AUDIO_DEVICES < <(python3 - <<'PY'
import sounddevice as sd
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        print(f"{i}|{d['name']} ({d['max_input_channels']} in)")
PY
)

echo "Select audio device:"
select dev in "${AUDIO_DEVICES[@]}"; do
  AUDIO_DEVICE_INDEX="${dev%%|*}"
  break
done

echo
echo "Last.fm configuration"
read -p "LASTFM_API_KEY: " LASTFM_API_KEY
read -p "LASTFM_API_SECRET: " LASTFM_API_SECRET
read -p "LASTFM_USERNAME: " LASTFM_USERNAME
read -s -p "LASTFM_PASSWORD: " LASTFM_PASSWORD
echo

LASTFM_PASSWORD_HASH=$(echo -n "$LASTFM_USERNAME$LASTFM_PASSWORD" | md5sum | awk '{print $1}')

if ! command -v wlr-randr >/dev/null; then
  echo "wlr-randr not installed."
  exit 1
fi

mapfile -t MONITORS < <(wlr-randr | awk '/^[A-Z]/ {print $1}')

echo "Select monitor:"
select m in "${MONITORS[@]}"; do
  OUTPUT="$m"
  break
done

MODE=$(wlr-randr | awk '/preferred, current/ {print "\""$1", "$3"\""; exit}')
WAYLAND_DISPLAY=$(ls /run/user/$USER_UID | grep '^wayland-' | head -n 1)

cat > "$CONFIG_FILE" <<EOF
SAMPLE_RATE = $SAMPLE_RATE
CHUNK_SECONDS = $CHUNK_SECONDS
RETRY_DELAY = $RETRY_DELAY
SILENCE_TIMEOUT = $SILENCE_TIMEOUT
VOLUME_THRESHOLD = $VOLUME_THRESHOLD
MONITOR_IDLE_SECONDS = $MONITOR_IDLE_SECONDS

AUDIO_DEVICE_INDEX = "$AUDIO_DEVICE_INDEX"

LASTFM_API_KEY = "$LASTFM_API_KEY"
LASTFM_API_SECRET = "$LASTFM_API_SECRET"
LASTFM_USERNAME = "$LASTFM_USERNAME"
LASTFM_PASSWORD_HASH = "$LASTFM_PASSWORD_HASH"

USER = "$(whoami)"
UID = "$(id -u)"
WAYLAND_DISPLAY = "$WAYLAND_DISPLAY"

OUTPUT = "$OUTPUT"
MODE = $MODE
EOF

cat > "$BASE_DIR/backend.sh" <<EOF
#!/usr/bin/env bash
cd "$BASE_DIR"
source venv/bin/activate
cd backend
exec uvicorn main:app --host 0.0.0.0 --port 8000
EOF
chmod +x "$BASE_DIR/backend.sh"

cat > "$BASE_DIR/frontend.sh" <<EOF
#!/usr/bin/env bash
export DISPLAY=:0
chromium \\
--disable-gpu-compositing \\
--disable-gpu-rasterization \\
--disable-smooth-scrolling \\
--disable-features=VizDisplayCompositor \\
--disable-extensions \\
--kiosk file://$FRONTEND_DIR/index.html
EOF
chmod +x "$BASE_DIR/frontend.sh"

echo
echo "Basic Setup finished."
echo "To run manually:"
echo "  ./backend.sh"
echo "  ./frontend.sh"
echo
echo "If you want autostart on boot, run:"
echo "  ./install-services.sh"
