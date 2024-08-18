import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor

from flask import g, current_app


def get_db():
    db = getattr(g, "_app_database", None)
    if db is None:
        db = g._app_database = sqlite3.connect(str(current_app.config["APP_DB"]))
        db.row_factory = sqlite3.Row
    return db


def close_db(exception=None):
    db = getattr(g, "_app_database", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(str(current_app.config["APP_DB"])) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                device_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )


def get_popular_nodes(limit=10):
    db = get_db()
    cursor = db.execute(
        """
        SELECT node_id, COUNT(*) as visit_count
        FROM visits
        WHERE node_id IS NOT NULL
        GROUP BY node_id
        ORDER BY visit_count DESC
        LIMIT ?
    """,
        (limit,),
    )
    return cursor.fetchall()


def get_history(limit=10):
    db = get_db()
    cursor = db.execute(
        """
        SELECT node_id
        FROM visits
        WHERE node_id IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (limit,),
    )
    return cursor.fetchall()


def get_user_history(device_id, limit=20):
    db = get_db()
    cursor = db.execute(
        """
        SELECT node_id, timestamp
        FROM visits
        WHERE device_id = ? AND node_id IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT ?
    """,
        (device_id, limit),
    )
    return cursor.fetchall()
