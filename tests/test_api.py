import pytest

from backend import create_app
from backend.extensions import db
from backend.models import User


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    monkeypatch.delenv('VERCEL', raising=False)
    app = create_app({'TESTING': True})
    with app.test_client() as c:
        c.app = app
        yield c
    with app.app_context():
        db.drop_all()


def register(client, username='sara', email='sara@example.com', password='correct-horse', **extra):
    payload = {'full_name': 'Sara Ali', 'username': username, 'email': email, 'password': password}
    payload.update(extra)
    return client.post('/api/auth/register', json=payload)


def auth(token):
    return {'Authorization': f'Bearer {token}'}


def test_health_and_seeded_courses(client):
    assert client.get('/api/health').get_json()['database'] == 'ok'
    courses = client.get('/api/courses').get_json()
    assert courses['total'] == 2
    assert sum(len(c['chapters']) for c in courses['courses']) == 11


def test_register_login_and_me(client):
    res = register(client)
    assert res.status_code == 201
    assert res.get_json()['user']['role'] == 'student'
    assert 'password_hash' not in res.get_json()['user']

    for ident in ('sara', 'SARA', 'Sara@Example.com'):
        res = client.post('/api/auth/login', json={'username': ident, 'password': 'correct-horse'})
        assert res.status_code == 200, ident
    token = res.get_json()['access_token']
    me = client.get('/api/auth/me', headers=auth(token)).get_json()['user']
    assert me['username'] == 'sara' and me['email'] == 'sara@example.com'


def test_register_cannot_choose_role_and_validates(client):
    res = register(client, role='admin')
    assert res.get_json()['user']['role'] == 'student'
    assert register(client).status_code == 409
    assert register(client, username='other', email='SARA@example.com').status_code == 409
    assert register(client, username='x', email='x@example.com').status_code == 400
    assert register(client, username='shortpw', email='s@example.com', password='1234567').status_code == 400
    assert register(client, username='bademail', email='not-an-email').status_code == 400


def test_wrong_password_and_throttle(client):
    register(client)
    for _ in range(8):
        res = client.post('/api/auth/login', json={'username': 'sara', 'password': 'nope-nope'})
        assert res.status_code == 401
    res = client.post('/api/auth/login', json={'username': 'sara', 'password': 'correct-horse'})
    assert res.status_code == 429
    assert res.headers['Retry-After'] == '900'


def test_protected_routes_need_valid_token(client):
    assert client.get('/api/auth/me').status_code == 401
    assert client.get('/api/auth/me', headers=auth('garbage')).status_code == 401


def test_deactivated_user_token_rejected(client):
    token = register(client).get_json()['access_token']
    with client.app.app_context():
        user = User.query.filter_by(username='sara').first()
        user.is_active = False
        db.session.commit()
    assert client.get('/api/auth/me', headers=auth(token)).status_code == 401
    res = client.post('/api/auth/login', json={'username': 'sara', 'password': 'correct-horse'})
    assert res.status_code == 403


def test_state_sync_is_cleaned(client):
    token = register(client).get_json()['access_token']
    assert client.get('/api/user/state', headers=auth(token)).get_json()['data'] == {}
    dirty = {
        'stats': {'answered': 10, 'correct': 99, 'time': 300, 'evil': 'x'},
        'days': {'2026-11-04': 4, 'nope': 3, '2026-11-03': 0},
        'chapters': ['math-0', 'physics-5', 'math-0', '<script>'],
        'exam': '2026-12-05',
        'mission': {'date': '2026-11-04', 'done': [1, 2, 'x', True]},
        'extra': {'a': 1},
    }
    res = client.put('/api/user/state', headers=auth(token), json={'data': dirty})
    assert res.status_code == 200
    data = client.get('/api/user/state', headers=auth(token)).get_json()['data']
    assert data == {
        'stats': {'answered': 10, 'correct': 10, 'time': 300},
        'days': {'2026-11-04': 4},
        'chapters': ['math-0', 'physics-5'],
        'exam': '2026-12-05',
        'mission': {'date': '2026-11-04', 'done': [1, 2]},
    }
    assert client.put('/api/user/state', headers=auth(token), json={'data': 'nope'}).status_code == 400


def test_profile_and_password_change(client):
    token = register(client).get_json()['access_token']
    res = client.put('/api/user/profile', headers=auth(token), json={'full_name': 'Sara A.', 'school': 'Cairo HS', 'role': 'admin'})
    assert res.get_json()['user']['full_name'] == 'Sara A.'
    assert res.get_json()['user']['role'] == 'student'
    bad = client.put('/api/user/password', headers=auth(token), json={'current_password': 'wrong', 'new_password': 'another-pass'})
    assert bad.status_code == 400
    ok = client.put('/api/user/password', headers=auth(token), json={'current_password': 'correct-horse', 'new_password': 'another-pass'})
    assert ok.status_code == 200
    assert client.post('/api/auth/login', json={'username': 'sara', 'password': 'another-pass'}).status_code == 200


def test_teacher_endpoints(client):
    student_token = register(client).get_json()['access_token']
    client.put('/api/user/state', headers=auth(student_token),
               json={'data': {'stats': {'answered': 4, 'correct': 3}, 'days': {'2026-11-04': 4}, 'chapters': ['math-1']}})
    assert client.get('/api/admin/students', headers=auth(student_token)).status_code == 403

    teacher_token = register(client, username='ahmed', email='ahmed@example.com').get_json()['access_token']
    with client.app.app_context():
        User.query.filter_by(username='ahmed').first().role = 'teacher'
        db.session.commit()
    students = client.get('/api/admin/students', headers=auth(teacher_token)).get_json()
    assert students['total'] == 1
    progress = students['students'][0]['progress']
    assert progress == {'answered': 4, 'accuracy': 75, 'chapters_done': 1, 'active_days': 1,
                        'last_active': '2026-11-04', 'exam': None}

    sara_id = students['students'][0]['id']
    reset = client.post(f'/api/admin/users/{sara_id}/reset-password', headers=auth(teacher_token)).get_json()
    temp = reset['temporary_password']
    assert client.post('/api/auth/login', json={'username': 'sara', 'password': temp}).status_code == 200


def test_quiz_flow(client):
    token = register(client).get_json()['access_token']
    quiz = client.get('/api/quizzes/1').get_json()
    assert all('correct_answer' not in q for q in quiz['questions'])
    attempt = client.post('/api/quizzes/1/start', headers=auth(token)).get_json()['attempt_id']
    answers = {str(q['id']): 'a' for q in quiz['questions']}
    result = client.post('/api/quizzes/1/submit', headers=auth(token), json={'attempt_id': attempt, 'answers': answers}).get_json()
    assert result['percentage'] == 100 and result['passed'] is True
    again = client.post('/api/quizzes/1/submit', headers=auth(token), json={'attempt_id': attempt, 'answers': answers})
    assert again.status_code == 409


def test_unknown_api_route_is_json(client):
    res = client.get('/api/nope')
    assert res.status_code == 404 and res.get_json()['error']
