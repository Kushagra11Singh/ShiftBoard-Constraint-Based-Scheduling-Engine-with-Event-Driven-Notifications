# Tests for /shifts endpoints

BASE_SHIFT = {
    'name': 'Morning Shift',
    'date': '2024-12-01',
    'start_time': '08:00:00',
    'end_time': '16:00:00',
    'required_staff_count': 1,
}


def test_create_shift_success(client):
    r = client.post('/shifts', json=BASE_SHIFT)
    assert r.status_code == 201
    data = r.json()
    assert data['name'] == 'Morning Shift'
    assert data['status'] == 'unscheduled'
    assert data['skill_requirements'] == []
    assert data['assignments'] == []


def test_create_shift_with_skill_requirement(client):
    skill = client.post('/skills', json={'name': 'Nursing'}).json()
    payload = {**BASE_SHIFT, 'skill_requirements': [{'skill_id': skill['id'], 'required_count': 1}]}
    r = client.post('/shifts', json=payload)
    assert r.status_code == 201
    assert len(r.json()['skill_requirements']) == 1


def test_list_shifts_empty(client):
    r = client.get('/shifts')
    assert r.status_code == 200
    assert r.json() == []


def test_list_shifts_with_filter(client):
    client.post('/shifts', json=BASE_SHIFT)
    r = client.get('/shifts?status_filter=unscheduled')
    assert r.status_code == 200
    assert len(r.json()) == 1
    r2 = client.get('/shifts?status_filter=scheduled')
    assert len(r2.json()) == 0


def test_get_shift_found(client):
    created = client.post('/shifts', json=BASE_SHIFT).json()
    r = client.get(f'/shifts/{created["id"]}')
    assert r.status_code == 200
    assert r.json()['name'] == 'Morning Shift'


def test_get_shift_not_found(client):
    r = client.get('/shifts/99999')
    assert r.status_code == 404


def test_update_shift(client):
    created = client.post('/shifts', json=BASE_SHIFT).json()
    r = client.put(
        f'/shifts/{created["id"]}',
        json={**BASE_SHIFT, 'name': 'Evening Shift', 'required_staff_count': 2},
    )
    assert r.status_code == 200
    assert r.json()['name'] == 'Evening Shift'
    assert r.json()['required_staff_count'] == 2


def test_update_shift_not_found(client):
    r = client.put('/shifts/99999', json=BASE_SHIFT)
    assert r.status_code == 404


def test_delete_shift_success(client):
    created = client.post('/shifts', json=BASE_SHIFT).json()
    r = client.delete(f'/shifts/{created["id"]}')
    assert r.status_code == 204
    assert client.get(f'/shifts/{created["id"]}').status_code == 404


def test_delete_shift_not_found(client):
    r = client.delete('/shifts/99999')
    assert r.status_code == 404


def test_schedule_shifts_success(client):
    for i in range(3):
        client.post('/staff', json={'name': f'Worker{i}', 'email': f'worker{i}@test.com'})
    shift = client.post('/shifts', json={**BASE_SHIFT, 'required_staff_count': 2}).json()
    r = client.post('/shifts/schedule', json={'shift_ids': [shift['id']]})
    assert r.status_code == 200
    data = r.json()
    assert data['success'] is True
    assert len(data['assignments']) == 2
    assert data['elapsed_ms'] >= 0


def test_schedule_shifts_with_skill_constraint(client):
    skill = client.post('/skills', json={'name': 'Forklift'}).json()
    # 2 staff with skill, 1 without
    for i in range(2):
        s = client.post('/staff', json={'name': f'Skilled{i}', 'email': f'sk{i}@test.com'}).json()
        client.post(f'/staff/{s["id"]}/skills/{skill["id"]}')
    client.post('/staff', json={'name': 'NoSkill', 'email': 'noskill@test.com'})

    payload = {
        **BASE_SHIFT,
        'required_staff_count': 1,
        'skill_requirements': [{'skill_id': skill['id'], 'required_count': 1}],
    }
    shift = client.post('/shifts', json=payload).json()
    r = client.post('/shifts/schedule', json={'shift_ids': [shift['id']]})
    assert r.status_code == 200
    data = r.json()
    assert data['success'] is True
    # Assigned staff must have the skill
    assigned_id = data['assignments'][0]['staff_id']
    staff_detail = client.get(f'/staff/{assigned_id}').json()
    assert any(sk['id'] == skill['id'] for sk in staff_detail['skills'])


def test_schedule_shifts_no_feasible_solution(client):
    skill = client.post('/skills', json={'name': 'RareSkill'}).json()
    # No staff have this skill
    client.post('/staff', json={'name': 'PlainWorker', 'email': 'plain@test.com'})
    payload = {
        **BASE_SHIFT,
        'skill_requirements': [{'skill_id': skill['id'], 'required_count': 1}],
    }
    shift = client.post('/shifts', json=payload).json()
    r = client.post('/shifts/schedule', json={'shift_ids': [shift['id']]})
    assert r.status_code == 200
    data = r.json()
    assert data['success'] is False
    assert data['assignments'] == []


def test_schedule_respects_hours_cap(client):
    # Staff with only 4h cap, shift is 8h -> infeasible
    client.post('/staff', json={
        'name': 'Tired', 'email': 'tired@test.com', 'max_hours_per_week': 4.0
    })
    shift = client.post('/shifts', json=BASE_SHIFT).json()  # 8-hour shift
    r = client.post('/shifts/schedule', json={'shift_ids': [shift['id']]})
    assert r.status_code == 200
    assert r.json()['success'] is False


def test_schedule_no_double_booking(client):
    worker = client.post('/staff', json={'name': 'Solo', 'email': 'solo@test.com'}).json()
    # Two overlapping shifts both needing 1 staff = only 1 can be assigned
    shift1 = client.post('/shifts', json={
        **BASE_SHIFT, 'name': 'S1', 'required_staff_count': 1
    }).json()
    shift2 = client.post('/shifts', json={
        **BASE_SHIFT, 'name': 'S2', 'required_staff_count': 1
    }).json()
    r = client.post('/shifts/schedule', json={'shift_ids': [shift1['id'], shift2['id']]})
    assert r.status_code == 200
    data = r.json()
    # With only 1 worker who can't be double-booked, one shift stays unassigned
    assert data['success'] is False


def test_schedule_shifts_not_found(client):
    r = client.post('/shifts/schedule', json={'shift_ids': [99999]})
    assert r.status_code == 404


def test_schedule_marks_shifts_as_scheduled(client):
    client.post('/staff', json={'name': 'Ready', 'email': 'ready@test.com'})
    shift = client.post('/shifts', json=BASE_SHIFT).json()
    client.post('/shifts/schedule', json={'shift_ids': [shift['id']]})
    updated = client.get(f'/shifts/{shift["id"]}').json()
    assert updated['status'] == 'scheduled'
    assert len(updated['assignments']) == 1
