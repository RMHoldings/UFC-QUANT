import os,sys,csv
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.external_dataset import normalize_external_csv
import pytest
def test_normalize_external_winner(tmp_path):
    src=tmp_path/"src.csv";out=tmp_path/"out.csv"
    with src.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["event_date","fight_url","fighter_1","fighter_2","winner","method"])
        w.writeheader();w.writerows([
        {"event_date":"2020-01-01","fight_url":"id1","fighter_1":"A","fighter_2":"B","winner":"A","method":"Decision"},
        {"event_date":"2020-01-02","fight_url":"id2","fighter_1":"C","fighter_2":"D","winner":"Draw","method":"Decision"},
        {"event_date":"2020-01-03","fight_url":"id3","fighter_1":"E","fighter_2":"F","winner":"F","method":"KO"}])
    summary=normalize_external_csv(str(src),str(out))
    assert summary["normalized_rows"]==2
    with out.open() as f: rows=list(csv.DictReader(f))
    assert [r["y"] for r in rows]==["1","0"]
def test_fails_closed_without_winner(tmp_path):
    src=tmp_path/"src.csv";out=tmp_path/"out.csv"
    src.write_text("date,fighter_1,fighter_2\n2020-01-01,A,B\n")
    with pytest.raises(ValueError,match="winner"):
        normalize_external_csv(str(src),str(out))
