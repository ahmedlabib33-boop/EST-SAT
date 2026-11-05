import os

import pytest

os.environ['DATABASE_URL'] = 'sqlite://'
os.environ.pop('VERCEL', None)

from backend import create_app  # noqa: E402
from backend.extensions import db  # noqa: E402


@pytest.fixture
def client():
    app = create_app({'TESTING': True})
    with app.app_context():
        with app.test_client() as c:
            yield c
        db.session.remove()
        db.drop_all()


def register(client, username='reviewer'):
    res = client.post('/api/auth/register', json={
        'username': username,
        'email': username + '@example.com',
        'password': 'practice-pass-1',
        'full_name': 'Review Student',
    })
    return res.get_json()['access_token']


def auth(token):
    return {'Authorization': 'Bearer ' + token}


def first_lesson_with_questions(client, subject):
    data = client.get('/api/practice/' + subject + '/topics').get_json()
    return next(l for l in data['lessons'] if l['questions'] > 0)


# ---------------------------------------------------------------- content

def test_banks_are_loaded(client):
    counts = {s['subject']: s for s in client.get('/api/practice/subjects').get_json()['subjects']}
    # 155, not the workbook's 159: four math rows repeat an earlier lesson verbatim.
    assert counts['math'] == {'subject': 'math', 'topics': 5, 'lessons': 155, 'questions': 328}
    assert counts['english'] == {'subject': 'english', 'topics': 12, 'lessons': 157, 'questions': 314}
    assert counts['physics'] == {'subject': 'physics', 'topics': 6, 'lessons': 47, 'questions': 94}


def test_unknown_subject_is_rejected(client):
    assert client.get('/api/practice/physics/topics').status_code == 200
    assert client.get('/api/practice/nope/topics').status_code == 400
    assert client.get('/api/practice/random?subject=nope').status_code == 400


def test_physics_is_a_full_subject(client):
    """Physics used to have no lessons at all, so a wrong physics answer could
    not be saved for review and there was nothing to revise from."""
    counts = {s['subject']: s for s in client.get('/api/practice/subjects').get_json()['subjects']}
    assert counts['physics']['topics'] == 6
    assert counts['physics']['lessons'] >= 40
    assert counts['physics']['questions'] >= 2 * counts['physics']['lessons']

    topics = client.get('/api/practice/physics/topics').get_json()
    lesson = topics['lessons'][0]
    body = client.get('/api/practice/physics/lessons/' + lesson['id']).get_json()
    assert body['questions'] and 'answer' not in body['questions'][0]
    assert body['lesson']['formula'] and body['lesson']['explanation']

    sheet = client.get('/api/practice/physics/revision').get_json()
    assert len(sheet['lessons']) == counts['physics']['lessons']
    assert all(l['title'] for l in sheet['lessons'])


def test_the_daily_mission_is_the_same_all_day_and_changes_tomorrow(client):
    first = client.get('/api/practice/daily?day=2026-11-05&n=6').get_json()
    again = client.get('/api/practice/daily?day=2026-11-05&n=6').get_json()
    tomorrow = client.get('/api/practice/daily?day=2026-11-06&n=6').get_json()
    ids = [q['id'] for q in first['questions']]
    assert len(ids) == 6 and len(set(ids)) == 6
    assert ids == [q['id'] for q in again['questions']]
    assert ids != [q['id'] for q in tomorrow['questions']]
    assert all('answer' not in q and 'explanation' not in q for q in first['questions'])
    # A bad or missing day falls back to today rather than failing.
    assert len(client.get('/api/practice/daily?day=nope').get_json()['questions']) == 6
    assert len(client.get('/api/practice/daily?n=999').get_json()['questions']) == 20


def test_unknown_lesson_is_404(client):
    assert client.get('/api/practice/math/lessons/math-lesson-99999').status_code == 404


