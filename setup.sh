#!/usr/bin/env bash
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$BASE_DIR/venv"
BACKEND_DIR="$BASE_DIR/backend"
CONFIG_FILE="$BACKEND_DIR/config2.py"

echo "
██  ██ ▄▄ ▄▄  ▄▄ ▄▄ ▄▄ ▄▄    ▄█████  ▄▄▄▄ ▄▄▄▄   ▄▄▄  ▄▄▄▄  ▄▄▄▄  ▄▄    ▄▄▄▄▄ ▄▄▄▄
██▄▄██ ██ ███▄██ ▀███▀ ██    ▀▀▀▄▄▄ ██▀▀▀ ██▄█▄ ██▀██ ██▄██ ██▄██ ██    ██▄▄  ██▄█▄
 ▀██▀  ██ ██ ▀██   █   ██▄▄▄ █████▀ ▀████ ██ ██ ▀███▀ ██▄█▀ ██▄█▀ ██▄▄▄ ██▄▄▄ ██ ██

(headless setup — no display required)
"

echo "Run this script WITHOUT sudo."

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3 first."
  exit 1
fi

echo "Python: $(python3 --version)"

# venv
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

pip install --upgrade pip -q
pip install -r "$BASE_DIR/requirements.txt" -q
echo "Dependencies installed."

read -p "Edit advanced settings? (Audio and timing, you can always change them in backend/config.py) (y/N): " ADVANCED

SAMPLE_RATE=44100
CHUNK_SECONDS=10
RETRY_DELAY=15
SILENCE_TIMEOUT=30
VOLUME_THRESHOLD=0.01
STATS_PORT=8000

if [[ "$ADVANCED" =~ ^[Yy]$ ]]; then
  read -p "SAMPLE_RATE [$SAMPLE_RATE]: "       v && SAMPLE_RATE=${v:-$SAMPLE_RATE}
  read -p "CHUNK_SECONDS [$CHUNK_SECONDS]: "   v && CHUNK_SECONDS=${v:-$CHUNK_SECONDS}
  read -p "RETRY_DELAY [$RETRY_DELAY]: "       v && RETRY_DELAY=${v:-$RETRY_DELAY}
  read -p "SILENCE_TIMEOUT [$SILENCE_TIMEOUT]: " v && SILENCE_TIMEOUT=${v:-$SILENCE_TIMEOUT}
  read -p "VOLUME_THRESHOLD [$VOLUME_THRESHOLD]: " v && VOLUME_THRESHOLD=${v:-$VOLUME_THRESHOLD}
  read -p "Stats web port [$STATS_PORT]: "     v && STATS_PORT=${v:-$STATS_PORT}
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
read -p "LASTFM_API_KEY: "    LASTFM_API_KEY
read -p "LASTFM_API_SECRET: " LASTFM_API_SECRET
read -p "LASTFM_USERNAME: "   LASTFM_USERNAME
read -s -p "LASTFM_PASSWORD: " LASTFM_PASSWORD
echo

LASTFM_PASSWORD_HASH=$(echo -n "$LASTFM_PASSWORD" | md5sum | awk '{print $1}')

cat > "$CONFIG_FILE" <<EOF

SAMPLE_RATE       = $SAMPLE_RATE
CHUNK_SECONDS     = $CHUNK_SECONDS
RETRY_DELAY       = $RETRY_DELAY
SILENCE_TIMEOUT   = $SILENCE_TIMEOUT
VOLUME_THRESHOLD  = $VOLUME_THRESHOLD
AUDIO_DEVICE_INDEX = "$AUDIO_DEVICE_INDEX"

LASTFM_API_KEY      = "$LASTFM_API_KEY"
LASTFM_API_SECRET   = "$LASTFM_API_SECRET"
LASTFM_USERNAME     = "$LASTFM_USERNAME"
LASTFM_PASSWORD_HASH = "$LASTFM_PASSWORD_HASH"

STATS_PORT = $STATS_PORT
EOF

cat > "$BASE_DIR/backend.sh" <<EOF
#!/usr/bin/env bash
cd "$BASE_DIR"
source venv/bin/activate
cd backend
exec uvicorn main:app --host 0.0.0.0 --port $STATS_PORT
EOF
chmod +x "$BASE_DIR/backend.sh"

echo
echo "Setup complete!"
echo
echo "To run manually:"
echo "  ./backend.sh"
echo
echo "Stats dashboard will be available at:"
echo "  http://$(hostname -I | awk '{print $1}'):$STATS_PORT"
echo
echo "To enable autostart on boot:"
echo "  ./autostart_setup.sh"
