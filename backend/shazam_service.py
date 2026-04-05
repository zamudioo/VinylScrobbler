#ZamudioScrobbler/backend/shazam_service.py
import tempfile
import soundfile as sf
from shazamio import Shazam
from logger import logger

shazam = Shazam()

def _extract_album(track: dict) -> str | None:
    for section in track.get("sections", []):
        if section.get("type") == "SONG":
            for item in section.get("metadata", []):
                if item.get("title", "").lower() == "album":
                    return item.get("text")
    return None

def _extract_genre(track: dict) -> str | None:
    # Primary genre lives at track.genres.primary
    return track.get("genres", {}).get("primary")

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

        result = {
            "title":  track.get("title"),
            "artist": track.get("subtitle"),
            "album":  _extract_album(track),
            "genre":  _extract_genre(track),
            "cover":  track.get("images", {}).get("coverart"),
        }

        logger.info(f"Track identified: {result['artist']} – {result['title']} [{result['genre']}]")
        return result
