# backend/shazam_service.py
import tempfile
import soundfile as sf
from shazamio import Shazam
from config import cfg
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

        # ── Confidence gate ───────────────────────────────────────────────
        matches = out.get("matches", [])
        min_matches = cfg.SHAZAM_MIN_MATCHES        # default 1
        if len(matches) < min_matches:
            logger.warning(
                f"Shazam: only {len(matches)} match(es) — below min {min_matches}, skipping"
            )
            return None

        track = out["track"]
        result = {
            "title":        track.get("title"),
            "artist":       track.get("subtitle"),
            "album":        _extract_album(track),
            "genre":        _extract_genre(track),
            "cover":        track.get("images", {}).get("coverart"),
            "match_count":  len(matches),    # expose for logging / future use
        }

        logger.info(
            f"Track identified ({len(matches)} match{'es' if len(matches)!=1 else ''}): "
            f"{result['artist']} – {result['title']}"
        )
        return result
