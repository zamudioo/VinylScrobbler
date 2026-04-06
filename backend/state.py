#ZamudioScrobbler/backend/state.py
from typing import Optional

class AppState:
    status: str = "idle"              # "idle" | "playing"
    current_track: Optional[dict] = None
    current_session_id: Optional[int] = None  # stats DB session id
    last_norm_key: Optional[tuple] = None     # (artist, normalized_title) for dedup
    detection_enabled: bool = True            # pause/resume detection loop

state = AppState()