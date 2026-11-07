import os,sys,csv,json
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.pipeline import create_feature_dataset,temporal_model_report
def test_report_includes_elo_benchmark_and_calibration(tmp_path):
    raw=tmp_path/"raw.csv"; feat=tmp_path/"feat.csv"; report=tmp_path/"report.json"
    fields=["date","red_name","blue_name","result","event_name","method","weight_class","red_sig_str_landed","red_sig_str_attempted","blue_sig_str_landed","blue_sig_str_attempted"]
    rows=[]
    for i in range(60):
        rows.append({"date":f"2021-{(i//28)+1:02d}-{(i%28)+1:02d}","red_name":f"A{i%9}","blue_name":f"B{(i+1)%9}",
        "result":"W" if i%2 else "L","event_name":"Test","method":"Decision","weight_class":"LW",
        "red_sig_str_landed":str(20+i%8),"red_sig_str_attempted":str(40+i%8),
        "blue_sig_str_landed":str(15+i%6),"blue_sig_str_attempted":str(35+i%6)})
    with raw.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    create_feature_dataset(str(raw),str(feat))
    result=temporal_model_report(str(feat),str(report),.7)
    assert "elo_baseline_metrics" in result
    assert "calibration_bins" in result
    assert result["elo_baseline_metrics"]["n"]==18
