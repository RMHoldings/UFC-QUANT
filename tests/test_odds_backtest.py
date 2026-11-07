import json,sys,os,csv
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.odds_backtest import load_joined_predictions,simulate_bets
import pytest

def test_join_and_roi(tmp_path):
    report=tmp_path/"pred.json"; odds=tmp_path/"odds.csv"
    report.write_text(json.dumps({"predictions":[{"date":"2024-01-01","red_name":"Alpha","blue_name":"Beta","p_red_win":.7,"actual_red_win":1,"weight_class":"Lightweight"}]}))
    with odds.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["date","red_name","blue_name","red_odds","blue_odds"]);w.writeheader()
        w.writerow({"date":"2024-01-01","red_name":"Alpha","blue_name":"Beta","red_odds":1.8,"blue_odds":2.1})
    joined=load_joined_predictions(report,odds)
    assert len(joined)==1
    result=simulate_bets(joined,edge_threshold=.03,stake_fraction=.01,bankroll=1000)
    assert result["bets_n"]==1 and result["profit"]==pytest.approx(8.0)
    assert result["market_fair_probability_metrics"]["n"] == 1
    assert result["weight_class_roi"]["Lightweight"]["bets_n"] == 1

def test_stake_cap(tmp_path):
    with pytest.raises(ValueError):simulate_bets([],stake_fraction=.10)
