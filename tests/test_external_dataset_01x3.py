import csv, os, sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.external_dataset import normalize_external_csv

def test_adapter_01x3atm3_schema(tmp_path):
    src=tmp_path/"source.csv"; dst=tmp_path/"normalized.csv"
    with src.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["event_date_iso","header_fighter_a_name","header_fighter_b_name","header_winner_name","FightID_generated"])
        w.writeheader()
        w.writerow({"event_date_iso":"2024-01-01","header_fighter_a_name":"Fighter A","header_fighter_b_name":"Fighter B","header_winner_name":"Fighter A","FightID_generated":"abc"})
        w.writerow({"event_date_iso":"2024-01-02","header_fighter_a_name":"Fighter C","header_fighter_b_name":"Fighter D","header_winner_name":"Fighter D","FightID_generated":"def"})
    summary=normalize_external_csv(src,dst)
    assert summary["normalized_rows"]==2
    with dst.open() as f: rows=list(csv.DictReader(f))
    assert rows[0]["y"]=="1" and rows[1]["y"]=="0"
