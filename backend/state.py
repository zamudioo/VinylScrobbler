#ZamudioScrobbler/backend/state.py
from typing import Optional
import time

class AppState:
    status = "idle"  # idle | playing
    current_track: Optional[dict] = None
    idle_started_at: Optional[float] = None
    monitor_on: bool = True

state = AppState()
