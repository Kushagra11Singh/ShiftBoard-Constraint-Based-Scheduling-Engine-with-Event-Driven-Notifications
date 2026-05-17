# Worker unit tests – all HTTP calls are mocked with respx; no real network needed.

import httpx
import pytest
import respx

from app.config import SCHEDULING_SERVICE_URL
from app.worker import _fetch_unscheduled_shifts, _trigger_schedule, _run_once


SHIFTS_URL = f'{SCHEDULING_SERVICE_URL}/shifts'
SCHEDULE_URL = f'{SCHEDULING_SERVICE_URL}/shifts/schedule'

SAMPLE_SHIFTS = [
    {'id': 1, 'name': 'Morning', 'status': 'unscheduled'},
    {'id': 2, 'name': 'Evening', 'status': 'unscheduled'},
]

SCHEDULE_SUCCESS = {
    'success': True,
    'assignments': [
        {'shift_id': 1, 'staff_id': 10},
        {'shift_id': 2, 'staff_id': 11},
    ],
    'elapsed_ms': 42.5,
    'message': 'Scheduled 2 assignments in 42.5 ms',
}

SCHEDULE_FAILURE = {
    'success': False,
    'assignments': [],
    'elapsed_ms': 5.0,
    'message': 'No feasible schedule found.',
}


# ── _fetch_unscheduled_shifts ────────────────────────────────────────────────

@respx.mock
def test_fetch_unscheduled_shifts_returns_list():
    respx.get(SHIFTS_URL).mock(return_value=httpx.Response(200, json=SAMPLE_SHIFTS))
    with httpx.Client() as client:
        result = _fetch_unscheduled_shifts(client)
    assert result == SAMPLE_SHIFTS


@respx.mock
def test_fetch_unscheduled_shifts_empty():
    respx.get(SHIFTS_URL).mock(return_value=httpx.Response(200, json=[]))
    with httpx.Client() as client:
        result = _fetch_unscheduled_shifts(client)
    assert result == []


@respx.mock
def test_fetch_unscheduled_shifts_http_error():
    respx.get(SHIFTS_URL).mock(return_value=httpx.Response(500))
    with httpx.Client() as client:
        with pytest.raises(httpx.HTTPStatusError):
            _fetch_unscheduled_shifts(client)


# ── _trigger_schedule ────────────────────────────────────────────────────────

@respx.mock
def test_trigger_schedule_success():
    respx.post(SCHEDULE_URL).mock(return_value=httpx.Response(200, json=SCHEDULE_SUCCESS))
    with httpx.Client() as client:
        result = _trigger_schedule(client, [1, 2])
    assert result['success'] is True
    assert len(result['assignments']) == 2


@respx.mock
def test_trigger_schedule_no_solution():
    respx.post(SCHEDULE_URL).mock(return_value=httpx.Response(200, json=SCHEDULE_FAILURE))
    with httpx.Client() as client:
        result = _trigger_schedule(client, [1])
    assert result['success'] is False


@respx.mock
def test_trigger_schedule_http_error():
    respx.post(SCHEDULE_URL).mock(return_value=httpx.Response(503))
    with httpx.Client() as client:
        with pytest.raises(httpx.HTTPStatusError):
            _trigger_schedule(client, [1])


# ── _run_once (integration of fetch + schedule) ──────────────────────────────

@respx.mock
def test_run_once_success_updates_metrics():
    from app import metrics
    respx.get(SHIFTS_URL).mock(return_value=httpx.Response(200, json=SAMPLE_SHIFTS))
    respx.post(SCHEDULE_URL).mock(return_value=httpx.Response(200, json=SCHEDULE_SUCCESS))

    before = metrics.SHIFTS_SCHEDULED_TOTAL._value.get()
    _run_once()
    after = metrics.SHIFTS_SCHEDULED_TOTAL._value.get()

    assert after - before == 2  # 2 assignments in SCHEDULE_SUCCESS


@respx.mock
def test_run_once_no_shifts_does_not_call_schedule():
    schedule_route = respx.post(SCHEDULE_URL)
    respx.get(SHIFTS_URL).mock(return_value=httpx.Response(200, json=[]))

    _run_once()
    assert not schedule_route.called


@respx.mock
def test_run_once_http_error_does_not_raise():
    respx.get(SHIFTS_URL).mock(return_value=httpx.Response(500))
    _run_once()  # should swallow the error and log it


@respx.mock
def test_run_once_no_solution_increments_counter():
    from app import metrics
    respx.get(SHIFTS_URL).mock(return_value=httpx.Response(200, json=[SAMPLE_SHIFTS[0]]))
    respx.post(SCHEDULE_URL).mock(return_value=httpx.Response(200, json=SCHEDULE_FAILURE))

    before = metrics.WORKER_RUNS_TOTAL.labels(result='no_solution')._value.get()
    _run_once()
    after = metrics.WORKER_RUNS_TOTAL.labels(result='no_solution')._value.get()
    assert after > before


@respx.mock
def test_run_once_sets_unscheduled_gauge():
    from app import metrics
    respx.get(SHIFTS_URL).mock(return_value=httpx.Response(200, json=SAMPLE_SHIFTS))
    respx.post(SCHEDULE_URL).mock(return_value=httpx.Response(200, json=SCHEDULE_SUCCESS))

    _run_once()
    assert metrics.UNSCHEDULED_SHIFTS_GAUGE._value.get() == 2
