from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

DB_PATH = Path(__file__).resolve().parent.parent / "lanwatch.sqlite3"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                ip TEXT NOT NULL,
                mac TEXT NOT NULL,
                hostname TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                seen_count INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (ip, mac)
            )
            """
        )
        conn.commit()


def upsert_devices(rows: Iterable[dict]) -> None:
    """
    rows: dicts with keys: ip, mac, hostname, seen_at (ISO8601 string)
    """
    with connect() as conn:
        for r in rows:
            ip = r["ip"]
            mac = r["mac"]
            hostname = r.get("hostname")
            seen_at = r["seen_at"]

            existing = conn.execute(
                "SELECT seen_count FROM devices WHERE ip=? AND mac=?",
                (ip, mac),
            ).fetchone()

            if existing is None:
                conn.execute(
                    """
                    INSERT INTO devices (ip, mac, hostname, first_seen, last_seen, seen_count)
                    VALUES (?, ?, ?, ?, ?, 1)
                    """,
                    (ip, mac, hostname, seen_at, seen_at),
                )
            else:
                conn.execute(
                    """
                    UPDATE devices
                    SET hostname = COALESCE(?, hostname),
                        last_seen = ?,
                        seen_count = seen_count + 1
                    WHERE ip=? AND mac=?
                    """,
                    (hostname, seen_at, ip, mac),
                )

        conn.commit()


def list_devices(limit: int = 500) -> list[dict]:
    with connect() as conn:
        cur = conn.execute(
            """
            SELECT ip, mac, hostname, first_seen, last_seen, seen_count
            FROM devices
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]

