#ZamudioScrobbler/backend/audio.py
import sounddevice as sd
import numpy as np
from config import (
    SAMPLE_RATE,
    CHUNK_SECONDS,
    VOLUME_THRESHOLD,
    AUDIO_DEVICE_INDEX
)
from logger import logger

def record_chunk():
    frames = int(SAMPLE_RATE * CHUNK_SECONDS)

    audio = sd.rec(
        frames,
        samplerate=SAMPLE_RATE,
        channels=1,
        device=AUDIO_DEVICE_INDEX,
        dtype="float32"
    )

    sd.wait()
    return audio.flatten()

def has_audio(signal):
    rms = np.sqrt(np.mean(signal ** 2))
    logger.info(f"RMS level: {rms:.4f}")

    if rms > VOLUME_THRESHOLD:
        logger.info("Audio detected")
        return True
    else:
        logger.info("No audio detected")
        return False
