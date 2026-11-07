import csv, os, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.combined_dataset import normalize_combined_csv


def test_combined_csv_maps_explicit_result_and_odds(tmp_path):
    src=tmp_path/"combined.csv"; normalized=tmp_path/"normalized.csv"; odds=tmp_path/"odds.csv"; summary=tmp_path/"summary.json"
    fields=["event_date","event_name","weight_class","fighter1","fighter2","outcome","favourite","underdog","favourite_odds","underdog_odds"]
    rows=[
        {"event_date":"2023-09-16","event_name":"UFC event","weight_class":"Flyweight","fighter1":"A","fighter2":"B","outcome":"fighter","favourite":"B","underdog":"A","favourite_odds":"1.6","underdog_odds":"2.4"},
        {"event_date":"2023-09-16","event_name":"UFC event","weight_class":"Bantamweight","fighter1":"C","fighter2":"D","outcome":"fighter2","favourite":"C","underdog":"D","favourite_odds":"1.7","underdog_odds":"2.2"},
        {"event_date":"2023-09-16","event_name":"UFC event","weight_class":"Welterweight","fighter1":"E","fighter2":"F","outcome":"Draw","favourite":"E","underdog":"F","favourite_odds":"1.8","underdog_odds":"2.0"},
        {"event_date":"2023-09-16","event_name":"UFC event","weight_class":"Lightweight","fighter1":"G","fighter2":"H","outcome":"unresolved","favourite":"G","underdog":"H","favourite_odds":"1.8","underdog_odds":"2.0"},
    ]
    with src.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    result=normalize_combined_csv(src,normalized,odds,summary)
    assert result["normalized_bouts"]==2
    assert result["odds_rows"]==2
    with normalized.open() as f: norm=list(csv.DictReader(f))
    assert [r["y"] for r in norm]==["1","0"]
    with odds.open() as f: o=list(csv.DictReader(f))
    assert o[0]["favourite"]=="B" and float(o[0]["favourite_odds"])==1.6
    assert result["excluded_counts"]["draw_excluded"]==1
    assert result["excluded_counts"]["ambiguous_outcome_excluded"]==1


def test_combined_csv_requires_explicit_winner_schema(tmp_path):
    src=tmp_path/"src.csv";src.write_text("event_date,fighter1,fighter2\n2020-01-01,A,B\n")
    with pytest.raises(ValueError,match="outcome"):
        normalize_combined_csv(src,tmp_path/"norm.csv",tmp_path/"odds.csv")
