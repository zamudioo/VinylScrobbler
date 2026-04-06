
import hashlib
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULTS: dict = {
    "SAMPLE_RATE":        44100,
    "CHUNK_SECONDS":      10,
    "RETRY_DELAY":        15,
    "SILENCE_TIMEOUT":    30,
    "VOLUME_THRESHOLD":   0.01,
    "AUDIO_DEVICE_INDEX": None,
    "LASTFM_API_KEY":     "",
    "LASTFM_API_SECRET":  "",
    "LASTFM_USERNAME":    "",
    "LASTFM_PASSWORD_HASH": "",
    "STATS_PORT":         8000,
}

_SENSITIVE = {"LASTFM_API_KEY", "LASTFM_API_SECRET", "LASTFM_PASSWORD_HASH"}


class Config:
    def __init__(self):
        self._d: dict = {}
        self.reload()

    def reload(self):
        """Re-read config.json from disk."""
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                self._d = {**DEFAULTS, **json.load(f)}
        else:
            self._d = dict(DEFAULTS)

    def save(self, updates: dict):
        """Merge *updates* into config and write to disk.

        Accepts a plain LASTFM_PASSWORD field and auto-hashes it to
        LASTFM_PASSWORD_HASH before saving (plaintext is never stored).
        """
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
        """True only when all required fields are present."""
        return all([
            self._d.get("LASTFM_API_KEY"),
            self._d.get("LASTFM_API_SECRET"),
            self._d.get("LASTFM_USERNAME"),
            self._d.get("LASTFM_PASSWORD_HASH"),
            self._d.get("AUDIO_DEVICE_INDEX") is not None,
        ])

    def to_public(self) -> dict:
        """Return config dict with sensitive fields masked."""
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

SAMPLE_RATE          = cfg._d.get("SAMPLE_RATE",          DEFAULTS["SAMPLE_RATE"])
CHUNK_SECONDS        = cfg._d.get("CHUNK_SECONDS",        DEFAULTS["CHUNK_SECONDS"])
RETRY_DELAY          = cfg._d.get("RETRY_DELAY",          DEFAULTS["RETRY_DELAY"])
SILENCE_TIMEOUT      = cfg._d.get("SILENCE_TIMEOUT",      DEFAULTS["SILENCE_TIMEOUT"])
VOLUME_THRESHOLD     = cfg._d.get("VOLUME_THRESHOLD",     DEFAULTS["VOLUME_THRESHOLD"])
AUDIO_DEVICE_INDEX   = cfg._d.get("AUDIO_DEVICE_INDEX",   DEFAULTS["AUDIO_DEVICE_INDEX"])
LASTFM_API_KEY       = cfg._d.get("LASTFM_API_KEY",       DEFAULTS["LASTFM_API_KEY"])
LASTFM_API_SECRET    = cfg._d.get("LASTFM_API_SECRET",    DEFAULTS["LASTFM_API_SECRET"])
LASTFM_USERNAME      = cfg._d.get("LASTFM_USERNAME",      DEFAULTS["LASTFM_USERNAME"])
LASTFM_PASSWORD_HASH = cfg._d.get("LASTFM_PASSWORD_HASH", DEFAULTS["LASTFM_PASSWORD_HASH"])
STATS_PORT           = cfg._d.get("STATS_PORT",           DEFAULTS["STATS_PORT"])
