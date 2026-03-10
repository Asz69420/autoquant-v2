"""Shared database utilities for AutoQuant scripts."""
import os
import sqlite3

ROOT = os.environ.get("AUTOQUANT_ROOT", r"C:\Users\Clamps\.openclaw\workspace-oragorn")
DB = os.path.join(ROOT, "db", "autoquant.db")


def get_connection(db_path=None, row_factory=True, timeout=30):
    """Get a SQLite connection with WAL mode and sensible defaults."""
    conn = sqlite3.connect(db_path or DB, timeout=timeout)
    if row_factory:
        conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn
