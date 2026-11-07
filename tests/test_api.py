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
        'chapters': ['math-0', 'physics-5', 'english-11', 'math-0', '<script>'],
        'exam': '2026-12-05',
        'mission': {'date': '2026-11-04', 'done': [1, 2, 'x', True]},
        'mistakes': [
            {'id': 'english-practice-7', 'date': '2026-11-04'},
            {'id': 'math-practice-12', 'date': 'nope'},
            {'id': 'english-practice-7', 'date': '2026-11-04'},
            {'id': '../../etc/passwd', 'date': '2026-11-04'},
            'not-a-dict',
        ],
        'extra': {'a': 1},
    }
    res = client.put('/api/user/state', headers=auth(token), json={'data': dirty})
    assert res.status_code == 200
    data = client.get('/api/user/state', headers=auth(token)).get_json()['data']
    assert data == {
        'stats': {'answered': 10, 'correct': 10, 'time': 300},
        'days': {'2026-11-04': 4},
        'chapters': ['math-0', 'physics-5', 'english-11'],
        'exam': '2026-12-05',
        'mission': {'date': '2026-11-04', 'done': [1, 2]},
        'mistakes': [
            {'id': 'english-practice-7', 'date': '2026-11-04'},
            {'id': 'math-practice-12', 'date': ''},
        ],
        'reviews': {},
        'topics': {},
        'lessons': [],
        'attempts': [],
        'time': {},
        'week': {'start': '', 'lessons': 0, 'practice': 0, 'reviews': 0, 'exams': 0},
        'xp': 0,
        'freezes': {'usedDays': [], 'earnedOn': []},
        'assignments': [],
        'goals': [],
        'music': '',
    }
    assert client.put('/api/user/state', headers=auth(token), json={'data': 'nope'}).status_code == 400


