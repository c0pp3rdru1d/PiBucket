from __future__ import annotations

import ipaddress
import re
import socket
import subprocess
from datetime import datetime, timezone
from typing import Iterable


_NEIGH_RE = re.compile(
    r"^(?P<ip>\d+\.\d+\.\d+\.\d+)\s+dev\s+(?P<dev>\S+)\s+lladdr\s+(?P<mac>[0-9a-f:]{17})\s+(?P<state>\S+)"
)


def _run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout


def _ping_sweep(cidr: str, count: int = 1, timeout_s: int = 1) -> None:
    """
    Ping each host to populate ARP/neighbor table.
    This is “cheap and cheerful” and works on a Pi 3.
    """
    net = ipaddress.ip_network(cidr, strict=False)
    for ip in net.hosts():
        subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout_s), str(ip)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _read_ip_neigh() -> Iterable[dict]:
    """
    Parses: ip neigh show
    """
    out = _run(["ip", "neigh", "show"])
    for line in out.splitlines():
        m = _NEIGH_RE.match(line.strip().lower())
        if not m:
            continue
        state = m.group("state")
        # ignore incomplete entries
        if state in {"incomplete", "failed"}:
            continue
        yield {
            "ip": m.group("ip"),
            "mac": m.group("mac"),
        }


def _try_hostname(ip: str) -> str | None:
    try:
        name, _, _ = socket.gethostbyaddr(ip)
        return name
    except Exception:
        return None


def scan_lan(cidr: str, prefer_arp_scan: bool = True) -> list[dict]:
    """
    Returns list of dicts with: ip, mac, hostname, seen_at
    """
    seen_at = datetime.now(timezone.utc).isoformat()

    devices: list[dict] = []

    # If arp-scan is installed, it’s usually better/faster on LAN.
    if prefer_arp_scan:
        try:
            out = _run(["sudo", "arp-scan", "--localnet"])
            # arp-scan output lines usually: IP<TAB>MAC<TAB>vendor
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].count(".") == 3 and ":" in parts[1]:
                    ip = parts[0]
                    mac = parts[1].lower()
                    hostname = _try_hostname(ip)
                    devices.append({"ip": ip, "mac": mac, "hostname": hostname, "seen_at": seen_at})
            if devices:
                return devices
        except Exception:
            # fall back to ping+ip neigh
            pass

    _ping_sweep(cidr)
    for row in _read_ip_neigh():
        ip = row["ip"]
        mac = row["mac"]
        hostname = _try_hostname(ip)
        devices.append({"ip": ip, "mac": mac, "hostname": hostname, "seen_at": seen_at})

    return devices

