"""Parse UFCStats fight-details pages for totals and round-level statistics.
HTML structure varies over time; parser extracts the Totals table by recognizable headers,
and returns explicit missing/parse warnings instead of fabricating stats.
"""
from __future__ import annotations
import re
from collections import defaultdict
from bs4 import BeautifulSoup

def _clean(s):
    return re.sub(r"\s+"," ",s or "").strip()

def _texts(cell):
    # UFCStats often puts two fighter values in paired <p> elements within a table cell.
    ps=cell.select("p")
    vals=[_clean(p.get_text(" ",strip=True)) for p in ps if _clean(p.get_text(" ",strip=True))]
    if len(vals)>=2: return vals[:2]
    raw=_clean(cell.get_text(" ",strip=True))
    # Rendered pair values often concatenate with whitespace; avoid unsafe split guesses.
    return [raw] if raw else []

def _pair_from_text(text):
    s=_clean(text)
    m=re.match(r"^(\d+)\s+of\s+(\d+)$",s,re.I)
    if m: return int(m.group(1)),int(m.group(2))
    return None

def _int_or_none(s):
    try: return int(_clean(s))
    except (ValueError,TypeError): return None

def _time_seconds(s):
    m=re.match(r"^(\d+):(\d{2})$",_clean(s))
    if not m: return None
    return int(m.group(1))*60+int(m.group(2))

def _header_text(th):
    return _clean(th.get_text(" ",strip=True)).lower().replace("%"," %")

def _find_totals_table(soup):
    candidates=[]
    for table in soup.select("table"):
        headers=[_header_text(th) for th in table.select("thead th")]
        if not headers:
            first=table.select_one("tr")
            headers=[_header_text(x) for x in first.select("th")] if first else []
        normalized=" ".join(headers)
        score=sum(term in normalized for term in ("fighter","kd","sig. str.","total str.","td","sub. att","ctrl"))
        if score>=5 and "sig. str." in normalized and "fighter" in normalized:
            candidates.append((score,table,headers))
    if not candidates: return None,None
    candidates.sort(key=lambda x:x[0],reverse=True)
    return candidates[0][1],candidates[0][2]

def parse_totals_html(html):
    soup=BeautifulSoup(html,"lxml")
    table,headers=_find_totals_table(soup)
    if table is None:
        return {"fighters":{},"warnings":["totals_table_not_found"],"source":"UFCStats"}
    # resolve header indexes using aliases
    aliases={
      "kd":("kd",),"sig":("sig. str.","sig str"),"total":("total str.","total str"),
      "td":("td",),"sub":("sub. att","sub att"),"rev":("rev",),"ctrl":("ctrl",)
    }
    indexes={}
    for key,terms in aliases.items():
        for i,h in enumerate(headers):
            if any(term in h for term in terms):
                # TD columns: exact label to avoid TD % selecting instead
                if key=="td" and ("%" in h or "td %" in h): continue
                indexes[key]=i;break
    body_rows=table.select("tbody tr")
    if not body_rows: body_rows=table.select("tr")[1:]
    result={}
    warnings=[]
    for row in body_rows:
        cells=row.select("td")
        if not cells: continue
        names=[]
        for a in cells[0].select("a"):
            name=_clean(a.get_text(" ",strip=True))
            if name and name not in names: names.append(name)
        if len(names)<2:
            first_text=_clean(cells[0].get_text(" ",strip=True))
            # Known UFCStats table may put fighter names as paired <p> without links
            names=[_clean(p.get_text(" ",strip=True)) for p in cells[0].select("p")]
            names=[n for n in names if n]
        if len(names)<2:
            warnings.append("fighter_pair_not_parsed");continue
        cell_values={i:_texts(cells[i]) for i in range(len(cells))}
        fighter_stats={}
        for side,name in enumerate(names[:2]):
            stats={}
            def get_value(key):
                idx=indexes.get(key)
                if idx is None or idx>=len(cells): return None
                vals=cell_values.get(idx,[])
                return vals[side] if len(vals)>side else None
            pair=_pair_from_text(get_value("sig"))
            stats["sig_str_landed"]=pair[0] if pair else None
            stats["sig_str_attempted"]=pair[1] if pair else None
            pair=_pair_from_text(get_value("total"))
            stats["total_str_landed"]=pair[0] if pair else None
            stats["total_str_attempted"]=pair[1] if pair else None
            pair=_pair_from_text(get_value("td"))
            stats["td_landed"]=pair[0] if pair else None
            stats["td_attempted"]=pair[1] if pair else None
            stats["knockdowns"]=_int_or_none(get_value("kd"))
            stats["submission_attempts"]=_int_or_none(get_value("sub"))
            stats["reversals"]=_int_or_none(get_value("rev"))
            stats["control_time_seconds"]=_time_seconds(get_value("ctrl"))
            fighter_stats[name]=stats
        result.update(fighter_stats)
    if len(result)<2: warnings.append("fighter_stats_incomplete")
    return {"fighters":result,"warnings":warnings,"source":"UFCStats"}

def parse_totals_page(client,url):
    soup=client.get_soup(url)
    return parse_totals_html(str(soup))
