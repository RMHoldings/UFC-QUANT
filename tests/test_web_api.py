from fastapi.testclient import TestClient
from ufc_quant import api

client = TestClient(api.app)

def test_health_endpoint():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_demo_report_is_html_and_marked_demo():
    response = client.get('/api/demo-report')
    assert response.status_code == 200
    assert 'text/html' in response.headers['content-type']
    assert 'DEMO REPORT' in response.text
    assert 'synthetic inputs' in response.text.lower()

def test_upcoming_event_endpoint_maps_upstream_error(monkeypatch):
    def fail(timeout=20):
        raise RuntimeError('upstream unreachable')
    monkeypatch.setattr('ufc_quant.ingest_ufc_com.fetch_next_upcoming_event', fail)
    response = client.get('/api/events/upcoming')
    assert response.status_code == 502
    assert 'Unable to retrieve' in response.json()['detail']
    assert 'upstream unreachable' not in response.json()['detail']

def test_upcoming_event_endpoint_returns_source_card(monkeypatch):
    def fake(timeout=20):
        return {'event': {'name': 'Test Event', 'date': '2099-01-01'}, 'fights': [{'fighter_a': 'A', 'fighter_b': 'B'}]}
    monkeypatch.setattr('ufc_quant.ingest_ufc_com.fetch_next_upcoming_event', fake)
    response = client.get('/api/events/upcoming')
    assert response.status_code == 200
    assert response.json()['source_status'] == 'live'
    assert len(response.json()['fights']) == 1

def test_upcoming_event_endpoint_rejects_invalid_event_schema(monkeypatch):
    def fake(timeout=20):
        return {'event': 'not-an-object', 'fights': []}
    monkeypatch.setattr('ufc_quant.ingest_ufc_com.fetch_next_upcoming_event', fake)
    response = client.get('/api/events/upcoming')
    assert response.status_code == 502
    assert 'ValueError' in response.json()['detail']

def test_upcoming_event_endpoint_rejects_non_object_fight_rows(monkeypatch):
    def fake(timeout=20):
        return {'event': {'name': 'Test Event'}, 'fights': [None]}
    monkeypatch.setattr('ufc_quant.ingest_ufc_com.fetch_next_upcoming_event', fake)
    response = client.get('/api/events/upcoming')
    assert response.status_code == 502
    assert 'ValueError' in response.json()['detail']
