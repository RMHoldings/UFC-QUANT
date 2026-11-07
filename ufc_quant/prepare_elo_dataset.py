"""Prepare Elo feature snapshots from a raw UFCStats CSV.
Outcome convention: y=1 if red corner/fighter A won, y=0 if blue/fighter B won.
This tool only infers outcome from normalized result strings; unknown outcomes are skipped.
"""
from __future__ import annotations
import argparse,csv
from .elo import build_elo_snapshots

def normalize_outcome(value):
    s=(value or "").strip().upper()
    # UFCStats often marks winner/loser with W/L in the result column.
    if s in ("W","WIN","1"): return 1
    if s in ("L","LOSS","0"): return 0
    if s in ("D","DRAW"): return None
    return None

def convert(input_csv,output_csv):
    with open(input_csv,newline="",encoding="utf-8-sig") as f: raw=list(csv.DictReader(f))
    rows=[]
    for r in raw:
        y=normalize_outcome(r.get("result"))
        if y is None: continue
        date=r.get("event_date") or r.get("date") or ""
        rows.append({"date":date,"red_name":r["red_name"],"blue_name":r["blue_name"],"y":y,
                     "event_name":r.get("event_name",""),"method":r.get("method","")})
    enriched=build_elo_snapshots(rows)
    fields=["date","event_name","red_name","blue_name","y","method","rating_a_pre","rating_b_pre","elo_diff_pre","elo_expected_a"]
    with open(output_csv,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in enriched: w.writerow({k:row.get(k) for k in fields})
    return len(enriched)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input_csv");ap.add_argument("--output",default="elo_dataset.csv")
    a=ap.parse_args()
    count=convert(a.input_csv,a.output)
    print(f"Wrote {count} rows to {a.output}")
if __name__=="__main__": main()
