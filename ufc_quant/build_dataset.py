"""Download historical UFCStats bout list into a normalized raw CSV.
Stats-derived pre-fight features are intentionally not synthesized here; those require
fighter-history snapshots to avoid outcome leakage.
"""
from __future__ import annotations
import argparse, csv, time
from dataclasses import asdict
from .ingest import UFCStatsClient

def collect_events(client, max_pages=30):
    events=[]
    for page in range(1,max_pages+1):
        page_events=client.events(page)
        if not page_events: break
        events.extend(page_events)
    # de-duplicate by event URL
    seen=set(); out=[]
    for e in events:
        if e.url not in seen: seen.add(e.url); out.append(e)
    return out

def build_raw_bout_csv(output, max_pages=30, delay=1.5, include_stats=False):
    client=UFCStatsClient(delay_seconds=delay)
    events=collect_events(client,max_pages=max_pages)
    rows=[]
    for idx,event in enumerate(events,1):
        print(f"[{idx}/{len(events)}] {event.name} | {event.date}")
        try:
            bouts=client.event_bouts(event.url)
            for bout in bouts:
                row={**asdict(bout), "date": event.date, "location": event.location}
                if include_stats and bout.fight_url:
                    from .ufcstats_fight_parser import parse_totals_page
                    parsed=parse_totals_page(client,bout.fight_url)
                    fighter_stats=parsed.get("fighters",{})
                    for side,fighter_name in (("red",bout.red_name),("blue",bout.blue_name)):
                        stats=fighter_stats.get(fighter_name)
                        if stats is None:
                            # Name normalization only strips whitespace and case; never fuzzy-match two fighters.
                            keymap={str(k).strip().casefold():v for k,v in fighter_stats.items()}
                            stats=keymap.get(fighter_name.strip().casefold(),{})
                        for metric,value in (stats or {}).items():
                            row[f"{side}_{metric}"]=value
                    row["stats_parse_warnings"]=";".join(parsed.get("warnings",[]))
                rows.append(row)
        except Exception as exc:
            print("WARN event skipped:",event.name,repr(exc))
    fields=["date","location","event_name","red_name","blue_name","red_url","blue_url","fight_url","result","method","round","time"]
    if include_stats:
        stat_fields=["sig_str_landed","sig_str_attempted","total_str_landed","total_str_attempted",
                     "td_landed","td_attempted","knockdowns","submission_attempts","reversals","control_time_seconds"]
        fields += [f"{side}_{metric}" for side in ("red","blue") for metric in stat_fields]
        fields += ["stats_parse_warnings"]
    with open(output,"w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    return len(events),len(rows)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="ufcstats_raw_bouts.csv")
    ap.add_argument("--max-pages",type=int,default=30)
    ap.add_argument("--delay",type=float,default=1.5)
    ap.add_argument("--include-stats",action="store_true",help="Fetch each fight detail page and parse totals (more requests).")
    args=ap.parse_args()
    n_events,n_bouts=build_raw_bout_csv(args.output,args.max_pages,args.delay,args.include_stats)
    print(f"Collected {n_bouts} bouts across {n_events} events -> {args.output}")
