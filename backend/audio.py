# backend/audio.py
import sounddevice as sd
import numpy as np
from config import cfg
from logger import logger


def record_chunk():
    frames = int(cfg.SAMPLE_RATE * cfg.CHUNK_SECONDS)
    audio = sd.rec(
        frames,
        samplerate=cfg.SAMPLE_RATE,
        channels=1,
        device=cfg.AUDIO_DEVICE_INDEX,
        dtype="float32",
    )
    sd.wait()
    return audio.flatten()


def has_audio(signal) -> bool:
    rms = float(np.sqrt(np.mean(signal ** 2)))
    logger.info(f"RMS level: {rms:.4f}")
    if rms > cfg.VOLUME_THRESHOLD:
        logger.info("Audio detected")
        return True
    logger.info("No audio detected")
    return False
