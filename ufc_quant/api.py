"""FastAPI adapter for the UFCQuant web dashboard.

Live event data is fetched on-demand from the existing UFC.com adapter. The demo
report is explicitly synthetic and must not be represented as a real forecast.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
SAMPLE_CARD_PATH = ROOT / "sample_card.json"

app = FastAPI(title="UFCQuant API", version="1.0.0", description="API adapter for UFCQuant research dashboard")

allowed_origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ufcquant-api", "version": app.version}


@app.get("/api/events/upcoming")
def upcoming_event() -> dict[str, Any]:
    try:
        from .ingest_ufc_com import fetch_next_upcoming_event
        card = fetch_next_upcoming_event(timeout=float(os.getenv("UFC_SOURCE_TIMEOUT", "20")))
        if not isinstance(card, dict) or not isinstance(card.get("event"), dict) or not isinstance(card.get("fights"), list):
            raise ValueError("The UFC source adapter returned an unexpected card schema")
        if any(not isinstance(fight, dict) for fight in card["fights"]):
            raise ValueError("The UFC source adapter returned an invalid fight row")
        return {"source_status": "live", "source": "UFC.com", "event": card["event"], "fights": card["fights"]}
    except Exception as exc:
        # Avoid exposing stack traces, internal paths, or raw exception details via public API.
        raise HTTPException(status_code=502, detail=f"Unable to retrieve a verified upcoming UFC card ({type(exc).__name__}).") from exc


@app.get("/api/demo-report", response_class=Response)
def demo_report() -> Response:
    try:
        card = json.loads(SAMPLE_CARD_PATH.read_text(encoding="utf-8"))
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        from .report import build_report
        html = build_report(card, config)
        # Make the synthetic/demo status unmistakable in the page title.
        html = html.replace("UFC Main Card Quantitative Report", "UFCQuant — DEMO REPORT (synthetic inputs)")
        return Response(content=html, media_type="text/html; charset=utf-8")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Demo report generation failed ({type(exc).__name__}).") from exc
