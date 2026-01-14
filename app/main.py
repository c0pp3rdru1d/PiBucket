from __future__ import annotations

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .db import init_db, list_devices, upsert_devices
from .scanner import scan_lan

APP_TITLE = "LANWatch"
DEFAULT_CIDR = os.getenv("LANWATCH_CIDR", "192.168.10.0/24")
SCAN_TOKEN = os.getenv("LANWATCH_TOKEN", "")  # optional protection

app = FastAPI(title=APP_TITLE)
templates = Jinja2Templates(directory=str((__file__).rsplit("/", 2)[0] + "/templates"))

# Fix template path robustly:
from pathlib import Path
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    devices = list_devices()
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
def api_scan(token: str = ""):
    if SCAN_TOKEN and token != SCAN_TOKEN:
        raise HTTPException(status_code=401, detail="Bad token")

    devices = scan_lan(DEFAULT_CIDR, prefer_arp_scan=True)
    upsert_devices(devices)
    return {"scanned": len(devices), "cidr": DEFAULT_CIDR}

