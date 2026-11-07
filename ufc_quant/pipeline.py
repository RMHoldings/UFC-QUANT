"""End-to-end offline raw UFCStats CSV -> leakage-safe features -> temporal model report."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
import numpy as np
from .pre_fight_features import build_pre_fight_features
from .backtest import fit_logistic,predict,evaluate

def outcome_from_result(value):
    s=(value or "").strip().upper()
    # UFCStats bout list result column typically reports W/L/D/NC for red-side entry.
    if s in {"W","WIN","1"}: return 1
    if s in {"L","LOSS","0"}: return 0
    if s in {"D","DRAW","DRAWN"}: return 0.5
    if s in {"NC","N/C","NO CONTEST",""}: return None
    return None

def prepare_rows(raw_rows):
    out=[]
    for r in raw_rows:
        y=outcome_from_result(r.get("result"))
        if y not in (0,1): # discard draws, NC, ambiguous labels for binary modeling
            continue
        if not r.get("date") or not r.get("red_name") or not r.get("blue_name"): continue
        normalized=dict(r); normalized["y"]=y
        out.append(normalized)
    return out

def create_feature_dataset(raw_csv, features_csv):
    with open(raw_csv,newline="",encoding="utf-8-sig") as f: raw=list(csv.DictReader(f))
    eligible=prepare_rows(raw)
    features=build_pre_fight_features(eligible)
    if not features: raise ValueError("No eligible bouts: inspect result labels/date/name columns.")
    keys=list(features[0].keys())
    with open(features_csv,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(features)
    return len(raw),len(eligible),len(features)

def temporal_model_report(features_csv,report_json,train_fraction=.7):
    with open(features_csv,newline="",encoding="utf-8-sig") as f: rows=sorted(list(csv.DictReader(f)),key=lambda r:r.get("date",""))
    if len(rows)<30: raise ValueError(f"At least 30 eligible bouts required; found {len(rows)}.")
    split=max(1,min(len(rows)-1,int(len(rows)*train_fraction)))
    target=np.array([int(float(r["y"])) for r in rows])
    # Only use pre-fight, numeric columns, excluding identifiers, target and metadata.
    excluded={"date","red_name","blue_name","event_name","method","weight_class","y"}
    candidates=[k for k in rows[0] if k not in excluded and k.endswith("_pre")]
    train_matrix=[]; test_matrix=[]; used=[]
    for col in candidates:
        vals=[]
        for r in rows:
            v=r.get(col,"")
            try: vals.append(float(v) if v not in ("","None","NA") else np.nan)
            except (TypeError,ValueError): vals.append(np.nan)
        arr=np.asarray(vals,dtype=float)
        if np.all(np.isnan(arr)): continue
        median=float(np.nanmedian(arr[:split]))
        arr=np.where(np.isnan(arr),median,arr)
        if np.std(arr[:split])<1e-10: continue
        train_matrix.append(arr[:split]);test_matrix.append(arr[split:]);used.append(col)
    if not used: raise ValueError("No usable numeric pre-fight features.")
    xtrain=np.column_stack(train_matrix);xtest=np.column_stack(test_matrix)
    model=fit_logistic(xtrain,target[:split])
    probs=predict(model,xtest)
    metrics=evaluate(target[split:],probs).__dict__
    # Elo-only benchmark, computed from pre-fight rating differences; no training fit.
    elo_diffs=np.array([float(r.get("elo_diff_pre") or 0.0) for r in rows[split:]],dtype=float)
    elo_probs=1.0/(1.0+10.0**(-elo_diffs/400.0))
    elo_metrics=evaluate(target[split:],elo_probs).__dict__
    def calibration_bins(y,p,bins=10):
        out=[]
        for b in range(bins):
            lo=b/bins; hi=(b+1)/bins
            ids=[i for i,v in enumerate(p) if (lo<=v<hi) or (b==bins-1 and v==hi)]
            if ids:
                out.append({"range":f"{lo:.1f}-{hi:.1f}","n":len(ids),
                            "mean_probability":float(np.mean(p[ids])),"observed_rate":float(np.mean(y[ids]))})
        return out
    calibration=calibration_bins(target[split:],probs)
    report={"train_n":split,"test_n":len(rows)-split,"feature_count":len(used),"features":used,
            "metrics":metrics,"elo_baseline_metrics":elo_metrics,"calibration_bins":calibration, "test_predictions":[{"date":rows[i+split]["date"],"red_name":rows[i+split]["red_name"],
            "blue_name":rows[i+split]["blue_name"],"p_red_win":float(probs[i]),"actual_red_win":int(target[i+split])}
            for i in range(len(probs))],"method":"chronological holdout; median imputation fitted on train only"}
    Path(report_json).write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw_csv")
    ap.add_argument("--features",default="ufc_pre_fight_features.csv")
    ap.add_argument("--report",default="ufc_temporal_backtest.json")
    ap.add_argument("--train-fraction",type=float,default=.7)
    args=ap.parse_args()
    raw_n,eligible_n,feature_n=create_feature_dataset(args.raw_csv,args.features)
    report=temporal_model_report(args.features,args.report,args.train_fraction)
    print(json.dumps({"raw_rows":raw_n,"eligible_binary_bouts":eligible_n,"feature_rows":feature_n,"metrics":report["metrics"],"feature_count":report["feature_count"],"files":[args.features,args.report]},indent=2))
if __name__=="__main__": main()