def test_study_extras_are_cleaned_and_bounded(client):
    token = register(client).get_json()['access_token']
    dirty = {
        'mistakes': [{'id': 'math-practice-1', 'date': '2026-11-05'}],
        'reviews': {
            'math-practice-1': {'stage': 9, 'due': '2026-11-06', 'last': 'nope', 'evil': 1},
            '../etc/passwd': {'stage': 1},
            'english-practice-2': 'not-a-dict',
            'math-practice-900': {'stage': 2, 'due': '2026-11-07', 'last': '2026-11-05'},
        },
        'topics': {
            'math|MATH-01': [10, 99],
            'physics|Modern Physics': [2, 1],
            'english|eng-01': [0, 0],
            '<script>|x': [1, 1],
            'math|MATH-02': [1],
        },
        'lessons': ['math-lesson-1', 'math-lesson-1', 'english-lesson-2', 'nope'],
        'attempts': [
            {'date': '2026-11-05', 'subject': 'mixed', 'score': 50, 'total': 40, 'percent': 120, 'seconds': 99, 'evil': 1},
            {'date': 'nope', 'subject': 'math', 'score': 1, 'total': 1},
            {'date': '2026-11-05', 'subject': 'history', 'score': 1, 'total': 1},
            {'date': '2026-11-05', 'subject': 'math', 'score': 1, 'total': 0},
        ],
        'time': {'2026-11-05': 600, 'nope': 5, '2026-11-04': 999999, '2026-11-03': 0},
        'week': {'start': '2026-11-02', 'lessons': 3, 'practice': 'x', 'reviews': -2, 'exams': 1, 'evil': 1},
        'xp': 1234,
        'freezes': {'usedDays': ['2026-11-01', 'x', '2026-11-01'], 'earnedOn': 'nope'},
        'assignments': [
            {'id': 'a-1', 'kind': 'lesson', 'target': 'math-lesson-1', 'title': 'T', 'due': 'x', 'note': 'n' * 200, 'created': '2026-11-05'},
            {'id': 'bad', 'kind': 'lesson', 'target': 'x'},
            {'id': 'a-2', 'kind': 'hack', 'target': 'x'},
            {'id': 'a-3', 'kind': 'exam', 'target': ''},
        ],
        'goals': [
            {'id': 'g-1', 'kind': 'level', 'target': 3, 'label': 'L', 'message': 'm' * 700, 'hasVoice': 'yes', 'created': '2026-11-05', 'unlockedAt': ''},
            {'id': 'g-2', 'kind': 'hack', 'target': '3'},
            {'id': 'g-3', 'kind': 'level', 'target': True},
        ],
        'music': 'http://not-https.example',
    }
    assert client.put('/api/user/state', headers=auth(token), json={'data': dirty}).status_code == 200
    data = client.get('/api/user/state', headers=auth(token)).get_json()['data']
    # math-practice-900 has no saved mistake, so its schedule is dead weight and is dropped.
    assert data['reviews'] == {'math-practice-1': {'stage': 4, 'due': '2026-11-06', 'last': ''}}
    assert data['topics'] == {'math|MATH-01': [10, 10], 'physics|Modern Physics': [2, 1]}
    assert data['lessons'] == ['math-lesson-1', 'english-lesson-2']
    assert data['attempts'] == [{'date': '2026-11-05', 'subject': 'mixed', 'score': 40, 'total': 40,
                                 'percent': 100, 'seconds': 99, 'level': 'standard'}]
    assert data['time'] == {'2026-11-04': 86400, '2026-11-05': 600}
    assert data['week'] == {'start': '2026-11-02', 'lessons': 3, 'practice': 0, 'reviews': 0, 'exams': 1}
    assert data['xp'] == 1234
    assert data['freezes'] == {'usedDays': ['2026-11-01'], 'earnedOn': []}
    assert len(data['assignments']) == 1
    assert len(data['assignments'][0]['note']) == 140
    assert data['assignments'][0]['due'] == ''
    assert len(data['goals']) == 1
    assert data['goals'][0]['target'] == '3'
    assert len(data['goals'][0]['message']) == 600
    assert data['goals'][0]['hasVoice'] is False
    assert data['music'] == ''

    too_many = {
        'lessons': ['math-lesson-%d' % i for i in range(500)],
        'attempts': [{'date': '2026-11-05', 'subject': 'math', 'score': 1, 'total': 1} for _ in range(50)],
        'goals': [{'id': 'g-%d' % i, 'kind': 'level', 'target': '2'} for i in range(50)],
        'music': 'https://www.youtube.com/watch?v=abc',
    }
    assert client.put('/api/user/state', headers=auth(token), json={'data': too_many}).status_code == 200
    data = client.get('/api/user/state', headers=auth(token)).get_json()['data']
    assert len(data['lessons']) == 400
    assert len(data['attempts']) == 30
    assert len(data['goals']) == 30
    assert data['music'] == 'https://www.youtube.com/watch?v=abc'


def test_the_newest_mistakes_keep_their_review_schedule(client):
    """Past 100 mistakes the oldest are dropped; the schedules kept must be for the ones left."""
    token = register(client).get_json()['access_token']
    mistakes = [{'id': 'math-practice-%d' % i, 'date': '2026-11-01'} for i in range(1, 131)]
    state = {
        'mistakes': mistakes,
        'reviews': {m['id']: {'stage': 2, 'due': '2026-11-10', 'last': '2026-11-03'} for m in mistakes},
    }
    assert client.put('/api/user/state', headers=auth(token), json={'data': state}).status_code == 200
    data = client.get('/api/user/state', headers=auth(token)).get_json()['data']
    kept = [m['id'] for m in data['mistakes']]
    assert len(kept) == 100
    assert kept[-1] == 'math-practice-130'
    assert sorted(data['reviews']) == sorted(kept)


def test_only_the_most_answered_topics_are_kept(client):
    token = register(client).get_json()['access_token']
    state = {'topics': {'math|Topic %02d' % i: [i + 1, 0] for i in range(100)}}
    assert client.put('/api/user/state', headers=auth(token), json={'data': state}).status_code == 200
    data = client.get('/api/user/state', headers=auth(token)).get_json()['data']
    assert len(data['topics']) == 80
    assert min(pair[0] for pair in data['topics'].values()) == 21


def test_an_exam_remembers_which_paper_it_was(client):
    token = register(client).get_json()['access_token']
    sent = {'attempts': [
        {'date': '2026-11-05', 'subject': 'mixed', 'score': 30, 'total': 40, 'percent': 75, 'seconds': 1200,
         'level': 'challenge'},
        {'date': '2026-11-04', 'subject': 'mixed', 'score': 60, 'total': 98, 'percent': 61, 'seconds': 8000,
         'level': 'mock'},
        {'date': '2026-11-03', 'subject': 'math', 'score': 18, 'total': 20, 'percent': 90, 'seconds': 900,
         'level': 'nonsense'},
    ]}
    assert client.put('/api/user/state', headers=auth(token), json={'data': sent}).status_code == 200
    kept = client.get('/api/user/state', headers=auth(token)).get_json()['data']['attempts']
    assert [a['level'] for a in kept] == ['challenge', 'mock', 'standard']


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
                        'last_active': '2026-11-04', 'exam': None, 'to_review': 0}

    sara_id = students['students'][0]['id']
    reset = client.post(f'/api/admin/users/{sara_id}/reset-password', headers=auth(teacher_token)).get_json()
    temp = reset['temporary_password']
    assert client.post('/api/auth/login', json={'username': 'sara', 'password': temp}).status_code == 200


def make_role(client, username, role):
    with client.app.app_context():
        User.query.filter_by(username=username).first().role = role
        db.session.commit()


def test_admin_student_detail_and_account_controls(client):
    sara_token = register(client).get_json()['access_token']
    client.put('/api/user/state', headers=auth(sara_token),
               json={'data': {'stats': {'answered': 2, 'correct': 1}, 'chapters': ['physics-0']}})
    teacher_token = register(client, username='omar', email='omar@example.com').get_json()['access_token']
    admin_token = register(client, username='ahmed', email='ahmed@example.com').get_json()['access_token']
    make_role(client, 'omar', 'teacher')
    make_role(client, 'ahmed', 'admin')
    with client.app.app_context():
        ids = {u.username: u.id for u in User.query.all()}

    assert client.get(f"/api/admin/students/{ids['sara']}", headers=auth(sara_token)).status_code == 403
    detail = client.get(f"/api/admin/students/{ids['sara']}", headers=auth(teacher_token)).get_json()
    assert detail['state']['chapters'] == ['physics-0'] and detail['student']['progress']['accuracy'] == 50
    assert client.get(f"/api/admin/students/{ids['omar']}", headers=auth(admin_token)).status_code == 404

    # teacher: can disable a student, cannot change roles or touch staff/self
    assert client.patch(f"/api/admin/users/{ids['sara']}", headers=auth(teacher_token), json={'role': 'teacher'}).status_code == 403
    assert client.patch(f"/api/admin/users/{ids['ahmed']}", headers=auth(teacher_token), json={'is_active': False}).status_code == 403
    assert client.patch(f"/api/admin/users/{ids['omar']}", headers=auth(teacher_token), json={'is_active': False}).status_code == 400
    res = client.patch(f"/api/admin/users/{ids['sara']}", headers=auth(teacher_token), json={'is_active': False})
    assert res.status_code == 200 and res.get_json()['user']['is_active'] is False
    assert client.post('/api/auth/login', json={'username': 'sara', 'password': 'correct-horse'}).status_code == 403
    client.patch(f"/api/admin/users/{ids['sara']}", headers=auth(teacher_token), json={'is_active': True})

    # admin: can promote/demote between student and teacher, never to admin
    assert client.patch(f"/api/admin/users/{ids['sara']}", headers=auth(admin_token), json={'role': 'admin'}).status_code == 400
    res = client.patch(f"/api/admin/users/{ids['sara']}", headers=auth(admin_token), json={'role': 'teacher'})
    assert res.get_json()['user']['role'] == 'teacher'
    assert client.patch(f"/api/admin/users/{ids['ahmed']}", headers=auth(admin_token), json={'is_active': False}).status_code == 400


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


def test_the_teacher_sets_one_board_and_every_student_reads_it(client):
    student = register(client).get_json()['access_token']
    teacher = register(client, username='ahmed', email='ahmed@example.com').get_json()['access_token']
    with client.app.app_context():
        User.query.filter_by(username='ahmed').first().role = 'teacher'
        db.session.commit()

    assert client.get('/api/user/class-board', headers=auth(student)).get_json()['assignments'] == []

    board = {'notice': 'Finish the quadratics lesson before Sunday.', 'assignments': [
        {'id': 'a-1', 'kind': 'lesson', 'target': 'math-lesson-20', 'title': 'Quadratic standard form',
         'due': '2026-11-09', 'note': 'Bring your working', 'created': '2026-11-07'},
        {'id': 'bad', 'kind': 'lesson', 'target': 'math-lesson-21'},
        {'id': 'a-2', 'kind': 'hack', 'target': 'x'},
    ]}
    # A student cannot set it.
    assert client.put('/api/admin/class-board', headers=auth(student), json={'board': board}).status_code == 403

    saved = client.put('/api/admin/class-board', headers=auth(teacher), json={'board': board})
    assert saved.status_code == 200
    assert len(saved.get_json()['assignments']) == 1

    seen = client.get('/api/user/class-board', headers=auth(student)).get_json()
    assert seen['notice'] == 'Finish the quadratics lesson before Sunday.'
    assert seen['assignments'][0]['target'] == 'math-lesson-20'
    assert seen['teacher'] == 'Sara Ali'


def test_the_teachers_own_progress_sync_leaves_the_board_alone(client):
    teacher = register(client, username='ahmed', email='ahmed@example.com').get_json()['access_token']
    with client.app.app_context():
        User.query.filter_by(username='ahmed').first().role = 'teacher'
        db.session.commit()
    board = {'notice': 'Mock exam on Thursday.', 'assignments': []}
    assert client.put('/api/admin/class-board', headers=auth(teacher), json={'board': board}).status_code == 200

    # The teacher uses the app as well, and their own state syncs like anyone else's.
    assert client.put('/api/user/state', headers=auth(teacher),
                      json={'data': {'stats': {'answered': 5, 'correct': 5}}}).status_code == 200
    assert client.get('/api/user/class-board', headers=auth(teacher)).get_json()['notice'] == 'Mock exam on Thursday.'


def test_the_class_report_shows_the_weakest_topics_and_who_owes_homework(client):
    teacher = register(client, username='ahmed', email='ahmed@example.com').get_json()['access_token']
    with client.app.app_context():
        User.query.filter_by(username='ahmed').first().role = 'teacher'
        db.session.commit()
    board = {'notice': '', 'assignments': [
        {'id': 'a-1', 'kind': 'lesson', 'target': 'math-lesson-20', 'title': 'Quadratics', 'created': '2026-11-01'},
        {'id': 'a-2', 'kind': 'exam', 'target': 'mixed-40', 'title': 'Mock', 'created': '2026-11-01'},
    ]}
    client.put('/api/admin/class-board', headers=auth(teacher), json={'board': board})

    done = register(client, username='omar', email='omar@example.com').get_json()['access_token']
    client.put('/api/user/state', headers=auth(done), json={'data': {
        'lessons': ['math-lesson-20'],
        'attempts': [{'date': '2026-11-05', 'subject': 'mixed', 'score': 20, 'total': 40, 'percent': 50, 'seconds': 60}],
        'topics': {'math|MATH-01': [10, 2], 'english|eng-01': [10, 9]},
    }})
    behind = register(client, username='lina', email='lina@example.com').get_json()['access_token']
    client.put('/api/user/state', headers=auth(behind), json={'data': {'topics': {'math|MATH-01': [10, 4]}}})

    report = client.get('/api/admin/class-report', headers=auth(teacher)).get_json()
    assert report['students'] == 2
    weakest = report['topics'][0]
    assert weakest['topic'] == 'MATH-01'
    assert weakest['answered'] == 20 and weakest['correct'] == 6 and weakest['accuracy'] == 30
    assert weakest['students'] == 2

    lesson, exam = report['homework']
    assert lesson['done'] == 1 and lesson['names'] == ['Sara Ali']
    assert exam['done'] == 1
    assert client.get('/api/admin/class-report', headers=auth(done)).status_code == 403


