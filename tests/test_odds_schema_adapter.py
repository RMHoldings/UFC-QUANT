import json,sys,os,csv
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.odds_backtest import load_joined_predictions,simulate_bets

def test_favourite_underdog_schema(tmp_path):
    report=tmp_path/"pred.json"; odds=tmp_path/"odds.csv"
    report.write_text(json.dumps({"predictions":[{"date":"2023-09-16","red_name":"Alexa Grasso","blue_name":"Valentina Shevchenko","p_red_win":.6,"actual_red_win":1}]}))
    with odds.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["event_date","fighter1","fighter2","favourite","underdog","favourite_odds","underdog_odds"])
        w.writeheader()
        w.writerow({"event_date":"2023-09-16","fighter1":"Alexa Grasso","fighter2":"Valentina Shevchenko","favourite":"Valentina Shevchenko","underdog":"Alexa Grasso","favourite_odds":"1.7","underdog_odds":"2.4"})
    joined=load_joined_predictions(report,odds)
    assert len(joined)==1
    assert joined[0]["red_odds"]==2.4 and joined[0]["blue_odds"]==1.7
