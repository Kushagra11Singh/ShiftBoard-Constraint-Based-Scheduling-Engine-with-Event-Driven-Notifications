import os

SCHEDULING_SERVICE_URL: str = os.getenv('SCHEDULING_SERVICE_URL', 'http://localhost:8000')
WORKER_INTERVAL_SECONDS: int = int(os.getenv('WORKER_INTERVAL_SECONDS', '60'))
