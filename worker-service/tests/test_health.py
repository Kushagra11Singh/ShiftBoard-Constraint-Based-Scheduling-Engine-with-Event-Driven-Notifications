from fastapi.testclient import TestClient
from unittest.mock import patch

with patch('app.worker.start_worker'), patch('app.worker.stop_worker'):
    from app.main import app

client = TestClient(app)


def test_health_endpoint():
    r = client.get('/health')
    assert r.status_code == 200
    data = r.json()
    assert data['status'] == 'ok'
    assert data['service'] == 'worker-service'


def test_metrics_endpoint():
    r = client.get('/metrics')
    assert r.status_code == 200
    assert 'worker_runs_total' in r.text


def test_trigger_endpoint():
    with patch('app.main.trigger_now', return_value={'triggered': True}) as mock_trigger:
        r = client.post('/trigger')
    assert r.status_code == 200
    assert r.json()['triggered'] is True
    mock_trigger.assert_called_once()
