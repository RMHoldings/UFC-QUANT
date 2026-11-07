"""UFCStats public-page ingestion helpers. Respect robots.txt, rate limits and source terms.
No API key is required. Data remains attributed to UFCStats.
"""
from __future__ import annotations
import re, time, logging
from dataclasses import dataclass, asdict
from typing import Optional
import requests
from bs4 import BeautifulSoup

BASE = "http://www.ufcstats.com"
EVENTS_URL = f"{BASE}/statistics/events"
HEADERS = {"User-Agent": "UFCQuantResearch/0.1 (public research; contact: configured by operator)"}
log = logging.getLogger(__name__)

@dataclass
class Event:
    name: str
    date: str
    location: str
    url: str
    status: str = "listed"

@dataclass
class Bout:
    event_name: str
    red_name: str
    blue_name: str
    red_url: str
    blue_url: str
    fight_url: str
    result: str = ""
    method: str = ""
    round: str = ""
    time: str = ""

@dataclass
class FighterStats:
    name: str
    url: str
    record: str = ""
    height: str = ""
    weight: str = ""
    reach: str = ""
    stance: str = ""
    dob: str = ""
    slpm: Optional[float] = None
    str_acc: Optional[float] = None
    sapm: Optional[float] = None
    str_def: Optional[float] = None
    td_avg: Optional[float] = None
    td_acc: Optional[float] = None
    td_def: Optional[float] = None
    sub_avg: Optional[float] = None

class UFCStatsClient:
    def __init__(self, delay_seconds=1.5, timeout=20, session=None):
        self.delay = max(1.0, float(delay_seconds))
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)

    def get_soup(self, url):
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        time.sleep(self.delay)
        return BeautifulSoup(response.text, "lxml")

    @staticmethod
    def _cell(row, idx):
        cells = row.find_all("td")
        return cells[idx].get_text(" ", strip=True) if idx < len(cells) else ""

    def events(self, page=1):
        url = EVENTS_URL if page == 1 else f"{EVENTS_URL}?page={page}"
        soup = self.get_soup(url)
        out=[]
        for row in soup.select("tr.b-fight-details__table-row"):
            link=row.select_one("a.b-link")
            if not link: continue
            cells=row.find_all("td")
            out.append(Event(
                name=link.get_text(" ",strip=True),
                date=self._cell(row,0),
                location=self._cell(row,1),
                url=link.get("href",""),
            ))
        return out

    def event_bouts(self, event_url):
        soup=self.get_soup(event_url)
        event_name=(soup.select_one("h2.b-content__title") or soup.title)
        event_name=event_name.get_text(" ",strip=True) if event_name else event_url
        bouts=[]
        for row in soup.select("tr.b-fight-details__table-row"):
            links=row.select("a.b-link")
            fight=row.select_one("a[href*='fight-details']")
            if len(links)<2: continue
            fight_url=fight.get("href","") if fight else ""
            result=self._cell(row,0)
            bouts.append(Bout(
                event_name=event_name,
                red_name=links[0].get_text(" ",strip=True),
                blue_name=links[1].get_text(" ",strip=True),
                red_url=links[0].get("href",""),
                blue_url=links[1].get("href",""),
                fight_url=fight_url,
                result=result,
                method=self._cell(row,7),
                round=self._cell(row,8),
                time=self._cell(row,9),
            ))
        return bouts

    @staticmethod
    def _number(text):
        text=(text or "").strip().replace("%","")
        try: return float(text)
        except (TypeError,ValueError): return None

    def fighter(self, fighter_url):
        soup=self.get_soup(fighter_url)
        title=soup.select_one("span.b-content__title-highlight")
        record=soup.select_one("span.b-content__title-record")
        bio={}
        for item in soup.select("ul.b-list__box li"):
            label=item.select_one("i.b-list__label")
            if label:
                key=label.get_text(" ",strip=True).rstrip(":").lower()
                value=item.get_text(" ",strip=True).replace(label.get_text(" ",strip=True),"",1).strip()
                bio[key]=value
        stats={}
        for item in soup.select("div.b-list__info-box li"):
            label=item.select_one("i.b-list__label")
            if label:
                key=label.get_text(" ",strip=True).rstrip(":").lower()
                val=item.get_text(" ",strip=True).replace(label.get_text(" ",strip=True),"",1).strip()
                stats[key]=val
        get=lambda key: stats.get(key)
        return FighterStats(
            name=title.get_text(" ",strip=True) if title else "",
            url=fighter_url,
            record=record.get_text(" ",strip=True) if record else "",
            height=bio.get("height",""), weight=bio.get("weight",""),
            reach=bio.get("reach",""), stance=bio.get("stance",""),
            dob=bio.get("dob",""),
            slpm=self._number(get("slpm")),
            str_acc=self._number(get("str. acc.")),
            sapm=self._number(get("sapm")),
            str_def=self._number(get("str. def")),
            td_avg=self._number(get("td avg.")),
            td_acc=self._number(get("td acc.")),
            td_def=self._number(get("td def.")),
            sub_avg=self._number(get("sub. avg.")),
        )

def main_card_bouts(bouts, main_card_count=5):
    """UFCStats event order is generally prelim-to-main; operator should verify card labels.
    This intentionally does not guess from bout order: return all and mark main-card selection
    as requiring card source validation.
    """
    return {"bouts": [asdict(b) for b in bouts],
            "main_card_selection": "needs_ufc_com_event_card_confirmation",
            "source": "UFCStats"}
