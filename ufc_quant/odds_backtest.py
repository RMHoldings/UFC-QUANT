"""Odds-aware evaluation and staking simulation. Requires historical pre-fight decimal odds."""
from __future__ import annotations
import argparse,csv,json,math
from datetime import datetime
from pathlib import Path
import numpy as np
from .backtest import evaluate

def load_joined_predictions(predictions_json, odds_csv):
    report=json.loads(Path(predictions_json).read_text(encoding="utf-8"))
    preds=report.get("predictions",[])
    with open(odds_csv,newline="",encoding="utf-8-sig") as f: odds=list(csv.DictReader(f))
    def norm(s): return " ".join((s or "").strip().lower().split())
    def norm_date(s):
        raw=(s or "").strip()
        for fmt in ("%Y-%m-%d","%B %d, %Y","%b %d, %Y","%m/%d/%Y","%d/%m/%Y"):
            try: return datetime.strptime(raw,fmt).date().isoformat()
            except ValueError: pass
        return raw
    index={}
    for row in odds:
        date=norm_date(row.get("date") or row.get("event_date") or "")
        red=norm(row.get("red_name") or row.get("fighter_a") or row.get("fighter_1") or row.get("fighter1"))
        blue=norm(row.get("blue_name") or row.get("fighter_b") or row.get("fighter_2") or row.get("fighter2"))
        if not date or not red or not blue: continue
        try:
            raw_a=row.get("red_odds") or row.get("fighter_a_odds") or row.get("odds_1")
            raw_b=row.get("blue_odds") or row.get("fighter_b_odds") or row.get("odds_2")
            if raw_a and raw_b:
                a=float(raw_a); b=float(raw_b)
                if a>1 and b>1:
                    index[(date,red,blue)]=(a,b,row)
                    index[(date,blue,red)]=(b,a,row)
                    continue
            # Common dataset schema: favourite/underdog names and decimal prices
            fav=norm(row.get("favourite") or row.get("favorite"))
            dog=norm(row.get("underdog"))
            fav_odds=float(row.get("favourite_odds") or row.get("favorite_odds"))
            dog_odds=float(row.get("underdog_odds"))
            if fav_odds<=1 or dog_odds<=1: continue
            if fav==red and dog==blue:
                index[(date,red,blue)]=(fav_odds,dog_odds,row)
                index[(date,blue,red)]=(dog_odds,fav_odds,row)
            elif fav==blue and dog==red:
                index[(date,red,blue)]=(dog_odds,fav_odds,row)
                index[(date,blue,red)]=(fav_odds,dog_odds,row)
        except (TypeError,ValueError): continue
    joined=[]
    for p in preds:
        key=(norm_date(p.get("date","")),norm(p.get("red_name")),norm(p.get("blue_name")))
        match=index.get(key)
        if not match: continue
        a,b,row=match
        joined.append({**p,"red_odds":a,"blue_odds":b,"source_row":row})
    return joined

def simulate_bets(joined, edge_threshold=.03, stake_fraction=.01, bankroll=1000.0):
    if not 0<stake_fraction<=.05: raise ValueError("stake_fraction deve essere >0 e <= 5% (limite prudenziale).")
    if edge_threshold<0: raise ValueError("edge_threshold deve essere >=0")
    cash=float(bankroll); peak=cash; max_dd=0.; bets=[]; profits=[]
    market_y=[]; market_p=[]
    by_weight_class={}
    for p in joined:
        odds_r=float(p["red_odds"]); odds_b=float(p["blue_odds"])
        ir=1/odds_r; ib=1/odds_b; fair=ir/(ir+ib)
        market_y.append(int(p["actual_red_win"])); market_p.append(fair)
    for p in joined:
        prob=float(p["p_red_win"]); actual=int(p["actual_red_win"])
        odds_r=float(p["red_odds"]); odds_b=float(p["blue_odds"])
        # remove bookmaker overround by normalizing implied probabilities
        imp_r=1/odds_r; imp_b=1/odds_b; fair_r=imp_r/(imp_r+imp_b); fair_b=imp_b/(imp_r+imp_b)
        candidates=[("red",prob,odds_r,fair_r,actual==1),("blue",1-prob,odds_b,fair_b,actual==0)]
        choice=None
        for side,model_p,odds,fair_p,won in candidates:
            edge=model_p-fair_p
            ev=model_p*odds-1
            if edge>=edge_threshold and ev>0:
                choice=(side,model_p,odds,edge,ev,won);break
        if choice is None: continue
        side,model_p,odds,edge,ev,won=choice
        stake=cash*stake_fraction
        profit=stake*(odds-1) if won else -stake
        cash+=profit; peak=max(peak,cash); max_dd=max(max_dd,(peak-cash)/peak if peak else 0)
        bets.append({"date":p.get("date"),"side":side,"model_probability":model_p,"odds":odds,"edge":edge,"expected_value":ev,"stake":stake,"won":bool(won),"profit":profit,"bankroll_after":cash})
        profits.append(profit)
        wc=p.get("weight_class") or "Unknown"
        stats=by_weight_class.setdefault(wc,{"bets_n":0,"wins":0,"profit":0.0,"staked":0.0})
        stats["bets_n"]+=1; stats["wins"]+=int(bool(won)); stats["profit"]+=profit; stats["staked"]+=stake
    n=len(bets); total_staked=sum(x["stake"] for x in bets); total_profit=sum(profits)
    weight_class_roi={k:{**v,"roi_on_staked":v["profit"]/v["staked"] if v["staked"] else None,
                         "win_rate":v["wins"]/v["bets_n"] if v["bets_n"] else None,
                         "reliability_note":"Descriptive only; caution for fewer than 30 bets." if v["bets_n"]<30 else "At least 30 bets; still not proof of persistent edge."}
                     for k,v in sorted(by_weight_class.items())}
    market_metrics=evaluate(np.array(market_y),np.array(market_p)).__dict__ if market_y else None
    return {"matched_n":len(joined),"market_fair_probability_metrics":market_metrics,
            "weight_class_roi":weight_class_roi,"bets_n":n,"initial_bankroll":bankroll,"final_bankroll":cash,"profit":total_profit,
            "roi_on_staked":total_profit/total_staked if total_staked else None,"yield_pct":100*total_profit/total_staked if total_staked else None,
            "max_drawdown_pct":100*max_dd,"win_rate":sum(x["won"] for x in bets)/n if n else None,
            "avg_edge":sum(x["edge"] for x in bets)/n if n else None,"bet_log":bets,
            "method":"decimal odds; overround normalized for edge; positive model EV; fixed fractional stake; market fair-probability metrics and descriptive weight-class ROI. No claim of profitability without sufficiently large out-of-sample sample."}
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("walkforward_predictions_json");ap.add_argument("historical_odds_csv")
    ap.add_argument("--edge",type=float,default=.03);ap.add_argument("--stake",type=float,default=.01);ap.add_argument("--bankroll",type=float,default=1000)
    ap.add_argument("--report",default="ufc_roi_report.json");a=ap.parse_args()
    joined=load_joined_predictions(a.walkforward_predictions_json,a.historical_odds_csv)
    r=simulate_bets(joined,a.edge,a.stake,a.bankroll);Path(a.report).write_text(json.dumps(r,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in r.items() if k!="bet_log"},indent=2))
if __name__=="__main__":main()
