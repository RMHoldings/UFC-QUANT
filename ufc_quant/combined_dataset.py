"""Normalize a combined UFC results + historical-odds CSV into model and odds inputs.

Supports the public ``complete_ufc_data.csv`` style schema. Outcomes are accepted
only from explicit labels; ambiguous/unknown result labels are excluded rather than
inferred from fighter ordering. Historical prices are emitted only when both decimal
odds are present and valid.
"""
from __future__ import annotations
import argparse, csv, json
from collections import Counter
from datetime import datetime
from pathlib import Path

DATE_KEYS = ("event_date", "date", "event_date_iso", "fight_date")
A_KEYS = ("fighter1", "fighter_1", "red_name", "fighter_a")
B_KEYS = ("fighter2", "fighter_2", "blue_name", "fighter_b")
OUTCOME_KEYS = ("outcome", "winner", "winning_fighter", "result")
FAV_KEYS = ("favourite", "favorite")
DOG_KEYS = ("underdog", "dog")
FAV_ODDS_KEYS = ("favourite_odds", "favorite_odds", "fav_odds")
DOG_ODDS_KEYS = ("underdog_odds", "dog_odds")


def _pick(row, keys):
    return next((k for k in keys if k in row and str(row.get(k) or "").strip()), None)


def _date_iso(value):
    raw = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return raw


def _outcome_to_y(label, fighter_a, fighter_b):
    value = str(label or "").strip().casefold().replace(" ", "_")
    a = str(fighter_a or "").strip().casefold()
    b = str(fighter_b or "").strip().casefold()
    if value in {"fighter", "fighter1", "fighter_1", "1", "a", "red", "first"} or value == a:
        return 1
    if value in {"fighter2", "fighter_2", "2", "b", "blue", "second"} or value == b:
        return 0
    if value in {"draw", "drawn", "d"}:
        return None, "draw_excluded"
    if value in {"nc", "n/c", "no_contest", "no-contest"}:
        return None, "no_contest_excluded"
    return None, "ambiguous_outcome_excluded"


def normalize_combined_csv(input_csv, normalized_csv, odds_csv, summary_json=None):
    with open(input_csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("Dataset CSV vuoto.")
    sample = rows[0]
    keys = {"date": _pick(sample, DATE_KEYS), "fighter_a": _pick(sample, A_KEYS),
            "fighter_b": _pick(sample, B_KEYS), "outcome": _pick(sample, OUTCOME_KEYS),
            "favorite": _pick(sample, FAV_KEYS), "underdog": _pick(sample, DOG_KEYS),
            "favorite_odds": _pick(sample, FAV_ODDS_KEYS), "underdog_odds": _pick(sample, DOG_ODDS_KEYS)}
    essential = ("date", "fighter_a", "fighter_b", "outcome")
    missing = [k for k in essential if not keys[k]]
    if missing:
        raise ValueError("Colonne obbligatorie non trovate: " + ", ".join(missing))

    normalized, odds_rows = [], []
    excluded = Counter()
    seen = set()
    for r in rows:
        date = _date_iso(r.get(keys["date"]))
        a = str(r.get(keys["fighter_a"]) or "").strip()
        b = str(r.get(keys["fighter_b"]) or "").strip()
        if not date or not a or not b or a.casefold() == b.casefold():
            excluded["missing_or_invalid_bout_identity"] += 1
            continue
        y_result = _outcome_to_y(r.get(keys["outcome"]), a, b)
        if isinstance(y_result, tuple):
            excluded[y_result[1]] += 1
            continue
        if y_result is None:
            excluded["ambiguous_outcome_excluded"] += 1
            continue
        y = y_result
        uid = str(r.get("fight_id") or r.get("bout_id") or "").strip()
        identity = uid or (date, a.casefold(), b.casefold())
        if identity in seen:
            excluded["duplicate_bout"] += 1
            continue
        seen.add(identity)
        normalized.append({"date": date, "red_name": a, "blue_name": b, "y": y,
                          "event_name": r.get("event_name", ""), "method": r.get("method", ""),
                          "weight_class": r.get("weight_class", ""), "source_id": uid})

        fav_name = str(r.get(keys["favorite"]) or "").strip() if keys["favorite"] else ""
        dog_name = str(r.get(keys["underdog"]) or "").strip() if keys["underdog"] else ""
        fav_raw = r.get(keys["favorite_odds"]) if keys["favorite_odds"] else None
        dog_raw = r.get(keys["underdog_odds"]) if keys["underdog_odds"] else None
        try:
            fav_odds, dog_odds = float(fav_raw), float(dog_raw)
            if fav_odds <= 1 or dog_odds <= 1 or not fav_name or not dog_name:
                raise ValueError
            odds_rows.append({"date": date, "favourite": fav_name, "underdog": dog_name,
                              "favourite_odds": fav_odds, "underdog_odds": dog_odds})
        except (TypeError, ValueError):
            excluded["odds_missing_or_invalid"] += 1

    if not normalized:
        raise ValueError("Nessun incontro valido: controllare le colonne e le etichette outcome.")
    normalized.sort(key=lambda x: x["date"])
    odds_rows.sort(key=lambda x: x["date"])
    Path(normalized_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(odds_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(normalized_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(normalized[0])); w.writeheader(); w.writerows(normalized)
    odds_fields = ["date", "favourite", "underdog", "favourite_odds", "underdog_odds"]
    with open(odds_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=odds_fields); w.writeheader(); w.writerows(odds_rows)
    summary = {"input_rows": len(rows), "normalized_bouts": len(normalized), "odds_rows": len(odds_rows),
               "excluded_counts": dict(excluded), "selected_columns": keys,
               "date_min": normalized[0]["date"], "date_max": normalized[-1]["date"],
               "notes": ["Outcome is mapped only from explicit recognized labels.",
                         "Odds are emitted only when both decimal prices and favorite/underdog names are valid.",
                         "This converter does not establish that odds were captured pre-fight; audit timestamps/source before ROI claims."]}
    if summary_json:
        Path(summary_json).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_csv")
    ap.add_argument("--normalized", default="normalized_historical_bouts.csv")
    ap.add_argument("--odds", default="historical_odds.csv")
    ap.add_argument("--summary", default="combined_dataset_summary.json")
    args = ap.parse_args()
    print(json.dumps(normalize_combined_csv(args.input_csv, args.normalized, args.odds, args.summary), indent=2))


if __name__ == "__main__":
    main()
