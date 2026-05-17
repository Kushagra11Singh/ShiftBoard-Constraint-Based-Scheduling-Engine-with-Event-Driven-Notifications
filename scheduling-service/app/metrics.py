from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

REQUEST_COUNT = Counter('shiftboard_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status_code'])
REQUEST_LATENCY = Histogram('shiftboard_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])
SCHEDULING_DURATION_MS = Histogram('shiftboard_scheduling_duration_ms', 'Backtracking scheduler runtime ms', buckets=[10,50,100,200,500,1000,2000,5000])
SCHEDULING_SUCCESS_TOTAL = Counter('shiftboard_scheduling_success_total', 'Successful scheduling runs')
SCHEDULING_FAILURE_TOTAL = Counter('shiftboard_scheduling_failure_total', 'Failed scheduling runs')
ACTIVE_STAFF_GAUGE = Gauge('shiftboard_active_staff_total', 'Number of active staff members')
TOTAL_SHIFTS_GAUGE = Gauge('shiftboard_shifts_total', 'Total shifts in the system')

def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