def test_every_english_lesson_has_its_own_questions(client):
    """The source workbook keys English practice on the topic name, which would make
    all 157 rules share 12 question pairs. The importer keys on the rule instead."""
    data = client.get('/api/practice/english/topics').get_json()
    assert len(data['lessons']) == 157
    assert all(l['questions'] >= 2 for l in data['lessons'])

    topic = data['topics'][0]['id']
    in_topic = [l for l in data['lessons'] if l['topicId'] == topic]
    assert len(in_topic) > 1

    seen = set()
    for lesson in in_topic:
        body = client.get('/api/practice/english/lessons/' + lesson['id']).get_json()
        ids = tuple(q['id'] for q in body['questions'])
        assert ids not in seen, 'two rules share the same questions'
        seen.add(ids)


# ---------------------------------------------------------------- no leaks

@pytest.mark.parametrize('subject', ['math', 'english'])
def test_questions_never_carry_their_answer(client, subject):
    lesson = first_lesson_with_questions(client, subject)
    body = client.get('/api/practice/' + subject + '/lessons/' + lesson['id']).get_json()
    assert body['questions']
    for question in body['questions']:
        assert 'answer' not in question
        assert 'explanation' not in question
        assert len(question['choices']) == 4


def test_random_questions_never_carry_their_answer(client):
    body = client.get('/api/practice/random?subject=all&n=20').get_json()
    assert len(body['questions']) == 20
    assert all('answer' not in q and 'explanation' not in q for q in body['questions'])


def test_random_respects_subject_and_caps_n(client):
    body = client.get('/api/practice/random?subject=math&n=5').get_json()
    assert len(body['questions']) == 5
    assert {q['subject'] for q in body['questions']} == {'math'}
    assert len(client.get('/api/practice/random?n=999').get_json()['questions']) == 100


def test_random_can_be_limited_to_topics(client):
    body = client.get('/api/practice/random?subject=all&topics=MATH-01,eng-01&n=40').get_json()
    assert body['questions']
    assert {q['topicId'] for q in body['questions']} <= {'MATH-01', 'eng-01'}
    assert client.get('/api/practice/random?subject=all&topics=nope').get_json() == {'questions': []}


def test_questions_by_id_keep_order_and_never_carry_answers(client):
    body = client.get('/api/practice/questions?ids=english-practice-401,math-practice-401,does-not-exist').get_json()
    assert [q['id'] for q in body['questions']] == ['english-practice-401', 'math-practice-401']
    assert [q['subject'] for q in body['questions']] == ['english', 'math']
    assert all('answer' not in q and 'explanation' not in q for q in body['questions'])
    assert client.get('/api/practice/questions').get_json() == {'questions': []}
    ids = ','.join('math-practice-%d' % i for i in range(401, 500))
    assert len(client.get('/api/practice/questions?ids=' + ids).get_json()['questions']) == 60


