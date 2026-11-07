"""Weekly Saturday 09:00 Europe/Rome card-ingestion scheduler."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

LOGGER = logging.getLogger("ufc_quant.scheduler")


def ingest_upcoming_card(output="upcoming_event_card.json", session=None, today=None):
    """Save a source-backed fight-card manifest. Does not forecast without features."""
    from .ingest_ufc_com import fetch_next_upcoming_event

    card = fetch_next_upcoming_event(session=session, today=today)
    if not card.get("fights"):
        raise RuntimeError("Ingested event has no parsed matchups; refusing to write empty card.")
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path, card


def run_scheduler(output="upcoming_event_card.json"):
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError as exc:
        raise SystemExit("Install apscheduler to enable scheduling: pip install apscheduler") from exc

    def job():
        try:
            path, card = ingest_upcoming_card(output=output)
            LOGGER.info("Saved %s (%d matchups) to %s. Forecast skipped: fighter features not available.",
                       card["event"]["name"], len(card["fights"]), path)
        except Exception:
            LOGGER.exception("Scheduled UFC event ingestion failed; no forecast was generated.")

    scheduler = BlockingScheduler(timezone=ZoneInfo("Europe/Rome"))
    scheduler.add_job(job, "cron", day_of_week="sat", hour=9, minute=0,
                      id="ufc_upcoming_card_ingestion", replace_existing=True,
                      max_instances=1, coalesce=True)
    LOGGER.info("Scheduler running Saturday 09:00 Europe/Rome; output=%s", output)
    scheduler.start()
