from __future__ import annotations

import ipaddress
import subprocess
from typing import Any


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return (p.stdout or "") + (p.stderr or "")


def _ping_sweep(cidr: str) -> None:
    # For /28 (16 addresses), this is fast enough and fills ARP/neigh tables.
    net = ipaddress.ip_network(cidr, strict=False)
    for ip in net.hosts():
        subprocess.run(
            ["ping", "-c", "1", "-W", "1", str(ip)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _read_ip_neigh() -> list[dict[str, str]]:
    out = _run(["ip", "neigh", "show"])
    rows: list[dict[str, str]] = []
    # Example: "10.10.25.3 dev wlan0 lladdr aa:bb:cc:dd:ee:ff REACHABLE"
    for line in out.splitlines():
        parts = line.split()
        if not parts or parts[0].startswith("fe80:"):
            continue
        ip = parts[0]
        mac = None
        if "lladdr" in parts:
            i = parts.index("lladdr")
            if i + 1 < len(parts):
                mac = parts[i + 1]
        if mac:
            rows.append({"ip": ip, "mac": mac})
    return rows


def _read_proc_arp() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    try:
        with open("/proc/net/arp", "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 4:
                ip = parts[0]
                mac = parts[3]
                if mac and mac != "00:00:00:00:00:00":
                    rows.append({"ip": ip, "mac": mac})
    except Exception:
        pass
    return rows


def scan_lan(cidr: str) -> list[dict[str, Any]]:
    _ping_sweep(cidr)

    # Prefer ip neigh; fallback to /proc/net/arp
    rows = _read_ip_neigh()
    if not rows:
        rows = _read_proc_arp()

    # Filter to requested subnet
    net = ipaddress.ip_network(cidr, strict=False)
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            ip = ipaddress.ip_address(r["ip"])
            if ip in net:
                out.append({"ip": r["ip"], "mac": r.get("mac")})
        except Exception:
            continue
    # de-dupe by IP
    seen = set()
    uniq = []
    for d in out:
        if d["ip"] in seen:
            continue
        seen.add(d["ip"])
        uniq.append(d)
    return uniq

