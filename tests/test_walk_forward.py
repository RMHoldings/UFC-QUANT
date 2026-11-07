import csv, os, sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.walk_forward import walk_forward_report

def test_walk_forward_generates_expanding_folds(tmp_path):
    src=tmp_path/"features.csv"; report=tmp_path/"report.json"
    fields=["date","red_name","blue_name","y","elo_diff_pre","red_win_rate_pre","blue_win_rate_pre"]
    with src.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for i in range(120):
            w.writerow({"date":f"2020-{i//28+1:02d}-{i%28+1:02d}","red_name":f"R{i}","blue_name":f"B{i}","y":i%2,
                        "elo_diff_pre":(i%5)*20,"red_win_rate_pre":i%10/10,"blue_win_rate_pre":(i+2)%10/10})
    r=walk_forward_report(src,report,folds=3,initial_train_fraction=.5)
    assert len(r["folds"])==3
    assert r["folds"][1]["train_n"]>r["folds"][0]["train_n"]
    assert r["aggregate_metrics"]["n"]==60
    assert r["weight_class_metrics"]
    assert r["predictions"][0]["weight_class"] == "Unknown"
