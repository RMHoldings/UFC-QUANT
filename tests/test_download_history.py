import csv, hashlib, json
from pathlib import Path
import pytest
from ufc_quant.download_history import download_history

class FakeResponse:
    def __init__(self, body): self.body=body
    def raise_for_status(self): pass
    def iter_content(self, chunk_size=1024): yield self.body

class FakeSession:
    def __init__(self, body): self.body=body; self.kwargs=None
    def get(self, url, **kwargs): self.kwargs=(url,kwargs); return FakeResponse(self.body)

def test_download_history_validates_and_records_provenance(tmp_path):
    header="event_date_iso,header_fighter_a_name,header_fighter_b_name,header_winner_name,FightID_generated\n"
    rows="".join(f"2020-01-{(i%28)+1:02d},A{i},B{i},A{i},id{i}\n" for i in range(105))
    body=(header+rows).encode()
    session=FakeSession(body)
    target=tmp_path/"history.csv"; metadata=tmp_path/"source.json"
    result=download_history(target,metadata,"https://fake.test/data.csv",session=session)
    assert result["row_count"]==105
    assert result["sha256"]==hashlib.sha256(body).hexdigest()
    assert json.loads(metadata.read_text())["source_url"]=="https://fake.test/data.csv"
    assert target.read_bytes()==body

def test_download_history_rejects_bad_schema_and_preserves_old_file(tmp_path):
    target=tmp_path/"history.csv"; target.write_text("old contents")
    metadata=tmp_path/"source.json"
    session=FakeSession(b"date,fighter_a\n2020-01-01,A\n"*110)
    with pytest.raises(ValueError,match="incompatible schema"):
        download_history(target,metadata,"https://fake.test/bad.csv",session=session)
    assert target.read_text()=="old contents"
    assert not metadata.exists()
