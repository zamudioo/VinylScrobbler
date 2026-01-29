#ZamudioScrobbler/backend/shazam_service.py
import tempfile
import soundfile as sf
from shazamio import Shazam
from logger import logger

shazam = Shazam()

async def identify(audio, sample_rate):
    logger.info("Sending audio to Shazam…")

    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        sf.write(f.name, audio, sample_rate)

        try:
            out = await shazam.recognize(f.name)
        except Exception as e:
            logger.error(f"Shazam error: {e}")
            return None

        if not out or "track" not in out:
            logger.warning("No track identified")
            return None

        track = out["track"]

        title = track.get("title")
        artist = track.get("subtitle")

        logger.info(f"Track identified: {artist} – {title}")

        return {
            "title": title,
            "artist": artist,
            "album": (
                track.get("sections", [{}])[0]
                .get("metadata", [{}])[0]
                .get("text")
            ),
            "cover": track.get("images", {}).get("coverart")
        }
