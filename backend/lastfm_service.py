#ZamudioScrobbler/backend/lastfm_service.py
import pylast
from config import (
    LASTFM_API_KEY,
    LASTFM_API_SECRET,
    LASTFM_USERNAME,
    LASTFM_PASSWORD_HASH
)
from logger import logger

network = pylast.LastFMNetwork(
    api_key=LASTFM_API_KEY,
    api_secret=LASTFM_API_SECRET,
    username=LASTFM_USERNAME,
    password_hash=LASTFM_PASSWORD_HASH,
)

def scrobble(track):
    try:
        network.scrobble(
            artist=track["artist"],
            title=track["title"],
            timestamp=int(__import__("time").time())
        )
        logger.info("Scrobbled to Last.fm")
    except Exception as e:
        logger.error(f"Scrobble failed: {e}")
