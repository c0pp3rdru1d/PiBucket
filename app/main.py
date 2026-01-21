from __future__ import annotations

import os
import socket
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .db import init_db, list_devices, upsert_devices
from .scanner import scan_lan
from .vendor import VendorLookup

APP_TITLE = "PiBucket"
DEFAULT_CIDR = os.getenv("LANWATCH_CIDR", "10.10.25.0/28")

ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))
manuf_path = ROOT / "data" / "manuf"
vendors = VendorLookup(mapping={})

app = FastAPI(title=APP_TITLE)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    global vendors
    vendors = VendorLookup.from_manuf(manuf_path)


def _hostname_for_ip(ip: str) -> str | None:
    # Best-effort reverse lookup (won't always work)
    try:
        name, *_ = socket.gethostbyaddr(ip)
        return name
    except Exception:
        return None


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    devices = list_devices(limit=500)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": APP_TITLE,
            "cidr": DEFAULT_CIDR,
            "devices": devices,
            "count": len(devices),
        },
    )


@app.get("/api/devices", response_class=JSONResponse)
def api_devices(limit: int = 500):
    return list_devices(limit=limit)


@app.post("/api/scan", response_class=JSONResponse)
def api_scan():
    found = scan_lan(DEFAULT_CIDR)

    # Attach vendor + optional hostname
    for d in found:
        mac = d.get("mac")
        d["vendor"] = vendors.vendor_for(mac) or ""
        d["hostname"] = _hostname_for_ip(d["ip"]) or ""

    upsert_devices(found)
    return {"cidr": DEFAULT_CIDR, "scanned": len(found)}

