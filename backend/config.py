import hashlib
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULTS: dict = {
    "SAMPLE_RATE":          44100,
    "CHUNK_SECONDS":        10,
    "RETRY_DELAY":          15,
    "SILENCE_TIMEOUT":      30,
    "VOLUME_THRESHOLD":     0.01,
    "AUDIO_DEVICE_INDEX":   None,
    # Last.fm (optional)
    "LASTFM_API_KEY":       "",
    "LASTFM_API_SECRET":    "",
    "LASTFM_USERNAME":      "",
    "LASTFM_PASSWORD_HASH": "",
    # Spotify (optional)
    "SPOTIFY_CLIENT_ID":     "",
    "SPOTIFY_CLIENT_SECRET": "",
    "SPOTIFY_REDIRECT_URI":  "http://127.0.0.1:8000/api/spotify/callback",
    "SPOTIFY_ENABLED":       True,
    # Shazam
    "SHAZAM_MIN_MATCHES":   2,
    # Other
    "STATS_PORT":           8000,
}

_SENSITIVE = {"LASTFM_API_KEY", "LASTFM_API_SECRET", "LASTFM_PASSWORD_HASH",
              "SPOTIFY_CLIENT_SECRET"}


class Config:
    def __init__(self):
        self._d: dict = {}
        self.reload()

    def reload(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                self._d = {**DEFAULTS, **json.load(f)}
        else:
            self._d = dict(DEFAULTS)

    def save(self, updates: dict):
        if "LASTFM_PASSWORD" in updates:
            pw = updates.pop("LASTFM_PASSWORD")
            if pw:
                updates["LASTFM_PASSWORD_HASH"] = hashlib.md5(
                    pw.encode()
                ).hexdigest()
        self._d.update(updates)
        with open(CONFIG_PATH, "w") as f:
            json.dump(self._d, f, indent=2)

    def is_configured(self) -> bool:
        """Only requires an audio device — services are optional."""
        return self._d.get("AUDIO_DEVICE_INDEX") is not None

    def lastfm_configured(self) -> bool:
        return all([
            self._d.get("LASTFM_API_KEY"),
            self._d.get("LASTFM_API_SECRET"),
            self._d.get("LASTFM_USERNAME"),
            self._d.get("LASTFM_PASSWORD_HASH"),
        ])

    def spotify_configured(self) -> bool:
        return bool(
            self._d.get("SPOTIFY_CLIENT_ID") and
            self._d.get("SPOTIFY_CLIENT_SECRET") and
            self._d.get("SPOTIFY_ENABLED", True)
        )

    def to_public(self) -> dict:
        d = dict(self._d)
        for k in _SENSITIVE:
            v = d.get(k) or ""
            d[k] = ("••••" + v[-4:]) if len(v) > 4 else ("••••" if v else "")
        return d

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._d[name]
        except KeyError:
            if name in DEFAULTS:
                return DEFAULTS[name]
            raise AttributeError(f"Config has no key '{name}'")


cfg = Config()
