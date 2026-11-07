import os,sys,csv
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.dataset_audit import audit_csv
def test_audit_detects_duplicate_and_invalid_pair(tmp_path):
    p=tmp_path/"data.csv"
    fields=["fight_url","red_sig_str_landed","red_sig_str_attempted","blue_sig_str_landed","blue_sig_str_attempted"]
    rows=[{"fight_url":"url1","red_sig_str_landed":"12","red_sig_str_attempted":"10","blue_sig_str_landed":"5","blue_sig_str_attempted":"8"},
          {"fight_url":"url1","red_sig_str_landed":"","red_sig_str_attempted":"","blue_sig_str_landed":"3","blue_sig_str_attempted":"5"}]
    with p.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    report=audit_csv(str(p))
    assert report["duplicate_fight_url_count"]==1
    assert report["invariant_violation_count"]==1
    assert "duplicate_fight_urls" in report["warnings"]
def test_empty_dataset(tmp_path):
    p=tmp_path/"empty.csv";p.write_text("fight_url\\n")
    assert audit_csv(str(p))["row_count"]==0
