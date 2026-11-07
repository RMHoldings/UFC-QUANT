import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from ufc_quant.ufcstats_fight_parser import parse_totals_html
HTML="""<html><body><table><thead><tr>
<th><p>Fighter</p></th><th><p>KD</p></th><th><p>Sig. str.</p></th>
<th><p>Sig. str. %</p></th><th><p>Total str.</p></th><th><p>Td</p></th>
<th><p>Td %</p></th><th><p>Sub. att</p></th><th><p>Rev.</p></th><th><p>Ctrl</p></th>
</tr></thead><tbody><tr><td><p><a>A Fighter</a></p><p><a>B Fighter</a></p></td>
<td><p>1</p><p>0</p></td><td><p>10 of 20</p><p>5 of 15</p></td>
<td><p>50%</p><p>33%</p></td><td><p>25 of 40</p><p>12 of 30</p></td>
<td><p>2 of 3</p><p>0 of 1</p></td><td><p>66%</p><p>0%</p></td>
<td><p>1</p><p>0</p></td><td><p>0</p><p>1</p></td><td><p>2:30</p><p>0:15</p></td>
</tr></tbody></table></body></html>"""
def test_parse_totals_table_two_fighters():
    result=parse_totals_html(HTML)
    assert not result["warnings"]
    a=result["fighters"]["A Fighter"]
    b=result["fighters"]["B Fighter"]
    assert a["sig_str_landed"]==10 and a["sig_str_attempted"]==20
    assert a["td_landed"]==2 and a["td_attempted"]==3
    assert a["control_time_seconds"]==150
    assert b["knockdowns"]==0 and b["control_time_seconds"]==15
def test_missing_table_warning():
    result=parse_totals_html("<html><body><p>no stats table</p></body></html>")
    assert "totals_table_not_found" in result["warnings"]
