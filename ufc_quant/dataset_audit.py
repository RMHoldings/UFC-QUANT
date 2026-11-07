"""Dataset QA report: coverage, missingness, duplicates, and value sanity checks."""
from __future__ import annotations
import argparse,csv,json,math
from collections import Counter

STAT_COLUMNS=("red_sig_str_landed","red_sig_str_attempted","red_total_str_landed","red_total_str_attempted",
"red_td_landed","red_td_attempted","red_knockdowns","red_submission_attempts","red_control_time_seconds",
"blue_sig_str_landed","blue_sig_str_attempted","blue_total_str_landed","blue_total_str_attempted",
"blue_td_landed","blue_td_attempted","blue_knockdowns","blue_submission_attempts","blue_control_time_seconds")

def _numeric(v):
    if v in (None,"","NA","na"): return None
    try: return float(v)
    except (TypeError,ValueError): return None

def audit_csv(path):
    with open(path,newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    n=len(rows)
    if n==0: return {"row_count":0,"errors":["empty_dataset"]}
    urls=[r.get("fight_url","").strip() for r in rows if r.get("fight_url","").strip()]
    dup_urls=[u for u,c in Counter(urls).items() if c>1]
    columns=list(rows[0].keys())
    present_stats=[c for c in STAT_COLUMNS if c in columns]
    missing_by_col={}
    ranges={}
    for c in present_stats:
        vals=[_numeric(r.get(c)) for r in rows]
        missing=sum(v is None for v in vals)
        missing_by_col[c]={"missing":missing,"coverage_pct":round(100*(n-missing)/n,2)}
        numeric=[v for v in vals if v is not None]
        if numeric:
            ranges[c]={"min":min(numeric),"max":max(numeric)}
    warnings=[]
    if dup_urls: warnings.append("duplicate_fight_urls")
    if not present_stats: warnings.append("stats_columns_not_present")
    # Validate basic arithmetic/values when parsed
    invalid=[]
    for i,r in enumerate(rows):
        for side in ("red","blue"):
            for landed,attempted in ((f"{side}_sig_str_landed",f"{side}_sig_str_attempted"),
                                     (f"{side}_total_str_landed",f"{side}_total_str_attempted"),
                                     (f"{side}_td_landed",f"{side}_td_attempted")):
                l=_numeric(r.get(landed)); a=_numeric(r.get(attempted))
                if l is not None and a is not None and (l<0 or a<0 or l>a):
                    invalid.append({"row":i+2,"pair":[landed,attempted],"values":[l,a]})
    if invalid: warnings.append("stat_pair_invariant_violations")
    parse_warnings=Counter()
    if "stats_parse_warnings" in columns:
        for r in rows:
            for token in (r.get("stats_parse_warnings") or "").split(";"):
                if token.strip(): parse_warnings[token.strip()]+=1
    return {
      "row_count":n,"unique_fight_url_count":len(set(urls)),"duplicate_fight_url_count":len(dup_urls),
      "columns":columns,"stat_columns_found":present_stats,"stat_coverage":missing_by_col,
      "numeric_ranges":ranges,"parse_warning_counts":dict(parse_warnings),
      "invariant_violation_count":len(invalid),"invariant_violations_sample":invalid[:20],
      "warnings":warnings,"errors":[]
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--json",default="dataset_qa.json")
    ap.add_argument("--markdown",default="dataset_qa.md")
    args=ap.parse_args()
    report=audit_csv(args.csv_path)
    with open(args.json,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    with open(args.markdown,"w",encoding="utf-8") as f:
        f.write("# UFC Dataset Quality Audit\\n\\n")
        f.write(f"- Rows: {report['row_count']}\\n")
        f.write(f"- Unique fight URLs: {report.get('unique_fight_url_count',0)}\\n")
        f.write(f"- Duplicate URLs: {report.get('duplicate_fight_url_count',0)}\\n")
        f.write(f"- Invariant violations: {report.get('invariant_violation_count',0)}\\n\\n")
        f.write("## Statistic coverage\\n\\n| Column | Missing | Coverage |\\n|---|---:|---:|\\n")
        for c,v in report.get("stat_coverage",{}).items():
            f.write(f"| {c} | {v['missing']} | {v['coverage_pct']}% |\\n")
        f.write("\\n## Warnings\\n\\n")
        for w in report.get("warnings",[]): f.write(f"- {w}\\n")
        if not report.get("warnings"): f.write("- None\\n")
    print(json.dumps({"rows":report["row_count"],"warnings":report.get("warnings",[]),"invariant_violations":report.get("invariant_violation_count",0)},indent=2))
    print("Saved:",args.json,args.markdown)
if __name__=="__main__": main()
