import json, os, sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.report import build_report

def test_report_uses_empirical_prediction(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config=json.loads(open(os.path.join(os.path.dirname(os.path.dirname(__file__)),"config.json"),encoding="utf-8").read())
    card={"event":{"name":"Historical model test","date":"2026-12-01"},"fights":[
        {"fighter_a":"A","fighter_b":"B","empirical_prediction":{"p_a":0.72,"p_b":0.28,"model":"historical logistic regression"}}]}
    html=build_report(card,config)
    assert "historical logistic regression win probabilities" in html
    assert "72.0%" in html and "28.0%" in html
