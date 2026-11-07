import csv
from ufc_quant.walk_forward import walk_forward_report

def test_walk_forward_keeps_same_date_bouts_together_and_adds_calibration(tmp_path):
    src=tmp_path/"features.csv"; report=tmp_path/"report.json"
    fields=["date","red_name","blue_name","y","elo_diff_pre","red_win_rate_pre","blue_win_rate_pre"]
    with src.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for day in range(1,61):
            for bout in range(2):
                i=(day-1)*2+bout
                w.writerow({"date":f"2020-{(day-1)//28+1:02d}-{(day-1)%28+1:02d}","red_name":f"R{i}","blue_name":f"B{i}","y":i%2,
                            "elo_diff_pre":(i%5)*20,"red_win_rate_pre":i%10/10,"blue_win_rate_pre":(i+2)%10/10})
    r=walk_forward_report(src,report,folds=3,initial_train_fraction=.5)
    assert r["aggregate_50_50_baseline_metrics"]["brier"]==0.25
    assert "aggregate_calibration_bins" in r
    assert "brier_delta_bootstrap_ci_vs_50_50" in r
    for fold in r["folds"]:
        assert fold["train_end"] < fold["test_start"]
        assert fold["calibration_bins"] is not None
