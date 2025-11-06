from __future__ import annotations
import sqlite3, pathlib, datetime as dt
from typing import Optional, Iterable, Dict, Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  guid TEXT NOT NULL,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  published TIMESTAMP NULL,
  first_seen TIMESTAMP NOT NULL,
  UNIQUE(source, guid)
);
"""

def connect(db_path: pathlib.Path) -> sqlite3.Connection:
  db_path.parent.mkdir(parents=True, exist_ok=True)
  con = sqlite3.connect(str(db_path))
  con.execute("PRAGMA journal_mode=WAL;")
  con.execute("PRAGMA synchronous=NORMAL;")
  con.execute("PRAGMA foreign_keys=ON;")
  con.executescript(SCHEMA)
  return con

def upsert_items(con: sqlite3.Connection, rows: Iterable[Dict[str, Any]]) -> int:
  cur = con.cursor()
  n = 0
  for r in rows:
    cur.execute(
      """
      INSERT OR IGNORE INTO items (source, guid, url, title, published, first_seen)
      VALUES (?, ?, ?, ?, ?, ?)
      """,
      (
        r["source"],
        r["guid"],
        r["url"],
        r["title"],
        r["published"],
        r["first_seen"],
      ),
    )
    n += cur.rowcount if cur.rowcount is not None else 0
  con.commit()
  return n

def select_since(con: sqlite3.Connection, since: dt.datetime) -> list[dict]:
  cur = con.cursor()
  cur.execute(
    """
    SELECT source, guid, url, title, published, first_seen
    FROM items
    WHERE COALESCE(published, first_seen) >= ?
    ORDER BY COALESCE(published, first_seen) DESC
    """,
    (since,),
  )
  cols = [c[0] for c in cur.description]
  out = [dict(zip(cols, row)) for row in cur.fetchall()]
  # Cast timestamps back to datetime
  for r in out:
    for k in ["published", "first_seen"]:
      if isinstance(r[k], str):
        try:
          r[k] = dt.datetime.fromisoformat(r[k])
        except Exception:
          pass
  return out
