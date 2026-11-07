import csv, os, sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.empirical_backtest import normalized_to_features
import pytest

def test_normalized_to_features_temporal(tmp_path):
    src=tmp_path/"normalized.csv"; dst=tmp_path/"features.csv"
    with src.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["date","red_name","blue_name","y"])
        w.writeheader()
        for i in range(40):
            w.writerow({"date":f"2020-{(i//28)+1:02d}-{(i%28)+1:02d}","red_name":f"F{i%7}","blue_name":f"F{(i+2)%7}","y":i%2})
    res=normalized_to_features(src,dst)
    assert res["feature_rows"]==40
    with dst.open() as f: rows=list(csv.DictReader(f))
    assert rows[0]["red_bouts_pre"]=="0"

def test_rejects_too_few_rows(tmp_path):
    src=tmp_path/"n.csv"; dst=tmp_path/"f.csv"
    src.write_text("date,red_name,blue_name,y\n2020-01-01,A,B,1\n")
    with pytest.raises(ValueError,match="30"):
        normalized_to_features(src,dst)
