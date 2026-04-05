#ZamudioScrobbler/backend/main.py
import asyncio
import os
import time
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from audio import record_chunk, has_audio
from shazam_service import identify
from lastfm_service import scrobble
from stats_service import init_db, record_play, start_session, end_session, get_summary, get_history
from state import state
from config import SAMPLE_RATE, RETRY_DELAY, SILENCE_TIMEOUT
from logger import logger


app = FastAPI(title="VinylScrobbler")

STATS_WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "stats_web")
if os.path.isdir(STATS_WEB_DIR):
    app.mount("/static", StaticFiles(directory=STATS_WEB_DIR), name="static")

clients: set = set()

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


@app.get("/")
async def serve_stats_page():
    """Serve the stats dashboard."""
    path = os.path.join(STATS_WEB_DIR, "index.html")
    return FileResponse(path)

@app.get("/api/now")
async def now_playing():
    """Return current playback status."""
    return {"status": state.status, "track": state.current_track}

@app.get("/api/stats/summary")
async def stats_summary(period: str = "week"):
    """
    Return aggregated stats.
    period: today | week | month | year | all
    """
    allowed = {"today", "week", "month", "year", "all"}
    if period not in allowed:
        return JSONResponse({"error": "invalid period"}, status_code=400)
    return get_summary(period)

@app.get("/api/stats/history")
async def stats_history(page: int = 1, limit: int = 50):
    if limit > 200:
        limit = 200
    return get_history(page, limit)


async def detection_loop():
    silence_start = None

    while True:
        audio = record_chunk()

        if has_audio(audio):
            silence_start = None

            track = await identify(audio, SAMPLE_RATE)
            if track:
                if state.current_track != track:
                    state.current_track = track

                    if state.current_session_id is None:
                        state.current_session_id = start_session()

                    record_play(track)
                    scrobble(track)

                state.status = "playing"
                await broadcast({"status": "playing", "track": track})

            await asyncio.sleep(RETRY_DELAY)

        else:
            if silence_start is None:
                silence_start = time.time()

            silence_elapsed = int(time.time() - silence_start)
            logger.info(f"Silence: {silence_elapsed}s")

            if silence_elapsed > SILENCE_TIMEOUT and state.status != "idle":
                state.status = "idle"
                state.current_track = None

                end_session(state.current_session_id)
                state.current_session_id = None

                await broadcast({"status": "idle"})

            await asyncio.sleep(1)

@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(detection_loop())
    logger.info("VinylScrobbler backend started (headless mode)")
