#ZamudioScrobbler/backend/main.py
import asyncio
import time
from fastapi import FastAPI, WebSocket
from audio import record_chunk, has_audio
from shazam_service import identify
from lastfm_service import scrobble
from state import state
from config import SAMPLE_RATE, RETRY_DELAY, SILENCE_TIMEOUT, MONITOR_IDLE_SECONDS
from logger import logger
from monitor_service import turn_off_monitor, turn_on_monitor

app = FastAPI()
clients = set()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    logger.info("WebSocket connected")

    try:
        while True:
            await asyncio.sleep(1)
    except Exception:
        pass
    finally:
        clients.discard(ws)
        logger.info("WebSocket disconnected")


async def broadcast(data):
    if not clients:
        return

    dead = []
    for ws in clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)

    for ws in dead:
        clients.discard(ws)



async def detection_loop():
    silence_start = None

    while True:
        audio = record_chunk()

        if has_audio(audio):
            silence_start = None
            state.idle_started_at = None

            track = await identify(audio, SAMPLE_RATE)
            if track:
                if not state.monitor_on:
                    turn_on_monitor()
                    state.monitor_on = True

                if state.current_track != track:
                    state.current_track = track
                    scrobble(track)

                state.status = "playing"
                await broadcast({
                    "status": "playing",
                    "track": track
                })

            await asyncio.sleep(RETRY_DELAY)

        else:
            if silence_start is None:
                silence_start = time.time()
                state.idle_started_at = time.time()

            silence_elapsed = int(time.time() - silence_start)
            idle_elapsed = int(time.time() - state.idle_started_at)

            logger.info(
                f"Silence {silence_elapsed}s | Idle {idle_elapsed}s"
            )

            if silence_elapsed > SILENCE_TIMEOUT:
                if state.status != "idle":
                    state.status = "idle"
                    state.current_track = None
                    await broadcast({"status": "idle"})

            if (
                idle_elapsed >= MONITOR_IDLE_SECONDS
                and state.monitor_on
            ):
                turn_off_monitor()
                state.monitor_on = False

            await asyncio.sleep(1)

@app.on_event("startup")
async def startup():
    asyncio.create_task(detection_loop())
