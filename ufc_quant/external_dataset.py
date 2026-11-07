"""External historical dataset adapter and empirical validation gate.
Supports common one-row-per-bout schemas. Refuses to fabricate outcomes when winner is absent.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from collections import Counter

DATE_KEYS=("event_date_iso","date","event_date","fight_date")
FIGHTER_A_KEYS=("red_name","fighter_1","fighter_a","fighter1","fighter_a_name","header_fighter_a_name")
FIGHTER_B_KEYS=("blue_name","fighter_2","fighter_b","fighter2","fighter_b_name","header_fighter_b_name")
WINNER_KEYS=("winner","winning_fighter","winner_name","result_winner","header_winner_name")
URL_KEYS=("fight_url","url","fight_id","bout_id","fight_stats_page_url","FightID_generated")
def pick(row,keys):
    for k in keys:
        if k in row and str(row[k]).strip(): return k
    return None
def normalize_external_csv(input_csv,output_csv):
    with open(input_csv,newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
    if not rows: raise ValueError("Dataset vuoto.")
    keys=rows[0].keys()
    datek=pick(rows[0],DATE_KEYS); ak=pick(rows[0],FIGHTER_A_KEYS); bk=pick(rows[0],FIGHTER_B_KEYS); wk=pick(rows[0],WINNER_KEYS); urlk=pick(rows[0],URL_KEYS)
    missing=[label for label,key in (("date",datek),("fighter_a",ak),("fighter_b",bk),("winner",wk)) if key is None]
    if missing: raise ValueError("Campi indispensabili assenti: "+", ".join(missing)+"; nessun target viene inventato.")
    out=[]; invalid=Counter(); seen=set()
    for i,r in enumerate(rows,2):
        a=(r.get(ak) or "").strip(); b=(r.get(bk) or "").strip(); winner=(r.get(wk) or "").strip()
        date=(r.get(datek) or "").strip()
        if not date or not a or not b or not winner: invalid["missing_required"]+=1; continue
        if a.casefold()==b.casefold(): invalid["same_fighter_both_sides"]+=1; continue
        if winner.casefold()==a.casefold(): y=1
        elif winner.casefold()==b.casefold(): y=0
        elif winner.casefold() in {"draw","drawn","d"}: invalid["draw_excluded"]+=1; continue
        elif winner.casefold() in {"nc","n/c","no contest","no-contest"}: invalid["no_contest_excluded"]+=1; continue
        else: invalid["winner_not_matched_to_fighter"]+=1; continue
        uid=(r.get(urlk) or "").strip() if urlk else ""
        identity=uid or (date.casefold(),a.casefold(),b.casefold())
        if identity in seen: invalid["duplicate_bout"]+=1; continue
        seen.add(identity)
        out.append({"date":date,"red_name":a,"blue_name":b,"y":y,
                    "event_name":r.get("event_name",r.get("event","")),
                    "method":r.get("method",""),"weight_class":r.get("weight_class",""),
                    "source_id":uid})
    if not out: raise ValueError("Nessun bout valido dopo normalizzazione; controllare il campo winner.")
    out.sort(key=lambda r:r["date"])
    with open(output_csv,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    summary={"input_rows":len(rows),"normalized_rows":len(out),"excluded_or_invalid":dict(invalid),
             "selected_columns":{"date":datek,"fighter_a":ak,"fighter_b":bk,"winner":wk,"id":urlk},
             "date_min":out[0]["date"],"date_max":out[-1]["date"]}
    return summary
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_csv");ap.add_argument("--output",default="normalized_historical_bouts.csv")
    ap.add_argument("--summary",default="normalization_summary.json")
    args=ap.parse_args()
    summary=normalize_external_csv(args.input_csv,args.output)
    Path(args.summary).write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
