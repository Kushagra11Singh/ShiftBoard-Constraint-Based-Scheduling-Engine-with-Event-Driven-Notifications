def test_create_skill_success(client):
    r = client.post('/skills', json={'name': 'Python', 'description': 'Python programming'})
    assert r.status_code == 201
    data = r.json()
    assert data['id'] is not None
    assert data['name'] == 'Python'
    assert data['description'] == 'Python programming'


def test_create_skill_no_description(client):
    r = client.post('/skills', json={'name': 'SQL'})
    assert r.status_code == 201
    assert r.json()['description'] is None


def test_create_skill_duplicate_name(client):
    client.post('/skills', json={'name': 'Django'})
    r = client.post('/skills', json={'name': 'Django'})
    assert r.status_code == 400


def test_list_skills_empty(client):
    r = client.get('/skills')
    assert r.status_code == 200
    assert r.json() == []


def test_list_skills_multiple(client):
    client.post('/skills', json={'name': 'FastAPI'})
    client.post('/skills', json={'name': 'PostgreSQL'})
    r = client.get('/skills')
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_skill_found(client):
    created = client.post('/skills', json={'name': 'Redis'}).json()
    r = client.get(f'/skills/{created["id"]}')
    assert r.status_code == 200
    assert r.json()['name'] == 'Redis'


def test_get_skill_not_found(client):
    r = client.get('/skills/99999')
    assert r.status_code == 404


def test_update_skill(client):
    created = client.post('/skills', json={'name': 'Flask'}).json()
    r = client.put(f'/skills/{created["id"]}', json={'name': 'Flask-RESTx', 'description': 'REST ext'})
    assert r.status_code == 200
    assert r.json()['name'] == 'Flask-RESTx'


def test_update_skill_not_found(client):
    r = client.put('/skills/99999', json={'name': 'X'})
    assert r.status_code == 404


def test_delete_skill_success(client):
    created = client.post('/skills', json={'name': 'Celery'}).json()
    r = client.delete(f'/skills/{created["id"]}')
    assert r.status_code == 204
    assert client.get(f'/skills/{created["id"]}').status_code == 404


def test_delete_skill_not_found(client):
    r = client.delete('/skills/99999')
    assert r.status_code == 404
