import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.quality import audit_fighter_stats
class F:
    name="Test Fighter"
    slpm=3.2; str_acc=45; sapm=2.1; str_def=55
    td_avg=1.2; td_acc=30; td_def=70; sub_avg=0.4
def test_complete_stats():
    F.td_def=70
    assert audit_fighter_stats(F())["ok"]
def test_missing_stats():
    F.td_def=None
    result=audit_fighter_stats(F())
    assert not result["ok"] and "td_def" in result["missing"]
