"""Train an empirical historical model and score a sourced upcoming UFC card.

All feature snapshots are generated before each historical bout. Upcoming fighter
features use only that fighter's latest available historical snapshot. The command
requires explicit historical outcomes and never creates missing fighter statistics.
"""
from __future__ import annotations
import argparse, csv, json, re, unicodedata
from pathlib import Path
import numpy as np
from .pre_fight_features import build_pre_fight_features
from .backtest import fit_logistic, predict

EXCLUDED = {"date", "red_name", "blue_name", "event_name", "method", "weight_class", "y"}

def _name_key(name):
    value=unicodedata.normalize("NFKD", str(name or ""))
    value="".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

def _feature_columns(rows):
    return [k for k in rows[0] if k not in EXCLUDED and k.endswith("_pre")]

def _numeric_column(rows, col):
    values=[]
    for row in rows:
        try:
            v=row.get(col, "")
            values.append(float(v) if v not in (None,"","None","NA","na") else np.nan)
        except (TypeError,ValueError): values.append(np.nan)
    return np.asarray(values,dtype=float)

def _latest_snapshots(feature_rows):
    snapshots={}
    for row in feature_rows:
        date=str(row.get("date", ""))
        for fighter, side in ((row.get("red_name"),"red"),(row.get("blue_name"),"blue")):
            key=_name_key(fighter)
            if not key: continue
            old=snapshots.get(key)
            if old is None or date >= old["date"]:
                snapshots[key]={"date":date,"name":fighter,"side":side,"row":row}
    return snapshots

def _side_value(snapshot, feature, desired_side):
    if snapshot is None: return np.nan
    row=snapshot["row"]
    source_side=snapshot["side"]
    if feature.startswith("red_"):
        base=feature[4:]
        source_col=f"{source_side}_{base}"
    elif feature.startswith("blue_"):
        base=feature[5:]
        source_col=f"{source_side}_{base}"
    else:
        return np.nan
    value=row.get(source_col)
    try: return float(value) if value not in (None,"","None","NA","na") else np.nan
    except (TypeError,ValueError): return np.nan

def _compose_upcoming_features(fighter_a, fighter_b, snapshots, columns):
    sa=snapshots.get(_name_key(fighter_a)); sb=snapshots.get(_name_key(fighter_b))
    result={}
    for col in columns:
        if col.startswith("red_"):
            result[col]=_side_value(sa,col,"red")
        elif col.startswith("blue_"):
            result[col]=_side_value(sb,col,"blue")
        elif col=="elo_diff_pre":
            a=_side_value(sa,"red_elo_pre","red")
            b=_side_value(sb,"red_elo_pre","red")
            result[col]=a-b if np.isfinite(a) and np.isfinite(b) else np.nan
        elif "_diff_" in col:
            # Generated feature naming is symmetrical: red_<base>_pre - blue_<base>_pre.
            base=col.replace("_diff_", "_", 1)
            red_col="red_"+base
            blue_col="blue_"+base
            a=_side_value(sa,red_col,"red")
            b=_side_value(sb,blue_col,"blue")
            result[col]=a-b if np.isfinite(a) and np.isfinite(b) else np.nan
        else:
            result[col]=np.nan
    return result,sa,sb

