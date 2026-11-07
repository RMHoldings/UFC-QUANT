import os,sys,csv
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.pipeline import prepare_rows,outcome_from_result,create_feature_dataset,temporal_model_report
def test_result_normalization():
    assert outcome_from_result("W")==1
    assert outcome_from_result("L")==0
    assert outcome_from_result("D")==.5
    assert outcome_from_result("NC") is None
def test_pipeline_temporal_holdout(tmp_path):
    raw=tmp_path/"raw.csv"; feats=tmp_path/"features.csv"; report=tmp_path/"report.json"
    fields=["date","red_name","blue_name","result","event_name","method","weight_class","red_sig_str_landed","red_sig_str_attempted","blue_sig_str_landed","blue_sig_str_attempted"]
    rows=[]
    # deterministic series of synthetic bouts across fighters, synthetic only for pipeline test
    for i in range(60):
        rows.append({"date":f"2020-{(i//28)+1:02d}-{(i%28)+1:02d}","red_name":f"F{i%7}","blue_name":f"F{(i+2)%7}",
        "result":"W" if i%2 else "L","event_name":"Test","method":"Decision","weight_class":"LW",
        "red_sig_str_landed":str(20+i%8),"red_sig_str_attempted":str(40+i%8),
        "blue_sig_str_landed":str(15+i%6),"blue_sig_str_attempted":str(35+i%6)})
    with raw.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    raw_n,eligible_n,feat_n=create_feature_dataset(str(raw),str(feats))
    assert raw_n==60 and eligible_n==60 and feat_n==60
    r=temporal_model_report(str(feats),str(report),.7)
    assert r["train_n"]==42 and r["test_n"]==18
    assert r["feature_count"]>0 and "brier" in r["metrics"]
