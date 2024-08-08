import sqlite3
from pathlib import Path
from flask import g

# TODO: envvars
APP_DATABASE = Path("./app.db")


def get_db():
    db = getattr(g, "_app_database", None)
    if db is None:
        db = g._database = sqlite3.connect(APP_DATABASE)
        db.row_factory = sqlite3.Row
    return db


def close_db(e=None):
    db = getattr(g, "_app_database", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(APP_DATABASE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                node_id TEXT,
                device_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )


def add_visit(endpoint, node_id, device_id):
    db = get_db()
    db.execute(
        "INSERT INTO visits (endpoint, node_id, device_id) VALUES (?, ?, ?)",
        (endpoint, node_id, device_id),
    )
    db.commit()


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