@pytest.mark.parametrize('subject', ['math', 'english'])
def test_no_question_is_a_generated_placeholder(client, subject):
    """The imported banks were mostly four templates with the same wrong answers
    every time, which a student could pass without reading the question."""
    templates = ('Which formula or statement correctly represents', 'An EST-style problem requires',
                 'Which choice best shows the rule', 'In an EST question about')
    topics = client.get('/api/practice/' + subject + '/topics').get_json()
    seen = {}
    total = 0
    for lesson in topics['lessons']:
        body = client.get('/api/practice/%s/lessons/%s' % (subject, lesson['id'])).get_json()
        for question in body['questions']:
            total += 1
            assert not question['question'].startswith(templates), question['id']
            texts = [c['text'] for c in question['choices']]
            assert len(set(texts)) == 4, '%s repeats a choice' % question['id']
            for text in texts:
                # Short options repeat by nature: "are", "9", "0.5". Whole phrases should not.
                if len(text) > 15:
                    seen[text] = seen.get(text, 0) + 1
    # The templates offered the same three wrong sentences in all 157 questions.
    worst, count = max(seen.items(), key=lambda pair: pair[1])
    assert count <= max(6, total // 20), 'choice %r is reused in %d of %d questions' % (worst, count, total)


def test_revision_sheet_has_lessons_but_no_questions(client):
    body = client.get('/api/practice/math/revision').get_json()
    assert len(body['topics']) == 5
    assert len(body['lessons']) == 155
    assert body['lessons'][0]['formula']
    assert 'answer' not in body['lessons'][0]
    assert 'questions' not in body
    assert client.get('/api/practice/nope/revision').status_code == 400


# ----------------------------------------------------------------- grading

def test_grading_marks_right_and_wrong(client):
    lesson = first_lesson_with_questions(client, 'math')
    question = client.get('/api/practice/math/lessons/' + lesson['id']).get_json()['questions'][0]

    letters = [c['id'] for c in question['choices']]
    graded = client.post('/api/practice/grade',
                         json={'items': [{'id': question['id'], 'answer': letter} for letter in letters]})
    results = graded.get_json()
    assert results['total'] == 4
    assert results['score'] == 1
    assert results['percent'] == 25

    right = [r for r in results['results'] if r['correct']]
    assert len(right) == 1
    assert right[0]['answer'] == right[0]['selected']
    assert right[0]['explanation']


def test_grading_is_case_insensitive(client):
    question = client.get('/api/practice/random?subject=math&n=1').get_json()['questions'][0]
    upper = client.post('/api/practice/grade', json={'items': [{'id': question['id'], 'answer': 'a'}]}).get_json()
    lower = client.post('/api/practice/grade', json={'items': [{'id': question['id'], 'answer': 'A'}]}).get_json()
    assert upper['results'][0]['correct'] == lower['results'][0]['correct']


def test_unknown_question_is_reported_and_excluded(client):
    question = client.get('/api/practice/random?subject=english&n=1').get_json()['questions'][0]
    graded = client.post('/api/practice/grade', json={'items': [
        {'id': question['id'], 'answer': question['choices'][0]['id']},
        {'id': 'does-not-exist'},
    ]}).get_json()
    assert graded['total'] == 1
    assert graded['results'][1] == {'id': 'does-not-exist', 'error': 'Question not found.'}


def test_grade_rejects_bad_payloads(client):
    assert client.post('/api/practice/grade', json={}).status_code == 400
    assert client.post('/api/practice/grade', json={'items': []}).status_code == 400
    assert client.post('/api/practice/grade',
                       json={'items': [{'id': 'x', 'answer': 'A'}] * 101}).status_code == 400


def test_blank_answer_is_wrong_not_an_error(client):
    question = client.get('/api/practice/random?subject=math&n=1').get_json()['questions'][0]
    graded = client.post('/api/practice/grade', json={'items': [{'id': question['id'], 'answer': ''}]}).get_json()
    assert graded['total'] == 1 and graded['score'] == 0
    assert graded['results'][0]['correct'] is False


# ------------------------------------------------------------------ review

def test_review_needs_a_login(client):
    assert client.get('/api/practice/review').status_code == 401


def test_review_returns_only_this_student_s_mistakes(client):
    token = register(client)
    assert client.get('/api/practice/review', headers=auth(token)).get_json() == {'total': 0, 'questions': []}

    question = client.get('/api/practice/random?subject=english&n=1').get_json()['questions'][0]
    client.put('/api/user/state', headers=auth(token), json={'data': {
        'mistakes': [{'id': question['id'], 'date': '2026-11-05'}],
    }})

    body = client.get('/api/practice/review', headers=auth(token)).get_json()
    assert body['total'] == 1
    item = body['questions'][0]
    assert item['id'] == question['id']
    # Revealed here, and only here: this account has already missed this question.
    assert item['answer'] in ('A', 'B', 'C', 'D')
    assert item['explanation']

    other = register(client, username='someone.else')
    assert client.get('/api/practice/review', headers=auth(other)).get_json()['total'] == 0
