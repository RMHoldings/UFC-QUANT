"""Empirical backtest runner for normalized historical bout CSVs."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from .pre_fight_features import build_pre_fight_features
from .pipeline import temporal_model_report

def normalized_to_features(normalized_csv, features_csv):
    with open(normalized_csv, newline="", encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    if not rows:
        raise ValueError("CSV normalizzato vuoto.")
    required={"date","red_name","blue_name","y"}
    if not required.issubset(rows[0]):
        raise ValueError("CSV non normalizzato: richiesti date, red_name, blue_name, y.")
    rows=[r for r in rows if r.get("y") in {"0","1","0.0","1.0"}]
    if len(rows)<30:
        raise ValueError(f"Servono almeno 30 incontri binari validi; trovati {len(rows)}.")
    features=build_pre_fight_features(rows)
    with open(features_csv,"w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(features[0]))
        writer.writeheader()
        writer.writerows(features)
    return {"normalized_rows":len(rows),"feature_rows":len(features),"features_csv":str(features_csv)}

def run_empirical_backtest(normalized_csv, features_csv, report_json, train_fraction=.7):
    summary=normalized_to_features(normalized_csv,features_csv)
    report=temporal_model_report(features_csv,report_json,train_fraction)
    summary["report_json"]=str(report_json)
    summary["train_n"]=report["train_n"]
    summary["test_n"]=report["test_n"]
    summary["metrics"]=report["metrics"]
    summary["elo_baseline_metrics"]=report["elo_baseline_metrics"]
    summary["model_beats_elo_accuracy"]=report["metrics"]["accuracy"]>report["elo_baseline_metrics"]["accuracy"]
    return summary

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("normalized_csv")
    ap.add_argument("--features",default="empirical_pre_fight_features.csv")
    ap.add_argument("--report",default="empirical_backtest_report.json")
    ap.add_argument("--train-fraction",type=float,default=.7)
    args=ap.parse_args()
    result=run_empirical_backtest(args.normalized_csv,args.features,args.report,args.train_fraction)
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
