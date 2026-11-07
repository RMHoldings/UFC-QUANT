import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.pre_fight_features import build_pre_fight_features,validate_no_future_leakage
def test_snapshots_pre_fight_and_updates_after():
    bouts=[
      {"date":"2020-01-01","red_name":"A","blue_name":"B","y":1,"red_sig_str_landed":10,"red_sig_str_attempted":20,"blue_sig_str_landed":5,"blue_sig_str_attempted":10},
      {"date":"2020-02-01","red_name":"A","blue_name":"C","y":1,"red_sig_str_landed":15,"red_sig_str_attempted":25,"blue_sig_str_landed":4,"blue_sig_str_attempted":9},
    ]
    rows=build_pre_fight_features(bouts,metric_names=("sig_str_landed","sig_str_attempted"))
    assert rows[0]["red_bouts_pre"]==0 and rows[0]["red_win_rate_career_pre"] is None
    assert rows[1]["red_bouts_pre"]==1 and rows[1]["red_win_rate_career_pre"]==1.0
    assert rows[1]["red_sig_str_landed_avg_3_pre"]==10.0
    assert validate_no_future_leakage(rows)
def test_no_target_used_before_result():
    bouts=[{"date":"2020-01-01","red_name":"A","blue_name":"B","y":0}]
    rows=build_pre_fight_features(bouts,metric_names=())
    assert rows[0]["red_bouts_pre"]==0 and rows[0]["elo_diff_pre"]==0
