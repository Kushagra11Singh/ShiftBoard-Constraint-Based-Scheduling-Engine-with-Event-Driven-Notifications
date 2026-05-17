from fastapi.testclient import TestClient
from unittest.mock import patch

# Patch consumer so tests don't actually connect to Kafka
with patch('app.consumer.start_consumer'), patch('app.consumer.stop_consumer'):
    from app.main import app

client = TestClient(app)


def test_health_endpoint():
    r = client.get('/health')
    assert r.status_code == 200
    data = r.json()
    assert data['status'] == 'ok'
    assert data['service'] == 'notification-service'


def test_metrics_endpoint():
    r = client.get('/metrics')
    assert r.status_code == 200
    assert 'notification_events_consumed_total' in r.text
