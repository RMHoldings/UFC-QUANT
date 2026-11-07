"""Download a public UFCStats-derived historical CSV and write source provenance."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
import requests

DEFAULT_URL="https://huggingface.co/datasets/01x3ATM3/UFC_FIGHT_DATA_2013_TO_2025/resolve/main/output.csv"
REQUIRED_COLUMNS={"event_date_iso","header_fighter_a_name","header_fighter_b_name","header_winner_name"}


def download_history(output_csv="ufc_history_source.csv", provenance_json="ufc_history_provenance.json", url=DEFAULT_URL, timeout=60, session=None):
    client=session or requests
    target=Path(output_csv); target.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp_name=tempfile.mkstemp(prefix=target.name+".",suffix=".part",dir=str(target.parent)); os.close(fd)
    tmp=Path(tmp_name)
    try:
        response=client.get(url,timeout=timeout,stream=True,headers={"User-Agent":"UFCQuant research downloader/1.0"})
        response.raise_for_status()
        with tmp.open("wb") as out:
            for chunk in response.iter_content(chunk_size=1024*1024):
                if chunk: out.write(chunk)
        digest=hashlib.sha256(tmp.read_bytes()).hexdigest()
        with tmp.open("r",newline="",encoding="utf-8-sig") as f:
            reader=csv.DictReader(f)
            columns=set(reader.fieldnames or [])
            missing=sorted(REQUIRED_COLUMNS-columns)
            if missing: raise ValueError("Downloaded CSV has incompatible schema; missing columns: "+", ".join(missing))
            row_count=sum(1 for _ in reader)
        if row_count<100: raise ValueError(f"Downloaded dataset unexpectedly small ({row_count} rows); refusing to replace output.")
        os.replace(tmp,target)
        provenance={"source_url":url,"source_dataset":"01x3ATM3/UFC_FIGHT_DATA_2013_TO_2025",
                   "source_description":"UFCStats-derived one-row-per-bout dataset; source snapshot published with data through 2025-05-31 according to dataset viewer/card.",
                   "downloaded_at_utc":datetime.now(timezone.utc).isoformat(),"file":str(target),
                   "row_count":row_count,"columns":sorted(columns),"sha256":digest,
                   "validation":{"required_columns_present":True,"minimum_rows_100":True},
                   "warning":"Public third-party dataset; not independently source-audited. Check source terms and run dataset audit before modeling."}
        Path(provenance_json).write_text(json.dumps(provenance,indent=2),encoding="utf-8")
        return provenance
    finally:
        if tmp.exists(): tmp.unlink()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output",default="ufc_history_source.csv");ap.add_argument("--provenance",default="ufc_history_provenance.json")
    ap.add_argument("--url",default=DEFAULT_URL);ap.add_argument("--timeout",type=float,default=60)
    args=ap.parse_args();result=download_history(args.output,args.provenance,args.url,args.timeout)
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
