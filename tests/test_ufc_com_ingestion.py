from datetime import date
from pathlib import Path

import requests

from ufc_quant.ingest_ufc_com import fetch_event_index, parse_event_detail, fetch_next_upcoming_event
from ufc_quant.scheduler import ingest_upcoming_card

FIXTURES = Path(__file__).parent / "fixtures"
INDEX_HTML = (FIXTURES / "ufc_event_index.html").read_text(encoding="utf-8")
DETAIL_HTML = (FIXTURES / "ufc_event_detail.html").read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return self.responses.pop(0)


def test_event_index_deduplicates_and_absolute_urls():
    session = FakeSession([FakeResponse(INDEX_HTML)])
    events = fetch_event_index(session=session)
    assert len(events) == 1
    assert events[0]["url"] == "https://www.ufc.com/event/ufc-999"


def test_parse_event_detail_returns_names_date_location_and_source_status():
    card = parse_event_detail(DETAIL_HTML, "https://www.ufc.com/event/ufc-999")
    assert card["event"]["name"] == "UFC 999: Test vs Fixture"
    assert card["event"]["date"] == "2026-12-12"
    assert card["event"]["location"] == "Las Vegas, Nevada, US"
    assert card["ingestion"]["status"] == "OK"
    assert card["ingestion"]["feature_data_status"] == "NOT_PROVIDED"
    assert [(f["fighter_a"], f["fighter_b"]) for f in card["fights"]] == [
        ("Alpha Fighter", "Beta Fighter"), ("Gamma Fighter", "Delta Fighter")]


def test_next_event_selects_nearest_future_dated_card():
    session = FakeSession([FakeResponse(INDEX_HTML), FakeResponse(DETAIL_HTML)])
    card = fetch_next_upcoming_event(session=session, today=date(2026, 11, 7))
    assert card["event"]["date"] == "2026-12-12"
    assert len(card["fights"]) == 2


def test_ingestion_saves_manifest_without_fake_features(tmp_path):
    session = FakeSession([FakeResponse(INDEX_HTML), FakeResponse(DETAIL_HTML)])
    target = tmp_path / "manifest.json"
    path, card = ingest_upcoming_card(output=target, session=session, today=date(2026, 11, 7))
    assert path == target
    loaded = __import__("json").loads(target.read_text(encoding="utf-8"))
    assert loaded["event"]["source_status"] == "SOURCE_EXTRACTED"
    assert loaded["fights"] == card["fights"]
    assert "features_a" not in loaded["fights"][0]


def test_no_parsed_fights_fails_closed():
    html = "<html><body><h1>UFC event</h1></body></html>"
    card = parse_event_detail(html, "https://www.ufc.com/event/x")
    assert card["fights"] == []
    assert card["ingestion"]["status"] == "NO_FIGHTS_PARSED"
