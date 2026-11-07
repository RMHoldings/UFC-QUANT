"""Leakage-safe rolling pre-fight feature engineering.
Input rows are chronological bout records containing outcome y for red fighter and
post-fight per-bout statistics with prefix red_ / blue_. Feature snapshots are emitted
before updating fighter history with the current bout's stats/outcome.
"""
from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from typing import Iterable
import math

DEFAULT_METRICS = (
    "sig_str_landed", "sig_str_attempted", "total_str_landed", "total_str_attempted",
    "td_landed", "td_attempted", "submission_attempts", "knockdowns",
)

@dataclass
class FighterHistory:
    bouts: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    recent_outcomes: deque = None
    metric_history: dict = None
    def __post_init__(self):
        if self.recent_outcomes is None: self.recent_outcomes=deque(maxlen=5)
        if self.metric_history is None: self.metric_history=defaultdict(list)

    def form_win_rate(self, window=5):
        vals=list(self.recent_outcomes)[-window:]
        return sum(vals)/len(vals) if vals else None

    def metric_mean(self, metric, window=5):
        vals=self.metric_history.get(metric,[])
        vals=vals[-window:]
        return sum(vals)/len(vals) if vals else None

def _safe_div(a,b):
    return float(a)/float(b) if b not in (None,0,"", "0") and a is not None else None

def _as_float(v):
    if v in (None,"","NA","na"): return None
    try: return float(v)
    except (ValueError,TypeError): return None

def _diff(a,b):
    if a is None or b is None: return None
    return a-b

def build_pre_fight_features(bouts: Iterable[dict], date_key="date",
                             red_key="red_name", blue_key="blue_name",
                             outcome_key="y", metric_names=DEFAULT_METRICS,
                             windows=(3,5)):
    """Return sorted rows with pre-fight feature snapshots.

    y convention: 1=red wins, 0=blue wins, .5=draw. For each bout, snapshots are
    emitted first; only then are that bout's result and stats incorporated.
    Missing values stay null (no fabricated values).
    """
    histories=defaultdict(FighterHistory)
    elo_ratings=defaultdict(lambda:1500.0)
    rows=sorted(list(bouts),key=lambda r:r.get(date_key,""))
    out=[]
    for row in rows:
        red=row[red_key]; blue=row[blue_key]
        hr=histories[red]; hb=histories[blue]
        r_elo=elo_ratings[red]; b_elo=elo_ratings[blue]
        feat={
            "date":row.get(date_key,""),
            "red_name":red,"blue_name":blue,
            "red_bouts_pre":hr.bouts,"blue_bouts_pre":hb.bouts,
            "red_win_rate_career_pre":_safe_div(hr.wins,hr.bouts),
            "blue_win_rate_career_pre":_safe_div(hb.wins,hb.bouts),
            "red_elo_pre":r_elo,"blue_elo_pre":b_elo,
            "elo_diff_pre":r_elo-b_elo,
        }
        for window in windows:
            feat[f"red_form_win_rate_{window}_pre"]=hr.form_win_rate(window)
            feat[f"blue_form_win_rate_{window}_pre"]=hb.form_win_rate(window)
            feat[f"form_win_rate_diff_{window}_pre"]=_diff(
                feat[f"red_form_win_rate_{window}_pre"],feat[f"blue_form_win_rate_{window}_pre"])
            for metric in metric_names:
                rv=hr.metric_mean(metric,window); bv=hb.metric_mean(metric,window)
                feat[f"red_{metric}_avg_{window}_pre"]=rv
                feat[f"blue_{metric}_avg_{window}_pre"]=bv
                feat[f"{metric}_avg_diff_{window}_pre"]=_diff(rv,bv)
        # Derived historical rate feature snapshots
        for side,h in (("red",hr),("blue",hb)):
            sl=h.metric_history.get("sig_str_landed",[])
            sa=h.metric_history.get("sig_str_attempted",[])
            tdl=h.metric_history.get("td_landed",[])
            tda=h.metric_history.get("td_attempted",[])
            feat[f"{side}_sig_str_accuracy_pre"]=_safe_div(sum(sl),sum(sa)) if sl and sa else None
            feat[f"{side}_td_accuracy_pre"]=_safe_div(sum(tdl),sum(tda)) if tdl and tda else None
        feat["sig_str_accuracy_diff_pre"]=_diff(feat["red_sig_str_accuracy_pre"],feat["blue_sig_str_accuracy_pre"])
        feat["td_accuracy_diff_pre"]=_diff(feat["red_td_accuracy_pre"],feat["blue_td_accuracy_pre"])
        # Retain target and metadata in row for downstream supervised learning
        feat[outcome_key]=row.get(outcome_key)
        feat["event_name"]=row.get("event_name","")
        feat["method"]=row.get("method","")
        feat["weight_class"]=row.get("weight_class","")
        out.append(feat)

        # Update histories after snapshot (strict temporal order)
        y=_as_float(row.get(outcome_key))
        if y is not None:
            if y==1:
                hr.wins+=1; hb.losses+=1; hr.recent_outcomes.append(1); hb.recent_outcomes.append(0)
            elif y==0:
                hb.wins+=1; hr.losses+=1; hr.recent_outcomes.append(0); hb.recent_outcomes.append(1)
            elif y==0.5:
                hr.draws+=1; hb.draws+=1; hr.recent_outcomes.append(0.5); hb.recent_outcomes.append(0.5)
            hr.bouts+=1; hb.bouts+=1
            # Elo update from expectation computed before bout
            expected=1/(1+10**((b_elo-r_elo)/400))
            k=32
            elo_ratings[red]=r_elo+k*(y-expected)
            elo_ratings[blue]=b_elo+k*((1-y)-(1-expected))
        # accumulate post-bout statistics from the just-completed fight
        for metric in metric_names:
            rv=_as_float(row.get("red_"+metric)); bv=_as_float(row.get("blue_"+metric))
            if rv is not None: hr.metric_history[metric].append(rv)
            if bv is not None: hb.metric_history[metric].append(bv)
    return out

def validate_no_future_leakage(feature_rows, target_key="y"):
    """Basic structural assertion: snapshots must have zero pre-fight experience for debutants."""
    for r in feature_rows:
        if r.get("red_bouts_pre",0)==0 and r.get("red_win_rate_career_pre") is not None:
            raise AssertionError("Debutant red fighter has non-null prior career win rate")
        if r.get("blue_bouts_pre",0)==0 and r.get("blue_win_rate_career_pre") is not None:
            raise AssertionError("Debutant blue fighter has non-null prior career win rate")
    return True
