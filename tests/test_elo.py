import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.elo import Elo,build_elo_snapshots
def test_equal_ratings_expectation():
    e=Elo()
    assert abs(e.expected("A","B")-0.5)<1e-9
def test_winner_rating_rises():
    e=Elo()
    pre=e.update("A","B",1)
    assert e.rating("A")>pre["rating_a_pre"]
    assert e.rating("B")<pre["rating_b_pre"]
def test_snapshot_before_update():
    rows=[{"date":"2024-01-01","red_name":"A","blue_name":"B","y":1},
          {"date":"2024-02-01","red_name":"A","blue_name":"C","y":1}]
    out=build_elo_snapshots(rows)
    assert out[0]["elo_diff_pre"]==0
    assert out[1]["rating_a_pre"]>1500
