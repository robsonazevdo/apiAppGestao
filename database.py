import sqlite3
from flask import g

DB_PATH = "database.db"

def get_db():
    if "db" not in g:
        conn = sqlite3.connect(
            DB_PATH,
            timeout=10,
        )
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def close_connection(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
