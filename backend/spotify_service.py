# backend/spotify_service.py
"""
Spotify integration — OAuth Authorization Code flow + like track.

Setup:
  1. Create an app at https://developer.spotify.com/dashboard
  2. Add redirect URI: http://127.0.0.1:8000/api/spotify/callback
     (or your Pi's LAN IP if you access from another device)
  3. Copy Client ID and Secret into the wizard / settings
"""
import os
from typing import Optional
from config import cfg
from logger import logger

_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".spotify_token_cache")
SCOPE = "user-library-modify user-library-read"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_oauth():
    """Build a SpotifyOAuth instance from current config."""
    from spotipy.oauth2 import SpotifyOAuth
    return SpotifyOAuth(
        client_id=cfg.SPOTIFY_CLIENT_ID,
        client_secret=cfg.SPOTIFY_CLIENT_SECRET,
        redirect_uri=cfg.SPOTIFY_REDIRECT_URI,
        scope=SCOPE,
        cache_path=_CACHE_PATH,
        open_browser=False,
        show_dialog=False,
    )


def _make_client(token_info: dict):
    import spotipy
    return spotipy.Spotify(auth=token_info["access_token"])


def _get_valid_token() -> Optional[dict]:
    """Return a fresh token dict or None if not authenticated."""
    if not cfg.spotify_configured():
        return None
    try:
        oauth = _make_oauth()
        token_info = oauth.get_cached_token()
        if not token_info:
            return None
        if oauth.is_token_expired(token_info):
            token_info = oauth.refresh_access_token(token_info["refresh_token"])
        return token_info
    except Exception as e:
        logger.error(f"Spotify token refresh failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_auth_url() -> str:
    """Return the Spotify authorization URL to redirect the user to."""
    return _make_oauth().get_authorize_url()


def handle_callback(code: str) -> bool:
    """Exchange the OAuth code for tokens. Returns True on success."""
    try:
        oauth = _make_oauth()
        token_info = oauth.get_access_token(code, as_dict=True, check_cache=False)
        if token_info:
            logger.info("Spotify: OAuth tokens obtained and cached")
            return True
        return False
    except Exception as e:
        logger.error(f"Spotify callback error: {e}")
        return False


def is_connected() -> bool:
    """True when we have a valid (or refreshable) cached token."""
    return _get_valid_token() is not None


def get_status() -> dict:
    has_creds = cfg.spotify_configured()
    connected = is_connected() if has_creds else False
    username: Optional[str] = None
    if connected:
        try:
            token = _get_valid_token()
            sp = _make_client(token)
            me = sp.me()
            username = me.get("display_name") or me.get("id")
        except Exception:
            pass
    return {
        "client_configured": has_creds,
        "connected": connected,
        "username": username,
        "redirect_uri": cfg.SPOTIFY_REDIRECT_URI,
    }


def like_track(track: dict) -> bool:
    """Search Spotify for the track and add it to the user's Liked Songs."""
    token = _get_valid_token()
    if not token:
        logger.warning("Spotify: not connected — skipping like")
        return False
    try:
        sp = _make_client(token)
        artist = track.get("artist", "")
        title  = track.get("title", "")
        query  = f"track:{title} artist:{artist}"
        results = sp.search(q=query, type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])
        if not items:
            logger.warning(f"Spotify: no match for '{artist} – {title}'")
            return False
        track_id = items[0]["id"]
        # Don't duplicate if already liked
        already = sp.current_user_saved_tracks_contains([track_id])
        if already and already[0]:
            logger.info(f"Spotify: already liked '{title}'")
            return True
        sp.current_user_saved_tracks_add([track_id])
        logger.info(f"Spotify: liked '{artist} – {title}'")
        return True
    except Exception as e:
        logger.error(f"Spotify like failed: {e}")
        return False


def disconnect() -> None:
    """Remove cached token (logout)."""
    if os.path.exists(_CACHE_PATH):
        os.remove(_CACHE_PATH)
    logger.info("Spotify: disconnected")
