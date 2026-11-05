import os

import pytest

os.environ['DATABASE_URL'] = 'sqlite://'
os.environ.pop('VERCEL', None)

from backend import ai, create_app  # noqa: E402
from backend.extensions import db  # noqa: E402
from backend.models import User  # noqa: E402

PHOTO = 'data:image/jpeg;base64,AAAA'


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.delenv('AI_DAILY_LIMIT', raising=False)
    app = create_app({'TESTING': True})
    with app.app_context():
        with app.test_client() as c:
            yield c
        db.session.remove()
        db.drop_all()


@pytest.fixture
def groq(monkeypatch):
    calls = []

    def fake(messages, **kwargs):
        calls.append((messages, kwargs))
        return fake.reply

    fake.reply = 'Here is the next step.'
    fake.calls = calls
    monkeypatch.setattr(ai, 'call_groq', fake)
    return fake


def signup(client, username='coachkid'):
    res = client.post('/api/auth/register', json={
        'username': username,
        'email': username + '@example.com',
        'password': 'coach-pass-123',
        'full_name': 'Coach Kid',
    })
    return {'Authorization': 'Bearer ' + res.get_json()['access_token']}


def test_everything_needs_a_login(client, groq):
    assert client.get('/api/ai/status').status_code == 401
    assert client.post('/api/ai/coach', json={'question': 'x'}).status_code == 401
    assert client.post('/api/ai/cards', json={'items': [{'id': 'a'}]}).status_code == 401
    assert groq.calls == []


def test_coach_answers_and_counts_the_call(client, groq):
    headers = signup(client)
    assert client.get('/api/ai/status', headers=headers).get_json() == {'configured': True, 'limit': 150, 'left': 150}
    res = client.post('/api/ai/coach', headers=headers, json={'question': 'What is the slope formula?'})
    assert res.status_code == 200
    assert res.get_json() == {'reply': 'Here is the next step.'}
    assert client.get('/api/ai/status', headers=headers).get_json()['left'] == 149
    messages = groq.calls[0][0]
    assert messages[0]['role'] == 'system'
    assert 'SAT 1 and EST 1' in messages[0]['content']
    assert messages[1]['content'] == 'What is the slope formula?'


def test_bad_requests_cost_nothing(client, groq):
    headers = signup(client)
    assert client.post('/api/ai/coach', headers=headers, json={}).status_code == 400
    assert client.post('/api/ai/coach', headers=headers, json={'question': 7}).status_code == 400
    assert client.post('/api/ai/coach', headers=headers, json={'image': 'data:text/html;base64,AAAA'}).status_code == 400
    assert client.post('/api/ai/coach', headers=headers, json={'image': 'javascript:alert(1)'}).status_code == 400
    assert client.post('/api/ai/cards', headers=headers, json={'items': []}).status_code == 400
    assert client.post('/api/ai/cards', headers=headers, json={'items': ['x']}).status_code == 400
    assert client.get('/api/ai/status', headers=headers).get_json()['left'] == 150
    assert groq.calls == []


def test_photo_goes_to_a_vision_model(client, groq):
    headers = signup(client)
    assert client.post('/api/ai/coach', headers=headers, json={'image': PHOTO}).status_code == 200
    messages, kwargs = groq.calls[0]
    assert kwargs['models'] == ai.VISION_MODELS
    assert messages[1]['content'][1]['image_url']['url'] == PHOTO


def test_daily_limit_stops_the_student_but_not_others(client, groq, monkeypatch):
    monkeypatch.setenv('AI_DAILY_LIMIT', '2')
    headers = signup(client)
    assert client.post('/api/ai/coach', headers=headers, json={'question': 'a'}).status_code == 200
    assert client.post('/api/ai/coach', headers=headers, json={'question': 'b'}).status_code == 200
    res = client.post('/api/ai/coach', headers=headers, json={'question': 'c'})
    assert res.status_code == 429
    assert 'allowance' in res.get_json()['error']
    assert client.post('/api/ai/cards', headers=headers, json={'items': [{'id': 'x'}]}).status_code == 429
    assert len(groq.calls) == 2
    assert client.get('/api/ai/status', headers=headers).get_json()['left'] == 0
    other = signup(client, 'otherkid')
    assert client.post('/api/ai/coach', headers=other, json={'question': 'a'}).status_code == 200


