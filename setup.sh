#!/usr/bin/env bash
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$BASE_DIR/venv"
BACKEND_DIR="$BASE_DIR/backend"
CONFIG_JSON="$BACKEND_DIR/config.json"

echo "
██  ██ ▄▄ ▄▄  ▄▄ ▄▄ ▄▄ ▄▄    ▄█████  ▄▄▄▄ ▄▄▄▄   ▄▄▄  ▄▄▄▄  ▄▄▄▄  ▄▄    ▄▄▄▄▄ ▄▄▄▄
██▄▄██ ██ ███▄██ ▀███▀ ██    ▀▀▀▄▄▄ ██▀▀▀ ██▄█▄ ██▀██ ██▄██ ██▄██ ██    ██▄▄  ██▄█▄
 ▀██▀  ██ ██ ▀██   █   ██▄▄▄ █████▀ ▀████ ██ ██ ▀███▀ ██▄█▀ ██▄█▀ ██▄▄▄ ██▄▄▄ ██ ██

(headless setup — no display required)
"

echo "Run this script WITHOUT sudo."
echo ""


if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.10+ first."
  exit 1
fi

echo "Python: $(python3 --version)"
echo ""


if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r "$BASE_DIR/requirements.txt" -q
echo "Dependencies installed."
echo ""


echo "Detecting audio input devices..."
echo ""

mapfile -t AUDIO_DEVICES < <(python3 - <<'PY'
import sounddevice as sd
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        print(f"{i}|{d['name']} ({d['max_input_channels']} ch)")
PY
)

if [ ${#AUDIO_DEVICES[@]} -eq 0 ]; then
  echo "WARNING: No audio input devices found."
  echo "  You can set AUDIO_DEVICE_INDEX later via the web Settings panel."
  AUDIO_DEVICE_INDEX="null"
else
  echo "Select the audio input device (the one connected to your turntable/mixer):"
  select dev in "${AUDIO_DEVICES[@]}"; do
    AUDIO_DEVICE_INDEX="${dev%%|*}"
    echo "Selected: ${dev##*|}"
    break
  done
fi

echo ""


read -p "Stats web port [enter for default(8000)]: " STATS_PORT
STATS_PORT=${STATS_PORT:-8000}

echo ""


if [ -f "$CONFIG_JSON" ]; then
  echo "Updating existing config.json (preserving Last.fm credentials)..."
  python3 - <<PY
import json, os
path = "$CONFIG_JSON"
with open(path) as f:
    d = json.load(f)
d["AUDIO_DEVICE_INDEX"] = $AUDIO_DEVICE_INDEX
d["STATS_PORT"] = $STATS_PORT
with open(path, "w") as f:
    json.dump(d, f, indent=2)
print("  config.json updated.")
PY
else
  echo "Creating config.json..."
  python3 - <<PY
import json
d = {
    "SAMPLE_RATE":        44100,
    "CHUNK_SECONDS":      10,
    "RETRY_DELAY":        15,
    "SILENCE_TIMEOUT":    30,
    "VOLUME_THRESHOLD":   0.01,
    "AUDIO_DEVICE_INDEX": $AUDIO_DEVICE_INDEX,
    "LASTFM_API_KEY":     "",
    "LASTFM_API_SECRET":  "",
    "LASTFM_USERNAME":    "",
    "LASTFM_PASSWORD_HASH": "",
    "STATS_PORT":         $STATS_PORT,
}
with open("$CONFIG_JSON", "w") as f:
    json.dump(d, f, indent=2)
print("  config.json created.")
PY
fi

cat > "$BASE_DIR/backend.sh" <<EOF
#!/usr/bin/env bash
cd "$BASE_DIR"
source venv/bin/activate
cd backend
exec uvicorn main:app --host 0.0.0.0 --port $STATS_PORT
EOF
chmod +x "$BASE_DIR/backend.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo " 1. Start the server:"
echo "      ./backend.sh"
echo ""
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo " 2. Open the dashboard in your browser:"
echo "      http://${LOCAL_IP}:${STATS_PORT}"
echo ""
echo " 3. Complete Last.fm setup in the web UI."
echo "    The setup wizard will open automatically on first visit."
echo ""
echo " To enable autostart on boot:"
echo "      ./autostart_setup.sh"
echo ""
