"""Expanding-window walk-forward validation with event-date grouping and calibration diagnostics."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
import numpy as np
from .backtest import fit_logistic, predict, evaluate


def calibration_bins(y, p, bins=10):
    y=np.asarray(y,dtype=float); p=np.asarray(p,dtype=float)
    out=[]
    for b in range(bins):
        lo=b/bins; hi=(b+1)/bins
        ids=np.where(((lo<=p)&(p<hi)) | ((b==bins-1)&(p==hi)))[0]
        if len(ids):
            mean_p=float(np.mean(p[ids])); observed=float(np.mean(y[ids]))
            out.append({"range":f"{lo:.1f}-{hi:.1f}","n":int(len(ids)),
                        "mean_probability":mean_p,"observed_rate":observed,
                        "absolute_calibration_error":abs(mean_p-observed)})
    return out


def _date_group_indices(rows):
    """Return contiguous index ranges, keeping every bout on a date in one fold."""
    dates=[str(r.get("date", "")) for r in rows]
    groups=[]; start=0
    for i in range(1,len(dates)):
        if dates[i]!=dates[i-1]:
            groups.append((start,i)); start=i
    groups.append((start,len(dates)))
    return groups


def _bootstrap_brier_delta(y, p, repetitions=2000, seed=42):
    """CI for model Brier minus constant 0.5 baseline; negative favors model."""
    y=np.asarray(y,dtype=float); p=np.asarray(p,dtype=float)
    if len(y)<2: return {"estimate":None,"ci_95_low":None,"ci_95_high":None,"repetitions":0}
    model=(p-y)**2; baseline=(0.5-y)**2
    delta=model-baseline
    rng=np.random.default_rng(seed)
    samples=np.empty(repetitions,dtype=float)
    for i in range(repetitions): samples[i]=np.mean(delta[rng.integers(0,len(delta),len(delta))])
    return {"estimate":float(np.mean(delta)),"ci_95_low":float(np.quantile(samples,.025)),
            "ci_95_high":float(np.quantile(samples,.975)),"repetitions":repetitions,
            "interpretation":"Negative values favor the model over the 0.5 probability baseline."}


def walk_forward_report(features_csv, report_json, folds=5, initial_train_fraction=.5):
    if not 0.1<=initial_train_fraction<0.9: raise ValueError("initial_train_fraction must be in [0.1, 0.9).")
    with open(features_csv,newline="",encoding="utf-8-sig") as f:
        rows=sorted(list(csv.DictReader(f)),key=lambda r:r.get("date",""))
    n=len(rows)
    if n<100: raise ValueError(f"Walk-forward requires at least 100 bouts; got {n}.")
    if folds<2: raise ValueError("folds must be >= 2")
    date_groups=_date_group_indices(rows)
    if len(date_groups)<folds+2: raise ValueError("Not enough distinct bout dates to form grouped folds.")
    start_group=max(1,int(len(date_groups)*initial_train_fraction))
    # Guarantee a minimum of 30 training bouts while preserving date boundaries.
    while start_group<len(date_groups) and date_groups[start_group-1][1]<30: start_group+=1
    start=date_groups[start_group-1][1]
    remaining_groups=len(date_groups)-start_group
    if remaining_groups<folds: raise ValueError("Not enough date groups for requested folds after initial training period.")
    group_sizes=[remaining_groups//folds+(1 if i<remaining_groups%folds else 0) for i in range(folds)]
    excluded={"date","red_name","blue_name","event_name","method","weight_class","y"}
    candidates=[k for k in rows[0] if k not in excluded and k.endswith("_pre")]
    target=np.array([int(float(r["y"])) for r in rows])
    if not np.all(np.isin(target,[0,1])): raise ValueError("Walk-forward target y must contain only binary 0/1 values.")
    usable={}
    for col in candidates:
        try: arr=np.array([float(r[col]) if r.get(col) not in ("","None","NA") else np.nan for r in rows])
        except (TypeError,ValueError): continue
        if np.all(np.isnan(arr)): continue
        usable[col]=arr
    results=[]; predictions=[]; cursor=start; current_group=start_group
    for fold,size_groups in enumerate(group_sizes,1):
        test_end_group=current_group+size_groups
        test_end=date_groups[test_end_group-1][1]
        train_end=cursor
        columns=[]; train_cols=[]; test_cols=[]
        for col,arr in usable.items():
            train_values=arr[:train_end]
            median=float(np.nanmedian(train_values)) if not np.all(np.isnan(train_values)) else 0.0
            filled=np.where(np.isnan(arr),median,arr)
            if np.std(filled[:train_end])<1e-10: continue
            columns.append(col); train_cols.append(filled[:train_end]); test_cols.append(filled[cursor:test_end])
        if not columns: raise ValueError("No numeric pre-fight features found.")
        xtr=np.column_stack(train_cols); xte=np.column_stack(test_cols)
        ytr=target[:train_end]; yte=target[cursor:test_end]
        model=fit_logistic(xtr,ytr); probs=predict(model,xte)
        metrics=evaluate(yte,probs).__dict__
        elo=np.array([float(rows[i].get("elo_diff_pre") or 0.0) for i in range(cursor,test_end)])
        elo_probs=1/(1+10**(-elo/400))
        elo_metrics=evaluate(yte,elo_probs).__dict__
        results.append({"fold":fold,"train_start":rows[0]["date"],"train_end":rows[train_end-1]["date"],
                        "test_start":rows[cursor]["date"],"test_end":rows[test_end-1]["date"],
                        "train_n":train_end,"test_n":test_end-cursor,
                        "train_date_groups":current_group,"test_date_groups":size_groups,
                        "feature_count":len(columns),"metrics":metrics,"elo_baseline_metrics":elo_metrics,
                        "calibration_bins":calibration_bins(yte,probs)})
        for j,p in enumerate(probs):
            predictions.append({"fold":fold,"date":rows[cursor+j]["date"],"red_name":rows[cursor+j]["red_name"],
                                "blue_name":rows[cursor+j]["blue_name"],"p_red_win":float(p),
                                "actual_red_win":int(yte[j]),"weight_class":rows[cursor+j].get("weight_class", "Unknown") or "Unknown"})
        cursor=test_end; current_group=test_end_group
    y_all=np.array([p["actual_red_win"] for p in predictions]); p_all=np.array([p["p_red_win"] for p in predictions])
    elo_all=np.array([1/(1+10**(-float(rows[start+i].get("elo_diff_pre") or 0.0)/400)) for i in range(len(predictions))])
    overall=evaluate(y_all,p_all).__dict__; overall_elo=evaluate(y_all,elo_all).__dict__
    # Out-of-sample subgroup metrics by weight class; suppress interpretation for tiny groups.
    weight_class_metrics=[]
    for wc in sorted({p.get("weight_class", "Unknown") for p in predictions}):
        subset=[p for p in predictions if p.get("weight_class", "Unknown")==wc]
        ys=np.array([p["actual_red_win"] for p in subset]); ps=np.array([p["p_red_win"] for p in subset])
        m=evaluate(ys,ps).__dict__
        weight_class_metrics.append({"weight_class":wc,"metrics":m,"reliability_note":"Descriptive only; interpret cautiously when n < 100." if len(subset)<100 else "Subgroup sample >= 100; still subject to temporal and dataset limitations."})
    baseline=evaluate(y_all,np.full(len(y_all),.5)).__dict__
    report={"dataset_n":n,"distinct_date_groups":len(date_groups),"initial_train_n":start,
            "initial_train_date_groups":start_group,"folds":results,"aggregate_metrics":overall,
            "aggregate_elo_baseline_metrics":overall_elo,"aggregate_50_50_baseline_metrics":baseline,
            "aggregate_accuracy_delta_vs_elo":overall["accuracy"]-overall_elo["accuracy"],
            "aggregate_brier_skill_vs_50_50":1.0-overall["brier"]/baseline["brier"] if baseline["brier"] else None,
            "aggregate_calibration_bins":calibration_bins(y_all,p_all),
            "weight_class_metrics":weight_class_metrics,
            "brier_delta_bootstrap_ci_vs_50_50":_bootstrap_brier_delta(y_all,p_all),
            "predictions":predictions,
            "method":"expanding-window chronological walk-forward; all bouts on same date kept together; train-only median imputation; Elo and constant-0.5 benchmarks; calibration diagnostics"}
    Path(report_json).write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("features_csv");ap.add_argument("--report",default="ufc_walk_forward_report.json")
    ap.add_argument("--folds",type=int,default=5);ap.add_argument("--initial-train-fraction",type=float,default=.5)
    a=ap.parse_args();r=walk_forward_report(a.features_csv,a.report,a.folds,a.initial_train_fraction)
    print(json.dumps({"dataset_n":r["dataset_n"],"folds":r["folds"],"aggregate_metrics":r["aggregate_metrics"],
                      "aggregate_elo_baseline_metrics":r["aggregate_elo_baseline_metrics"],
                      "aggregate_50_50_baseline_metrics":r["aggregate_50_50_baseline_metrics"],
                      "aggregate_brier_skill_vs_50_50":r["aggregate_brier_skill_vs_50_50"],"weight_class_metrics":r["weight_class_metrics"],
                      "brier_delta_bootstrap_ci_vs_50_50":r["brier_delta_bootstrap_ci_vs_50_50"],"report":a.report},indent=2))
if __name__=="__main__":main()