def test_old_calls_stop_counting_after_a_day(client, groq, monkeypatch):
    monkeypatch.setenv('AI_DAILY_LIMIT', '1')
    headers = signup(client)
    assert client.post('/api/ai/coach', headers=headers, json={'question': 'a'}).status_code == 200
    assert client.post('/api/ai/coach', headers=headers, json={'question': 'b'}).status_code == 429
    from datetime import timedelta
    from backend.models import LoginAttempt, utcnow
    LoginAttempt.query.filter(LoginAttempt.key.like('ai:%')).update({'created_at': utcnow() - timedelta(hours=25)}, synchronize_session=False)
    db.session.commit()
    assert client.post('/api/ai/coach', headers=headers, json={'question': 'c'}).status_code == 200


def test_staff_are_not_counted(client, groq, monkeypatch):
    monkeypatch.setenv('AI_DAILY_LIMIT', '1')
    headers = signup(client, 'teacherkid')
    user = User.query.filter_by(username='teacherkid').first()
    user.role = 'teacher'
    db.session.commit()
    for _ in range(3):
        assert client.post('/api/ai/coach', headers=headers, json={'question': 'a'}).status_code == 200
    assert client.get('/api/ai/status', headers=headers).get_json() == {'configured': True, 'limit': None, 'left': None}


def test_without_a_key_it_says_so_and_spends_nothing(client, groq, monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY')
    headers = signup(client)
    assert client.get('/api/ai/status', headers=headers).get_json()['configured'] is False
    res = client.post('/api/ai/coach', headers=headers, json={'question': 'a'})
    assert res.status_code == 503
    assert groq.calls == []
    assert client.get('/api/ai/status', headers=headers).get_json()['left'] == 150


def test_upstream_failure_is_never_a_401(client, monkeypatch):
    headers = signup(client)

    def boom(*args, **kwargs):
        raise ai.GroqError('The AI service could not answer that. Please try again.')

    monkeypatch.setattr(ai, 'call_groq', boom)
    res = client.post('/api/ai/coach', headers=headers, json={'question': 'a'})
    assert res.status_code == 502
    assert 'AI service' in res.get_json()['error']
    assert client.post('/api/ai/cards', headers=headers, json={'items': [{'id': 'a'}]}).status_code == 502


def test_cards_keep_only_known_ids_and_clip_text(client, groq):
    headers = signup(client)
    groq.reply = '{"cards":[{"id":"math-practice-1","front":"F","back":"B","hook":"H"},{"id":"made-up","front":"F","back":"B"},{"id":"math-practice-2","front":"","back":"B"}]}'
    res = client.post('/api/ai/cards', headers=headers, json={'items': [
        {'id': 'math-practice-1', 'question': 'q', 'answer': 'a', 'explanation': 'e'},
        {'id': 'math-practice-2', 'question': 'q', 'answer': 'a', 'explanation': 'e'},
    ]})
    assert res.status_code == 200
    assert res.get_json() == {'cards': [{'id': 'math-practice-1', 'front': 'F', 'back': 'B', 'hook': 'H'}]}
    assert groq.calls[0][1]['json_mode'] is True
    groq.reply = 'not json at all'
    assert client.post('/api/ai/cards', headers=headers, json={'items': [{'id': 'a'}]}).get_json() == {'cards': []}


def test_cards_send_at_most_eight(client, groq):
    headers = signup(client)
    groq.reply = '{"cards":[]}'
    client.post('/api/ai/cards', headers=headers, json={'items': [{'id': str(i)} for i in range(20)]})
    import json
    assert len(json.loads(groq.calls[0][0][1]['content'])) == 8


def test_model_list_falls_through_when_a_model_is_retired(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.delenv('GROQ_MODEL', raising=False)
    tried = []

    def fake_post(model, *args):
        tried.append(model)
        if len(tried) == 1:
            return 400, {'error': {'code': 'model_decommissioned'}}
        return 200, {'choices': [{'message': {'content': 'ok'}}]}

    monkeypatch.setattr(ai, '_post', fake_post)
    assert ai.call_groq([{'role': 'user', 'content': 'x'}]) == 'ok'
    assert tried == ai.FALLBACK_MODELS[:2]


def test_upstream_errors_become_readable_messages(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setattr(ai, '_post', lambda *a: (401, {'error': {'message': 'Invalid API key sk-secret'}}))
    with pytest.raises(ai.GroqError) as exc:
        ai.call_groq([{'role': 'user', 'content': 'x'}])
    assert 'sk-secret' not in str(exc.value)
    monkeypatch.setattr(ai, '_post', lambda *a: (429, {}))
    with pytest.raises(ai.GroqError, match='busy'):
        ai.call_groq([{'role': 'user', 'content': 'x'}])
    monkeypatch.setattr(ai, '_post', lambda *a: (200, {'choices': []}))
    with pytest.raises(ai.GroqError, match='empty'):
        ai.call_groq([{'role': 'user', 'content': 'x'}])
