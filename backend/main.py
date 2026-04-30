# backend/main.py
import asyncio
import hashlib
import os
import re
import time

import sounddevice as sd
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from audio import record_chunk, has_audio
from config import cfg
from lastfm_service import scrobble, update_now_playing, init_network, test_credentials
from logger import logger
from state import state
from stats_service import (
    init_db, record_play, update_play, start_session, end_session,
    get_summary, get_history, get_artist_detail, delete_play, clear_history,
)

app = FastAPI(title="VinylScrobbler")

STATS_WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "stats_web")
if os.path.isdir(STATS_WEB_DIR):
    app.mount("/static", StaticFiles(directory=STATS_WEB_DIR), name="static")

clients: set = set()

_SUFFIX_PARENS = re.compile(
    r"\s*[\(\[][^\)\]]*"
    r"(remaster(?:ed)?|live|version|edit|radio|acoustic|demo|"
    r"instrumental|inst\.?|karaoke|backing\s+track|minus\s+one|"
    r"deluxe|bonus|single|album|original|anniversary|"
    r"feat\.?|ft\.?|\d{4})"
    r"[^\)\]]*[\)\]]\s*$",
    re.IGNORECASE,
)
_SUFFIX_DASH = re.compile(
    r"\s*[\-–]\s*"
    r"(remaster(?:ed)?|live|version|edit|radio|acoustic|"
    r"demo|instrumental|inst\.?|karaoke)"
    r".*$",
    re.IGNORECASE,
)


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    t = title.strip()
    while True:
        stripped = _SUFFIX_PARENS.sub("", t).strip()
        stripped = _SUFFIX_DASH.sub("", stripped).strip()
        if stripped == t:
            break
        t = stripped
    return t.lower()


def _track_norm_key(track: dict) -> tuple:
    artist = (track.get("artist") or "").strip().lower()
    title  = _normalize_title(track.get("title") or "")
    return (artist, title)


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
    path = os.path.join(STATS_WEB_DIR, "index.html")
    return FileResponse(path)


@app.get("/sw.js")
async def serve_sw():
    """Serve service worker from root scope so it can intercept all requests."""
    path = os.path.join(STATS_WEB_DIR, "sw.js")
    return FileResponse(path, media_type="application/javascript")


@app.get("/manifest.json")
async def serve_manifest():
    path = os.path.join(STATS_WEB_DIR, "manifest.json")
    return FileResponse(path, media_type="application/json")


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

@app.get("/api/setup/status")
async def setup_status():
    configured = cfg.is_configured()
    lastfm_ok  = False
    spotify_ok = False

    if cfg.lastfm_configured():
        result = test_credentials(
            cfg.LASTFM_API_KEY,
            cfg.LASTFM_API_SECRET,
            cfg.LASTFM_USERNAME,
            cfg.LASTFM_PASSWORD_HASH,
        )
        lastfm_ok = result["ok"]

    if cfg.spotify_configured():
        from spotify_service import is_connected
        spotify_ok = is_connected()

    return {
        "configured":     configured,
        "setup_required": not configured,
        "lastfm_configured": cfg.lastfm_configured(),
        "lastfm_ok":      lastfm_ok,
        "spotify_configured": cfg.spotify_configured(),
        "spotify_ok":     spotify_ok,
        "audio_device":   cfg.AUDIO_DEVICE_INDEX,
        "username":       cfg.LASTFM_USERNAME if cfg.lastfm_configured() else "",
    }


@app.get("/api/config")
async def get_config():
    return cfg.to_public()


@app.post("/api/config")
async def update_config(data: dict):
    try:
        cfg.save(data)
        if cfg.lastfm_configured():
            init_network()
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/devices")
async def list_audio_devices():
    devices = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            devices.append({
                "index":    i,
                "name":     d["name"],
                "channels": d["max_input_channels"],
                "default":  d.get("default_samplerate", 44100),
            })
    return {"devices": devices, "current": cfg.AUDIO_DEVICE_INDEX}


@app.post("/api/lastfm/test")
async def test_lastfm(data: dict):
    api_key    = (data.get("api_key")    or "").strip()
    api_secret = (data.get("api_secret") or "").strip()
    username   = (data.get("username")   or "").strip()
    password   = (data.get("password")   or "")

    if not all([api_key, api_secret, username, password]):
        return JSONResponse(
            {"ok": False, "error": "All fields are required"},
            status_code=400,
        )

    password_hash = hashlib.md5(password.encode()).hexdigest()
    result = test_credentials(api_key, api_secret, username, password_hash)

    if result["ok"]:
        result["password_hash"] = password_hash
        result["username"]      = username

    return result


