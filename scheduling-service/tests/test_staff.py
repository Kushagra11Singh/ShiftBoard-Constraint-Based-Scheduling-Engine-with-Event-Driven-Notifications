def test_create_staff_success(client):
    r = client.post('/staff', json={'name': 'Alice', 'email': 'alice@example.com'})
    assert r.status_code == 201
    data = r.json()
    assert data['id'] is not None
    assert data['name'] == 'Alice'
    assert data['email'] == 'alice@example.com'
    assert data['max_hours_per_week'] == 40.0
    assert data['is_active'] is True
    assert data['skills'] == []


def test_create_staff_duplicate_email(client):
    client.post('/staff', json={'name': 'Bob', 'email': 'bob@example.com'})
    r = client.post('/staff', json={'name': 'Bob2', 'email': 'bob@example.com'})
    assert r.status_code == 400
    assert 'Email' in r.json()['detail']


def test_list_staff_empty(client):
    r = client.get('/staff')
    assert r.status_code == 200
    assert r.json() == []


def test_list_staff_with_entries(client):
    client.post('/staff', json={'name': 'Carol', 'email': 'carol@example.com'})
    client.post('/staff', json={'name': 'Dave', 'email': 'dave@example.com'})
    r = client.get('/staff')
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_staff_found(client):
    created = client.post('/staff', json={'name': 'Eve', 'email': 'eve@example.com'}).json()
    r = client.get(f'/staff/{created["id"]}')
    assert r.status_code == 200
    assert r.json()['name'] == 'Eve'


def test_get_staff_not_found(client):
    r = client.get('/staff/99999')
    assert r.status_code == 404


def test_update_staff_success(client):
    created = client.post('/staff', json={'name': 'Frank', 'email': 'frank@example.com'}).json()
    r = client.put(
        f'/staff/{created["id"]}',
        json={'name': 'Franklin', 'email': 'frank@example.com', 'max_hours_per_week': 32.0, 'is_active': True},
    )
    assert r.status_code == 200
    assert r.json()['name'] == 'Franklin'
    assert r.json()['max_hours_per_week'] == 32.0


def test_update_staff_not_found(client):
    r = client.put('/staff/99999', json={'name': 'X', 'email': 'x@x.com', 'is_active': True, 'max_hours_per_week': 40})
    assert r.status_code == 404


def test_update_staff_duplicate_email(client):
    client.post('/staff', json={'name': 'A', 'email': 'a@example.com'})
    b = client.post('/staff', json={'name': 'B', 'email': 'b@example.com'}).json()
    r = client.put(
        f'/staff/{b["id"]}',
        json={'name': 'B', 'email': 'a@example.com', 'is_active': True, 'max_hours_per_week': 40},
    )
    assert r.status_code == 400


def test_delete_staff_success(client):
    created = client.post('/staff', json={'name': 'Grace', 'email': 'grace@example.com'}).json()
    r = client.delete(f'/staff/{created["id"]}')
    assert r.status_code == 204
    assert client.get(f'/staff/{created["id"]}').status_code == 404


def test_delete_staff_not_found(client):
    r = client.delete('/staff/99999')
    assert r.status_code == 404


def test_add_skill_to_staff(client):
    staff = client.post('/staff', json={'name': 'Henry', 'email': 'henry@example.com'}).json()
    skill = client.post('/skills', json={'name': 'Python'}).json()
    r = client.post(f'/staff/{staff["id"]}/skills/{skill["id"]}')
    assert r.status_code == 200
    assert any(s['name'] == 'Python' for s in r.json()['skills'])


def test_add_skill_to_staff_idempotent(client):
    staff = client.post('/staff', json={'name': 'Ivy', 'email': 'ivy@example.com'}).json()
    skill = client.post('/skills', json={'name': 'Java'}).json()
    client.post(f'/staff/{staff["id"]}/skills/{skill["id"]}')
    r = client.post(f'/staff/{staff["id"]}/skills/{skill["id"]}')
    assert r.status_code == 200
    assert len(r.json()['skills']) == 1


def test_add_skill_staff_not_found(client):
    skill = client.post('/skills', json={'name': 'Go'}).json()
    r = client.post(f'/staff/99999/skills/{skill["id"]}')
    assert r.status_code == 404


def test_add_skill_skill_not_found(client):
    staff = client.post('/staff', json={'name': 'Jack', 'email': 'jack@example.com'}).json()
    r = client.post(f'/staff/{staff["id"]}/skills/99999')
    assert r.status_code == 404


def test_remove_skill_from_staff(client):
    staff = client.post('/staff', json={'name': 'Kate', 'email': 'kate@example.com'}).json()
    skill = client.post('/skills', json={'name': 'Rust'}).json()
    client.post(f'/staff/{staff["id"]}/skills/{skill["id"]}')
    r = client.delete(f'/staff/{staff["id"]}/skills/{skill["id"]}')
    assert r.status_code == 200
    assert r.json()['skills'] == []


def test_remove_skill_staff_not_found(client):
    skill = client.post('/skills', json={'name': 'C++'}).json()
    r = client.delete(f'/staff/99999/skills/{skill["id"]}')
    assert r.status_code == 404


def test_remove_skill_skill_not_found(client):
    staff = client.post('/staff', json={'name': 'Leo', 'email': 'leo@example.com'}).json()
    r = client.delete(f'/staff/{staff["id"]}/skills/99999')
    assert r.status_code == 404
