#ZamudioScrobbler/backend/stats_service.py
import sqlite3
import time
import os
from logger import logger

DB_PATH = os.path.join(os.path.dirname(__file__), "stats.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plays (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   INTEGER NOT NULL,
            artist      TEXT,
            album       TEXT,
            title       TEXT,
            genre       TEXT,
            cover_url   TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time  INTEGER NOT NULL,
            end_time    INTEGER
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Stats DB initialized")

def record_play(track: dict):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO plays (timestamp, artist, album, title, genre, cover_url)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            int(time.time()),
            track.get("artist"),
            track.get("album"),
            track.get("title"),
            track.get("genre"),
            track.get("cover"),
        ),
    )
    conn.commit()
    conn.close()
    logger.info(f"Stats: play recorded — {track.get('artist')} – {track.get('title')}")

def delete_play(play_id: int) -> bool:
    """Delete a single play entry. Returns True if a row was deleted."""
    conn = get_conn()
    cur = conn.execute("DELETE FROM plays WHERE id = ?", (play_id,))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def clear_history() -> int:
    """Delete all play entries. Returns the number of rows deleted."""
    conn = get_conn()
    cur = conn.execute("DELETE FROM plays")
    count = cur.rowcount
    conn.commit()
    conn.close()
    return count

def start_session() -> int:
    conn = get_conn()
    cur = conn.execute("INSERT INTO sessions (start_time) VALUES (?)", (int(time.time()),))
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id

def end_session(session_id: int):
    if session_id is None:
        return
    conn = get_conn()
    conn.execute(
        "UPDATE sessions SET end_time = ? WHERE id = ?",
        (int(time.time()), session_id),
    )
    conn.commit()
    conn.close()

# ── Stats queries ─────────────────────────────────────────────────────────────

def _period_cutoff(period: str) -> int:
    now = int(time.time())
    if period == "today":
        import datetime
        today = datetime.date.today()
        return int(datetime.datetime(today.year, today.month, today.day).timestamp())
    elif period == "week":
        return now - 7 * 86400
    elif period == "month":
        return now - 30 * 86400
    elif period == "year":
        return now - 365 * 86400
    else:  # all
        return 0

def get_summary(period: str = "all") -> dict:
    cutoff = _period_cutoff(period)
    conn = get_conn()

    top_artists = conn.execute(
        """
        SELECT artist, COUNT(*) as plays, cover_url
        FROM plays
        WHERE timestamp >= ? AND artist IS NOT NULL
        GROUP BY artist
        ORDER BY plays DESC
        LIMIT 10
        """,
        (cutoff,),
    ).fetchall()

    top_albums = conn.execute(
        """
        SELECT album, artist, COUNT(*) as plays, cover_url
        FROM plays
        WHERE timestamp >= ? AND album IS NOT NULL
        GROUP BY album, artist
        ORDER BY plays DESC
        LIMIT 10
        """,
        (cutoff,),
    ).fetchall()

    top_tracks = conn.execute(
        """
        SELECT title, artist, album, COUNT(*) as plays, cover_url
        FROM plays
        WHERE timestamp >= ?
        GROUP BY title, artist
        ORDER BY plays DESC
        LIMIT 10
        """,
        (cutoff,),
    ).fetchall()

    genres = conn.execute(
        """
        SELECT genre, COUNT(*) as plays
        FROM plays
        WHERE timestamp >= ? AND genre IS NOT NULL
        GROUP BY genre
        ORDER BY plays DESC
        LIMIT 8
        """,
        (cutoff,),
    ).fetchall()

    total_plays = conn.execute(
        "SELECT COUNT(*) as c FROM plays WHERE timestamp >= ?", (cutoff,)
    ).fetchone()["c"]

    sessions = conn.execute(
        """
        SELECT start_time, end_time FROM sessions
        WHERE start_time >= ? AND end_time IS NOT NULL
        """,
        (cutoff,),
    ).fetchall()
    total_seconds = sum(s["end_time"] - s["start_time"] for s in sessions)

    conn.close()

    return {
        "period":       period,
        "total_plays":  total_plays,
        "total_seconds": total_seconds,
        "top_artists":  [dict(r) for r in top_artists],
        "top_albums":   [dict(r) for r in top_albums],
        "top_tracks":   [dict(r) for r in top_tracks],
        "genres":       [dict(r) for r in genres],
    }

def get_history(page: int = 1, limit: int = 50) -> dict:
    offset = (page - 1) * limit
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, timestamp, artist, album, title, genre, cover_url
        FROM plays
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) as c FROM plays").fetchone()["c"]
    conn.close()
    return {
        "page":  page,
        "limit": limit,
        "total": total,
        "plays": [dict(r) for r in rows],
    }