# backend/lastfm_service.py
import pylast
from config import cfg
from logger import logger

_network: "pylast.LastFMNetwork | None" = None


def init_network() -> None:
    global _network
    if not cfg.lastfm_configured():
        _network = None
        logger.warning("Last.fm not configured — scrobbling disabled")
        return
    try:
        _network = pylast.LastFMNetwork(
            api_key=cfg.LASTFM_API_KEY,
            api_secret=cfg.LASTFM_API_SECRET,
            username=cfg.LASTFM_USERNAME,
            password_hash=cfg.LASTFM_PASSWORD_HASH,
        )
        logger.info(f"Last.fm connected as @{cfg.LASTFM_USERNAME}")
    except Exception as e:
        _network = None
        logger.error(f"Last.fm init failed: {e}")


def get_network():
    return _network


def update_now_playing(track: dict) -> None:
    """Send 'Now Playing' update to Last.fm (shows on your profile in real-time)."""
    net = get_network()
    if net is None:
        return
    try:
        net.update_now_playing(
            artist=track["artist"],
            title=track["title"],
            album=track.get("album") or "",
        )
        logger.info("Last.fm: Now Playing updated")
    except Exception as e:
        logger.error(f"Last.fm Now Playing failed: {e}")


def scrobble(track: dict) -> None:
    net = get_network()
    if net is None:
        logger.warning("Scrobble skipped — Last.fm not connected")
        return
    try:
        import time
        # Update Now Playing first
        update_now_playing(track)
        net.scrobble(
            artist=track["artist"],
            title=track["title"],
            timestamp=int(time.time()),
            album=track.get("album") or "",
        )
        logger.info("Scrobbled to Last.fm")
    except Exception as e:
        logger.error(f"Scrobble failed: {e}")


def test_credentials(api_key: str, api_secret: str,
                     username: str, password_hash: str) -> dict:
    try:
        net = pylast.LastFMNetwork(
            api_key=api_key,
            api_secret=api_secret,
            username=username,
            password_hash=password_hash,
        )
        net.get_user(username).get_playcount()
        return {"ok": True}
    except pylast.WSError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"Connection error: {e}"}
