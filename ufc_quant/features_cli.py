"""CLI to construct leakage-safe pre-fight feature snapshots from bout-stat CSV."""
import argparse,csv,json
from .pre_fight_features import build_pre_fight_features,validate_no_future_leakage
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input_csv")
    ap.add_argument("--output",default="pre_fight_features.csv")
    ap.add_argument("--metrics",default="sig_str_landed,sig_str_attempted,total_str_landed,total_str_attempted,td_landed,td_attempted,submission_attempts,knockdowns")
    ap.add_argument("--date",default="date")
    a=ap.parse_args()
    with open(a.input_csv,newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
    features=build_pre_fight_features(rows,date_key=a.date,metric_names=tuple(a.metrics.split(",")))
    validate_no_future_leakage(features)
    if not features:
        raise SystemExit("No feature rows generated.")
    fields=list(features[0].keys())
    with open(a.output,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(features)
    print(f"Generated {len(features)} feature snapshots -> {a.output}")
if __name__=="__main__": main()
