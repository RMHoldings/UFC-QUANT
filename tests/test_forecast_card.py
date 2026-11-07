import csv, json, os, sys
from pathlib import Path
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.forecast_card import predict_card

def _dataset(path, n=40):
    fighters=[f"Fighter {i}" for i in range(12)]
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["date","red_name","blue_name","y","red_sig_str_landed","red_sig_str_attempted","blue_sig_str_landed","blue_sig_str_attempted"])
        w.writeheader()
        for i in range(n):
            a=fighters[i%12]; b=fighters[(i*5+3)%12]
            if a==b: b=fighters[(i+1)%12]
            y=i%2
            w.writerow({"date":f"2020-{(i//28)+1:02d}-{(i%28)+1:02d}","red_name":a,"blue_name":b,"y":y,
                "red_sig_str_landed":12+(i%7),"red_sig_str_attempted":25+(i%9),
                "blue_sig_str_landed":8+(i%5),"blue_sig_str_attempted":22+(i%8)})

def test_forecast_card_creates_historical_predictions_and_cutoff(tmp_path):
    hist=tmp_path/"hist.csv"; card=tmp_path/"card.json"; out=tmp_path/"forecast.json"
    _dataset(hist,45)
    card.write_text(json.dumps({"event":{"name":"Test card","date":"2021-01-01"},"fights":[
        {"fighter_a":"Fighter 0","fighter_b":"Fighter 1"},
        {"fighter_a":"Unknown debutant","fighter_b":"Fighter 2"}]}),encoding="utf-8")
    result=predict_card(hist,card,out,min_bouts=30)
    data=json.loads(out.read_text(encoding="utf-8"))
    assert result["historical_bouts_used"]==45
    assert len(result["scored_fights"])==2
    assert 0<=data["fights"][0]["empirical_prediction"]["p_a"]<=1
    assert data["fights"][1]["empirical_prediction"]["fighter_a_history_available"] is False
    assert data["forecast_metadata"]["event_date_cutoff"]=="2021-01-01"

def test_forecast_excludes_history_after_event_date(tmp_path):
    hist=tmp_path/"hist.csv"; card=tmp_path/"card.json"; out=tmp_path/"forecast.json"
    _dataset(hist,40)
    card.write_text(json.dumps({"event":{"date":"2020-02-20"},"fights":[{"fighter_a":"Fighter 0","fighter_b":"Fighter 1"}]}),encoding="utf-8")
    try:
        predict_card(hist,card,out,min_bouts=30)
    except ValueError as e:
        assert "before the event" in str(e)
    else:
        # If enough pre-cutoff records exist, metadata must show latest date before cutoff.
        data=json.loads(out.read_text(encoding="utf-8"))
        assert data["forecast_metadata"]["history_date_range"][1] < "2020-02-20"