@app.get("/api/spotify/status")
async def spotify_status():
    if not cfg.spotify_configured():
        return {"client_configured": False, "connected": False, "username": None,
                "redirect_uri": cfg.SPOTIFY_REDIRECT_URI}
    from spotify_service import get_status
    return get_status()


@app.get("/api/spotify/auth-url")
async def spotify_auth_url():
    if not cfg.spotify_configured():
        return JSONResponse({"ok": False, "error": "Spotify not configured"}, status_code=400)
    from spotify_service import get_auth_url
    url = get_auth_url()
    return {"ok": True, "url": url}


@app.get("/api/spotify/callback")
async def spotify_callback(code: str = None, error: str = None):
    """Spotify redirects here after user approves. Exchange code for tokens."""
    if error or not code:
        return RedirectResponse(url="/?spotify=error")
    from spotify_service import handle_callback
    ok = handle_callback(code)
    if ok:
        return RedirectResponse(url="/?spotify=connected")
    return RedirectResponse(url="/?spotify=error")


@app.post("/api/spotify/disconnect")
async def spotify_disconnect():
    from spotify_service import disconnect
    disconnect()
    return {"ok": True}


@app.post("/api/spotify/like")
async def spotify_like(data: dict):
    """Manually like a track on Spotify."""
    if not cfg.spotify_configured():
        return JSONResponse({"ok": False, "error": "Spotify not configured"}, status_code=400)
    from spotify_service import like_track, is_connected
    if not is_connected():
        return JSONResponse({"ok": False, "error": "Spotify not connected"}, status_code=401)
    ok = like_track(data)
    return {"ok": ok}



@app.patch("/api/history/{play_id}")
async def patch_play(play_id: int, data: dict):
    """Correct artist / title / album for a play entry."""
    ok = update_play(play_id, data)
    if not ok:
        return JSONResponse({"error": "not found or no valid fields"}, status_code=404)
    logger.info(f"Play {play_id} corrected: {data}")
    return {"updated": play_id}


@app.delete("/api/history/{play_id}")
async def delete_play_entry(play_id: int):
    ok = delete_play(play_id)
    if not ok:
        return JSONResponse({"error": "not found"}, status_code=404)
    logger.info(f"Deleted play entry id={play_id}")
    return {"deleted": play_id}


@app.delete("/api/history")
async def clear_all_history():
    count = clear_history()
    logger.info(f"Cleared all history ({count} entries)")
    return {"deleted": count}



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


@app.get("/api/stats/artist/{artist}")
async def artist_detail(artist: str):
    from urllib.parse import unquote
    return get_artist_detail(unquote(artist))


async def detection_loop():
    silence_start = None

    while True:
        if not state.detection_enabled:
            await asyncio.sleep(1)
            continue

        if not cfg.is_configured():
            await asyncio.sleep(5)
            continue

        audio = record_chunk()

        if has_audio(audio):
            silence_start = None

            from shazam_service import identify
            track = await identify(audio, cfg.SAMPLE_RATE)
            if track:
                norm_key = _track_norm_key(track)

                if norm_key != state.last_norm_key:
                    state.current_track  = track
                    state.last_norm_key  = norm_key

                    if state.current_session_id is None:
                        state.current_session_id = start_session()

                    record_play(track)

                    if cfg.lastfm_configured():
                        scrobble(track)
                    else:
                        logger.info("Last.fm not configured — scrobble skipped")

                else:
                    logger.info(
                        f"Dedup: skipping re-detection of "
                        f"{track.get('artist')} – {track.get('title')}"
                    )

                state.status = "playing"
                await broadcast({"status": "playing", "track": state.current_track})

            await asyncio.sleep(cfg.RETRY_DELAY)

        else:
            if silence_start is None:
                silence_start = time.time()

            silence_elapsed = int(time.time() - silence_start)
            logger.info(f"Silence: {silence_elapsed}s")

            if silence_elapsed > cfg.SILENCE_TIMEOUT and state.status != "idle":
                state.status           = "idle"
                state.current_track    = None
                state.last_norm_key    = None
                end_session(state.current_session_id)
                state.current_session_id = None
                await broadcast({"status": "idle"})

            await asyncio.sleep(1)


@app.on_event("startup")
async def startup():
    init_db()
    if cfg.lastfm_configured():
        init_network()
    else:
        logger.info("Last.fm not configured — scrobbling disabled (can be set up later)")
    if cfg.spotify_configured():
        from spotify_service import is_connected
        if is_connected():
            logger.info("Spotify connected")
        else:
            logger.info("Spotify credentials set but not yet authenticated")
    asyncio.create_task(detection_loop())
    logger.info("VinylScrobbler backend started")