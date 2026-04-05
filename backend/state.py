#ZamudioScrobbler/backend/state.py
from typing import Optional

class AppState:
    status: str = "idle"              # "idle" | "playing"
    current_track: Optional[dict] = None
    current_session_id: Optional[int] = None  # stats DB session id

state = AppState()