def predict_card(historical_csv, card_json, output_json, min_bouts=30):
    card=json.loads(Path(card_json).read_text(encoding="utf-8"))
    event_date=(card.get("event",{}) or {}).get("date")
    with open(historical_csv,newline="",encoding="utf-8-sig") as f: history=list(csv.DictReader(f))
    if not history: raise ValueError("Historical CSV is empty.")
    required={"date","red_name","blue_name","y"}
    if not required.issubset(history[0]):
        raise ValueError("Historical CSV must contain date, red_name, blue_name, y.")
    history=[r for r in history if str(r.get("y")) in {"0","1","0.0","1.0"} and r.get("date") and r.get("red_name") and r.get("blue_name")]
    # Prevent post-event historical rows from leaking into a forecast for a dated card.
    if event_date:
        history=[r for r in history if str(r.get("date", ""))[:10] < str(event_date)[:10]]
    if len(history)<min_bouts:
        raise ValueError(f"Need at least {min_bouts} eligible historical binary bouts before the event; found {len(history)}.")
    fights=card.get("fights")
    if not isinstance(fights,list) or not fights: raise ValueError("Card JSON has no fights array.")
    for fight in fights:
        if not fight.get("fighter_a") or not fight.get("fighter_b"):
            raise ValueError("Every card fight must contain fighter_a and fighter_b.")
    # Append outcome-less target bouts after history. The feature engine emits snapshots
    # for them but does not update fighter histories because y is unknown.
    target_date=str(event_date or (max(r["date"] for r in history)+"T99:99"))
    targets=[{"date":target_date,"red_name":f["fighter_a"],"blue_name":f["fighter_b"],"y":None,
              "event_name":(card.get("event",{}) or {}).get("name", "upcoming card")} for f in fights]
    feature_rows=build_pre_fight_features(history+targets)
    historical_features=feature_rows[:len(history)]
    target_features=feature_rows[len(history):]
    columns=_feature_columns(historical_features)
    if not columns: raise ValueError("No usable pre-fight features were generated.")
    xcols=[]; medians=[]; usable=[]
    for col in columns:
        arr=_numeric_column(historical_features,col)
        if np.all(np.isnan(arr)): continue
        median=float(np.nanmedian(arr))
        arr=np.where(np.isnan(arr),median,arr)
        if np.std(arr)<1e-10: continue
        xcols.append(arr); medians.append(median); usable.append(col)
    if not usable: raise ValueError("No variable numeric pre-fight features available to fit model.")
    X=np.column_stack(xcols)
    y=np.asarray([int(float(r["y"])) for r in historical_features],dtype=int)
    if len(set(y.tolist()))<2: raise ValueError("Historical data must contain wins for both sides of the binary target.")
    model=fit_logistic(X,y)
    scored=[]
    for fight,feature_row in zip(fights,target_features):
        row=_numeric_column([feature_row],usable)
        missing=np.isnan(row)
        row=np.where(missing,np.asarray(medians),row)
        p=float(predict(model,row.reshape(1,-1))[0])
        fighter_a=fight["fighter_a"]; fighter_b=fight["fighter_b"]
        # A fighter's prior record is visible in the target snapshot's bout counts.
        a_bouts=feature_row.get("red_bouts_pre",0) or 0
        b_bouts=feature_row.get("blue_bouts_pre",0) or 0
        fight["empirical_prediction"]={
            "p_a":p,"p_b":1-p,"model":"historical logistic regression",
            "historical_bouts_used":len(historical_features),"feature_count":len(usable),
            "fighter_a_history_available":float(a_bouts)>0,"fighter_b_history_available":float(b_bouts)>0,
            "fighter_a_prior_bouts":int(a_bouts),"fighter_b_prior_bouts":int(b_bouts),
            "missing_feature_count":int(missing.sum()),
            "imputation":"training-history median; missing values counted and reported",
            "warning":"Uncalibrated model estimate; not a betting recommendation. Prediction quality depends on source dataset completeness and temporal validation."
        }
        scored.append({"fighter_a":fighter_a,"fighter_b":fighter_b,"p_a":p,"p_b":1-p,
                       "fighter_a_prior_bouts":int(a_bouts),"fighter_b_prior_bouts":int(b_bouts),
                       "missing_feature_count":int(missing.sum())})
    card["forecast_metadata"]={"method":"empirical logistic regression fitted on provided historical CSV",
        "historical_bouts_used":len(historical_features),"feature_count":len(usable),
        "history_date_range":[min(r["date"] for r in history),max(r["date"] for r in history)],
        "event_date_cutoff":event_date,
        "limitations":"Only historical records strictly before a dated event are used. No source validation/calibration is implied. Missing fighter features are median-imputed and reported per fight."}
    Path(output_json).write_text(json.dumps(card,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return {"historical_bouts_used":len(historical_features),"feature_count":len(usable),"scored_fights":scored,"output":str(output_json)}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("historical_csv",help="Normalized historical CSV with explicit binary y outcomes")
    ap.add_argument("card_json",help="Sourced upcoming card JSON")
    ap.add_argument("--output",default="forecast_card.json")
    ap.add_argument("--min-bouts",type=int,default=30)
    args=ap.parse_args()
    print(json.dumps(predict_card(args.historical_csv,args.card_json,args.output,args.min_bouts),indent=2))
if __name__=="__main__": main()
