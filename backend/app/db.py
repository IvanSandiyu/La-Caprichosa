import sqlite3
import threading

from .config import DB_PATH

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        if not DB_PATH.exists():
            raise FileNotFoundError(
                f"No existe {DB_PATH}. Corré primero: python pipeline/build_dataset.py"
            )
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn
