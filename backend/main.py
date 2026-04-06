#ZamudioScrobbler/backend/main.py
import asyncio
import os
import re
import time
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from audio import record_chunk, has_audio
from shazam_service import identify
from lastfm_service import scrobble
from stats_service import (
    init_db, record_play, start_session, end_session,
    get_summary, get_history, delete_play, clear_history,
)
from state import state
from config import SAMPLE_RATE, RETRY_DELAY, SILENCE_TIMEOUT
from logger import logger


app = FastAPI(title="VinylScrobbler")

STATS_WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "stats_web")
if os.path.isdir(STATS_WEB_DIR):
    app.mount("/static", StaticFiles(directory=STATS_WEB_DIR), name="static")

clients: set = set()

# ── Track deduplication ───────────────────────────────────────────────────────

# Strips trailing parenthetical/bracketed metadata:
#   (2011 Remaster) · (Remastered) · (Live at Wembley) · (Acoustic Version)
#   (Radio Edit) · (Instrumental) · (feat. Someone) · (2024) · [Deluxe Edition] …
_SUFFIX_PARENS = re.compile(
    r"\s*[\(\[][^\)\]]*"
    r"(remaster(?:ed)?|live|version|edit|radio|acoustic|demo|"
    r"instrumental|inst\.?|karaoke|backing\s+track|minus\s+one|"
    r"deluxe|bonus|single|album|original|anniversary|"
    r"feat\.?|ft\.?|\d{4})"
    r"[^\)\]]*[\)\]]\s*$",
    re.IGNORECASE,
)

# Strips trailing dash-separated metadata (no parens):
#   - Live · - Remastered · - Acoustic · - Radio Edit …
_SUFFIX_DASH = re.compile(
    r"\s*[\-–]\s*"
    r"(remaster(?:ed)?|live|version|edit|radio|acoustic|"
    r"demo|instrumental|inst\.?|karaoke)"
    r".*$",
    re.IGNORECASE,
)

def _normalize_title(title: str) -> str:
    """Strip variant suffixes (remaster, live, instrumental, year…) and lowercase."""
    if not title:
        return ""
    t = title.strip()
    # Apply in a loop: a title can have multiple stacked suffixes,
    # e.g. "Song (Live) (2011 Remaster)" → strip both
    while True:
        stripped = _SUFFIX_PARENS.sub("", t).strip()
        stripped = _SUFFIX_DASH.sub("", stripped).strip()
        if stripped == t:
            break
        t = stripped
    return t.lower()

def _track_norm_key(track: dict) -> tuple:
    """Return a normalized (artist, title) key for dedup comparison."""
    artist = (track.get("artist") or "").strip().lower()
    title  = _normalize_title(track.get("title") or "")
    return (artist, title)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    logger.info("WebSocket client connected")
    try:
        while True:
            await asyncio.sleep(1)
    except Exception:
        pass
    finally:
        clients.discard(ws)
        logger.info("WebSocket client disconnected")

async def broadcast(data: dict):
    dead = []
    for ws in clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


# ── HTTP routes ───────────────────────────────────────────────────────────────

@app.get("/")
async def serve_stats_page():
    path = os.path.join(STATS_WEB_DIR, "index.html")
    return FileResponse(path)

@app.get("/api/now")
async def now_playing():
    return {"status": state.status, "track": state.current_track}

@app.get("/api/detection")
async def detection_status():
    return {"enabled": state.detection_enabled}

@app.post("/api/detection/toggle")
async def toggle_detection():
    state.detection_enabled = not state.detection_enabled
    if not state.detection_enabled:
        # Transition to idle immediately
        if state.status != "idle":
            state.status        = "idle"
            state.current_track = None
            state.last_norm_key = None
            end_session(state.current_session_id)
            state.current_session_id = None
            await broadcast({"status": "idle"})
        logger.info("Detection paused")
    else:
        logger.info("Detection resumed")
    return {"enabled": state.detection_enabled}


@app.get("/api/stats/summary")
async def stats_summary(period: str = "week"):
    allowed = {"today", "week", "month", "year", "all"}
    if period not in allowed:
        return JSONResponse({"error": "invalid period"}, status_code=400)
    return get_summary(period)

@app.get("/api/stats/history")
async def stats_history(page: int = 1, limit: int = 50):
    if limit > 200:
        limit = 200
    return get_history(page, limit)

@app.delete("/api/history/{play_id}")
async def delete_play_entry(play_id: int):
    """Delete a single play entry by ID."""
    ok = delete_play(play_id)
    if not ok:
        return JSONResponse({"error": "not found"}, status_code=404)
    logger.info(f"Deleted play entry id={play_id}")
    return {"deleted": play_id}

@app.delete("/api/history")
async def clear_all_history():
    """Delete all play history."""
    count = clear_history()
    logger.info(f"Cleared all history ({count} entries)")
    return {"deleted": count}


# ── Detection loop ────────────────────────────────────────────────────────────

async def detection_loop():
    silence_start = None

    while True:
        if not state.detection_enabled:
            await asyncio.sleep(1)
            continue

        audio = record_chunk()

        if has_audio(audio):
            silence_start = None

            track = await identify(audio, SAMPLE_RATE)
            if track:
                norm_key = _track_norm_key(track)

                if norm_key != state.last_norm_key:
                    # Genuinely new track (or first detection after silence)
                    state.current_track  = track
                    state.last_norm_key  = norm_key

                    if state.current_session_id is None:
                        state.current_session_id = start_session()

                    record_play(track)
                    scrobble(track)
                else:
                    # Same track (possibly detected as instrumental variant) — skip
                    logger.info(
                        f"Dedup: skipping re-detection of "
                        f"{track.get('artist')} – {track.get('title')}"
                    )

                state.status = "playing"
                await broadcast({"status": "playing", "track": state.current_track})

            await asyncio.sleep(RETRY_DELAY)

        else:
            if silence_start is None:
                silence_start = time.time()

            silence_elapsed = int(time.time() - silence_start)
            logger.info(f"Silence: {silence_elapsed}s")

            if silence_elapsed > SILENCE_TIMEOUT and state.status != "idle":
                state.status           = "idle"
                state.current_track    = None
                state.last_norm_key    = None  # reset dedup key on silence

                end_session(state.current_session_id)
                state.current_session_id = None

                await broadcast({"status": "idle"})

            await asyncio.sleep(1)


@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(detection_loop())
    logger.info("VinylScrobbler backend started (headless mode)")