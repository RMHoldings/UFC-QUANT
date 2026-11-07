"""UFC.com event index and fight-card ingestion.

The UFC site is dynamic and its markup may change. This adapter extracts only
source-visible event metadata and matchup names. It intentionally does not infer
fighter features, odds, or forecast inputs.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = "https://www.ufc.com/events"
USER_AGENT = "UFCQuantResearch/0.2 (event-card metadata; respectful requests)"


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _fetch(url: str, session=None, timeout=20):
    session = session or requests.Session()
    response = session.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.text


def fetch_event_index(session=None, timeout=20):
    html = _fetch(URL, session=session, timeout=timeout)
    soup = BeautifulSoup(html, "lxml")
    events = []
    for anchor in soup.select("a[href*='/event/']"):
        title = _clean(anchor.get_text(" ", strip=True))
        href = anchor.get("href", "")
        if title and href:
            absolute = urljoin(URL, href)
            if "/event/" in absolute:
                events.append({"title": title, "url": absolute, "source": URL})
    seen = set()
    unique = []
    for event in events:
        key = event["url"].split("#", 1)[0]
        if key not in seen:
            seen.add(key)
            unique.append(event)
    return unique


def _event_date(soup, json_ld_objects):
    candidates = []
    for obj in json_ld_objects:
        if isinstance(obj, dict):
            if obj.get("startDate"):
                candidates.append(str(obj["startDate"]))
            graph = obj.get("@graph")
            if isinstance(graph, list):
                candidates.extend(str(x["startDate"]) for x in graph if isinstance(x, dict) and x.get("startDate"))
    meta = soup.select_one('meta[property="article:published_time"], meta[name="date"]')
    if meta and meta.get("content"):
        candidates.append(meta["content"])
    for value in candidates:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            try:
                return date.fromisoformat(value[:10]).isoformat()
            except ValueError:
                continue
    # Explicit UFC event date labels in the rendered page, without guessing formats.
    for selector in (".field--name-field-event-date", ".event-date", "time[datetime]"):
        node = soup.select_one(selector)
        if node:
            value = node.get("datetime") or node.get_text(" ", strip=True)
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                continue
    return None


def _json_ld(soup):
    parsed = []
    for node in soup.select('script[type="application/ld+json"]'):
        raw = node.string or node.get_text()
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, list):
            parsed.extend(value)
        else:
            parsed.append(value)
    return parsed


def _fight_groups(soup):
    # Prefer explicit fight-card wrappers to avoid grouping arbitrary athlete links.
    selectors = (
        ".c-listing-fight",
        ".fight-card",
        ".fight-card__fight",
        "[class*='listing-fight']",
    )
    groups = []
    seen_nodes = set()
    for selector in selectors:
        nodes = soup.select(selector)
        if nodes:
            for node in nodes:
                identity = id(node)
                if identity not in seen_nodes:
                    seen_nodes.add(identity)
                    groups.append(node)
            if groups:
                break
    fights = []
    seen_matchups = set()
    for group in groups:
        names = []
        for anchor in group.select("a[href*='/athlete/']"):
            name = _clean(anchor.get_text(" ", strip=True))
            if name and name not in names:
                names.append(name)
        if len(names) < 2:
            # Some versions expose fighter names in corner-name elements without links.
            for node in group.select(".c-listing-fight__corner-name, .fight-card__fighter-name"):
                name = _clean(node.get_text(" ", strip=True))
                if name and name not in names:
                    names.append(name)
        if len(names) != 2:
            continue
        key = tuple(sorted(names, key=str.casefold))
        if key in seen_matchups:
            continue
        seen_matchups.add(key)
        division_node = group.select_one(".c-listing-fight__class, .fight-card__class, .weight-class")
        division = _clean(division_node.get_text(" ", strip=True)) if division_node else None
        fights.append({"fighter_a": names[0], "fighter_b": names[1], "division": division})
    return fights


def parse_event_detail(html: str, event_url: str, fallback_title: str | None = None):
    soup = BeautifulSoup(html, "lxml")
    ld = _json_ld(soup)
    title_node = soup.select_one("h1")
    title = _clean(title_node.get_text(" ", strip=True)) if title_node else (fallback_title or "")
    if not title:
        title = fallback_title or "UFC event (title unavailable)"
    location = None
    for obj in ld:
        if isinstance(obj, dict):
            place = obj.get("location")
            if isinstance(place, dict):
                address = place.get("address")
                if isinstance(address, dict):
                    location = ", ".join(filter(None, [address.get("addressLocality"), address.get("addressRegion"), address.get("addressCountry")])) or None
                elif isinstance(address, str):
                    location = address
    fights = _fight_groups(soup)
    return {
        "event": {
            "name": title,
            "date": _event_date(soup, ld),
            "location": location,
            "source_status": "SOURCE_EXTRACTED",
            "source_url": event_url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "fights": fights,
        "ingestion": {
            "source": "UFC.com",
            "fight_count": len(fights),
            "status": "OK" if fights else "NO_FIGHTS_PARSED",
            "feature_data_status": "NOT_PROVIDED",
            "notes": "Matchups are extracted from UFC.com page markup. Fighter model features, odds, and outcomes are not inferred.",
        },
    }


def fetch_event_detail(event, session=None, timeout=20):
    html = _fetch(event["url"], session=session, timeout=timeout)
    return parse_event_detail(html, event["url"], fallback_title=event.get("title"))


def fetch_next_upcoming_event(session=None, timeout=20, today=None):
    """Fetch event index and select the nearest event with a parseable future date/card."""
    today = today or date.today()
    index = fetch_event_index(session=session, timeout=timeout)
    candidates = []
    errors = []
    for item in index:
        try:
            card = fetch_event_detail(item, session=session, timeout=timeout)
            event_date = card["event"].get("date")
            if event_date and date.fromisoformat(event_date) >= today and card["fights"]:
                candidates.append((date.fromisoformat(event_date), card))
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{item.get('url')}: {exc}")
    if not candidates:
        detail = "; ".join(errors[:3])
        raise RuntimeError("Could not identify a dated upcoming event with parsed fights." + (f" Details: {detail}" if detail else ""))
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]
