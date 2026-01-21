from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "pibucket.sqlite3"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                ip TEXT PRIMARY KEY,
                mac TEXT,
                vendor TEXT,
                hostname TEXT,
                first_seen TEXT,
                last_seen TEXT,
                seen_count INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_devices(devices: list[dict[str, Any]]) -> None:
    now = _now_iso()
    with _connect() as conn:
        for d in devices:
            ip = d.get("ip")
            if not ip:
                continue

            mac = d.get("mac")
            vendor = d.get("vendor")
            hostname = d.get("hostname")

            row = conn.execute("SELECT * FROM devices WHERE ip = ?", (ip,)).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO devices (ip, mac, vendor, hostname, first_seen, last_seen, seen_count)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (ip, mac, vendor, hostname, now, now),
                )
            else:
                new_mac = mac or row["mac"]
                new_vendor = vendor or row["vendor"]
                new_hostname = hostname or row["hostname"]
                conn.execute(
                    """
                    UPDATE devices
                    SET mac=?, vendor=?, hostname=?, last_seen=?, seen_count=seen_count+1
                    WHERE ip=?
                    """,
                    (new_mac, new_vendor, new_hostname, now, ip),
                )
        conn.commit()


def list_devices(limit: int = 500) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT ip, mac, vendor, hostname, first_seen, last_seen, seen_count
            FROM devices
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]

