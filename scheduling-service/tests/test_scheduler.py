# Unit tests for the pure-Python backtracking scheduler
import datetime
from app.services.scheduler import solve_schedule

DATE = datetime.date(2024, 12, 1)
START = datetime.time(8, 0)
END = datetime.time(16, 0)


def _shift(id_, required_count=1, skills=None):
    return {
        'id': id_,
        'date': DATE,
        'start_time': START,
        'end_time': END,
        'required_staff_count': required_count,
        'skill_requirements': [{'skill_id': s} for s in (skills or [])],
    }


def _staff(id_, skills=None, max_hours=40.0, is_active=True):
    return {
        'id': id_,
        'skill_ids': list(skills or []),
        'max_hours_per_week': max_hours,
        'is_active': is_active,
    }


# ── Basic cases ─────────────────────────────────────────────────────────────

def test_simple_assignment():
    shifts = [_shift(1)]
    staff = [_staff(1)]
    result, ms = solve_schedule(shifts, staff)
    assert result is not None
    assert len(result) == 1
    assert result[0]['shift_id'] == 1
    assert result[0]['staff_id'] == 1
    assert ms >= 0


def test_multiple_slots_multiple_staff():
    shifts = [_shift(1, required_count=3)]
    staff = [_staff(i) for i in range(1, 5)]
    result, _ = solve_schedule(shifts, staff)
    assert result is not None
    assert len(result) == 3
    assigned_ids = {a['staff_id'] for a in result}
    assert len(assigned_ids) == 3  # no duplicates


def test_no_staff_returns_none():
    result, _ = solve_schedule([_shift(1)], [])
    assert result is None


def test_not_enough_staff():
    result, _ = solve_schedule([_shift(1, required_count=3)], [_staff(1), _staff(2)])
    assert result is None


# ── Skill constraints ────────────────────────────────────────────────────────

def test_skill_constraint_satisfied():
    shifts = [_shift(1, skills=[10])]
    staff = [_staff(1, skills=[10]), _staff(2, skills=[])]
    result, _ = solve_schedule(shifts, staff)
    assert result is not None
    assert result[0]['staff_id'] == 1  # only staff 1 has skill 10


def test_skill_constraint_unsatisfiable():
    shifts = [_shift(1, skills=[99])]
    staff = [_staff(1, skills=[1]), _staff(2, skills=[2])]
    result, _ = solve_schedule(shifts, staff)
    assert result is None


def test_multiple_required_skills():
    shifts = [_shift(1, skills=[1, 2])]
    staff = [_staff(1, skills=[1]), _staff(2, skills=[2]), _staff(3, skills=[1, 2])]
    result, _ = solve_schedule(shifts, staff)
    assert result is not None
    assert result[0]['staff_id'] == 3


# ── Hours cap ────────────────────────────────────────────────────────────────

def test_hours_cap_blocks_assignment():
    shifts = [_shift(1)]  # 8-hour shift
    staff = [_staff(1, max_hours=4.0)]  # only 4h cap
    result, _ = solve_schedule(shifts, staff)
    assert result is None


def test_hours_cap_allows_assignment():
    shifts = [_shift(1)]  # 8-hour shift
    staff = [_staff(1, max_hours=8.0)]
    result, _ = solve_schedule(shifts, staff)
    assert result is not None


def test_cumulative_hours_across_shifts():
    # Two 8h shifts, one staff with 10h cap – cannot do both
    s1 = _shift(1)
    s2 = {**_shift(2), 'date': datetime.date(2024, 12, 2)}  # different day so no overlap
    staff = [_staff(1, max_hours=10.0)]
    result, _ = solve_schedule([s1, s2], staff)
    assert result is None


# ── Double-booking prevention ────────────────────────────────────────────────

def test_no_double_booking_same_time():
    s1 = _shift(1)
    s2 = _shift(2)  # same date/time
    staff = [_staff(1)]  # only one worker
    result, _ = solve_schedule([s1, s2], staff)
    assert result is None


def test_no_double_booking_with_enough_staff():
    s1 = _shift(1)
    s2 = _shift(2)
    staff = [_staff(1), _staff(2)]
    result, _ = solve_schedule([s1, s2], staff)
    assert result is not None
    assert len(result) == 2
    # Different staff assigned
    ids = {a['staff_id'] for a in result}
    assert len(ids) == 2


# ── Inactive staff excluded ──────────────────────────────────────────────────

def test_inactive_staff_excluded():
    shifts = [_shift(1)]
    staff = [_staff(1, is_active=False), _staff(2, is_active=True)]
    result, _ = solve_schedule(shifts, staff)
    assert result is not None
    assert result[0]['staff_id'] == 2


def test_all_inactive_returns_none():
    shifts = [_shift(1)]
    staff = [_staff(1, is_active=False)]
    result, _ = solve_schedule(shifts, staff)
    assert result is None


# ── Performance (soft) ───────────────────────────────────────────────────────

def test_large_problem_under_200ms():
    import datetime
    shifts = [
        {
            'id': i,
            'date': DATE,
            'start_time': datetime.time(i % 8, 0),
            'end_time': datetime.time((i % 8) + 1, 0),
            'required_staff_count': 1,
            'skill_requirements': [],
        }
        for i in range(20)
    ]
    staff = [_staff(i, max_hours=40.0) for i in range(30)]
    result, ms = solve_schedule(shifts, staff)
    assert result is not None
    assert ms < 200, f'Scheduler took {ms:.1f} ms, expected < 200 ms'