def _teacher(client):
    token = register(client, username='ahmed', email='ahmed@example.com').get_json()['access_token']
    with client.app.app_context():
        User.query.filter_by(username='ahmed').first().role = 'teacher'
        db.session.commit()
    return token


def test_a_parent_reads_the_report_from_a_link_and_can_change_nothing(client):
    student = register(client).get_json()['access_token']
    client.put('/api/user/state', headers=auth(student), json={'data': {
        'stats': {'answered': 40, 'correct': 30, 'time': 3600},
        'days': {'2026-11-05': 12, '2026-11-06': 8},
        'lessons': ['math-lesson-20'],
        'attempts': [{'date': '2026-11-06', 'subject': 'math', 'score': 15, 'total': 20,
                      'percent': 75, 'seconds': 900, 'level': 'challenge'}],
        'exam': '2027-05-01',
        'music': 'https://example.com/private-playlist',
    }})
    teacher = _teacher(client)
    client.put('/api/admin/class-board', headers=auth(teacher), json={'board': {
        'notice': 'Mock on Thursday.',
        'assignments': [{'id': 'a-1', 'kind': 'lesson', 'target': 'math-lesson-20',
                         'title': 'Quadratics', 'created': '2026-11-01'},
                        {'id': 'a-2', 'kind': 'lesson', 'target': 'math-lesson-21',
                         'title': 'Circles', 'created': '2026-11-01'}],
    }})

    with client.app.app_context():
        student_id = User.query.filter_by(username='sara').first().id
    link = client.get(f'/api/admin/students/{student_id}/parent-link', headers=auth(teacher))
    assert link.status_code == 200
    token = link.get_json()['token']
    assert link.get_json()['path'] == '/parent-report.html?t=' + token

    # No account, no header: the link is the whole key.
    report = client.get('/api/parent/report?t=' + token)
    assert report.status_code == 200
    seen = report.get_json()
    assert seen['student']['name'] == 'Sara Ali'
    assert seen['student']['exam'] == '2027-05-01'
    assert seen['teacher'] == 'Sara Ali'
    assert seen['progress']['stats']['answered'] == 40
    assert seen['progress']['attempts'][0]['percent'] == 75
    # Personal keys stay out of a report the whole family can read.
    assert 'music' not in seen['progress']
    assert 'goals' not in seen['progress']
    assert 'mistakes' not in seen['progress']
    assert [h['done'] for h in seen['homework']] == [True, False]

    # It is a report, not a login: it opens nothing else.
    assert client.get('/api/user/state', headers=auth(token)).status_code in (401, 422)
    assert client.get('/api/admin/students', headers=auth(token)).status_code in (401, 422)


def test_a_broken_or_foreign_parent_link_is_refused(client):
    student = register(client).get_json()['access_token']
    teacher = _teacher(client)
    with client.app.app_context():
        student_id = User.query.filter_by(username='sara').first().id
    good = client.get(f'/api/admin/students/{student_id}/parent-link',
                      headers=auth(teacher)).get_json()['token']

    assert client.get('/api/parent/report').status_code == 404
    assert client.get('/api/parent/report?t=' + good[:-3] + 'xyz').status_code == 404
    assert client.get('/api/parent/report?t=' + student).status_code == 404

    # Only staff hand the link out, and only for a student who exists.
    assert client.get(f'/api/admin/students/{student_id}/parent-link',
                      headers=auth(student)).status_code == 403
    assert client.get('/api/admin/students/9999/parent-link', headers=auth(teacher)).status_code == 404

    # A disabled account stops answering.
    with client.app.app_context():
        User.query.filter_by(username='sara').first().is_active = False
        db.session.commit()
    assert client.get('/api/parent/report?t=' + good).status_code == 404
