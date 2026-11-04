from datetime import timedelta

import jwt
import pytest

from backend import create_app, livekit
from backend.extensions import db
from backend.models import LiveClass, User

SECRET = 'test-livekit-secret-' + 'x' * 24


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    monkeypatch.delenv('VERCEL', raising=False)
    monkeypatch.setenv('LIVEKIT_URL', 'wss://live.example.com')
    monkeypatch.setenv('LIVEKIT_API_KEY', 'test-key')
    monkeypatch.setenv('LIVEKIT_API_SECRET', SECRET)
    calls, participants = [], []

    def fake_room_service(method, payload, room):
        calls.append((method, payload))
        return {'participants': participants} if method == 'ListParticipants' else {}

    monkeypatch.setattr(livekit, 'room_service', fake_room_service)
    app = create_app({'TESTING': True})
    with app.test_client() as c:
        c.app, c.calls, c.participants = app, calls, participants
        yield c
    with app.app_context():
        db.drop_all()


def signup(client, username, role='student'):
    res = client.post('/api/auth/register', json={'full_name': username.title(), 'username': username,
                                                  'email': f'{username}@example.com', 'password': 'long-password'})
    data = res.get_json()
    if role != 'student':
        with client.app.app_context():
            db.session.get(User, data['user']['id']).role = role
            db.session.commit()
    return {'Authorization': 'Bearer ' + data['access_token']}, f"u{data['user']['id']}"


def claims(token):
    return jwt.decode(token, SECRET, algorithms=['HS256'])


def test_not_configured(client, monkeypatch):
    monkeypatch.delenv('LIVEKIT_URL')
    teacher, _ = signup(client, 'ahmed', 'teacher')
    assert client.get('/api/live/status').get_json() == {'configured': False, 'live': None}
    assert client.post('/api/live/start', headers=teacher, json={}).status_code == 503


def test_only_staff_can_start_and_tokens_have_right_permissions(client):
    teacher, teacher_id = signup(client, 'ahmed', 'teacher')
    student, student_id = signup(client, 'sara')
    assert client.post('/api/live/start', headers=student, json={'title': 'x'}).status_code == 403
    assert client.post('/api/live/join', headers=student).status_code == 404

    res = client.post('/api/live/start', headers=teacher, json={'title': 'Kinematics Q&A'})
    assert res.status_code == 201 and res.get_json()['live']['title'] == 'Kinematics Q&A'
    assert client.calls[-1][0] == 'CreateRoom'
    assert client.get('/api/live/status').get_json()['live']['host_name'] == 'Ahmed'
    assert client.post('/api/live/start', headers=teacher, json={}).get_json()['already_live'] is True

    s = client.post('/api/live/join', headers=student).get_json()
    c = claims(s['token'])
    assert s['url'] == 'wss://live.example.com' and s['role'] == 'student' and s['identity'] == student_id
    assert c['sub'] == student_id and c['iss'] == 'test-key' and c['name'] == 'Sara'
    assert c['video']['canPublish'] is False and c['video']['canSubscribe'] is True
    assert c['video']['canUpdateOwnMetadata'] is False
    assert c['attributes'] == {'role': 'student'}

    t = claims(client.post('/api/live/join', headers=teacher).get_json()['token'])
    assert t['sub'] == teacher_id and t['video']['canPublish'] is True
    assert 'screen_share' in t['video']['canPublishSources'] and t['attributes'] == {'role': 'host'}
    assert t['video']['room'] == c['video']['room']


def test_allow_talk_hand_and_open_mics(client):
    teacher, teacher_id = signup(client, 'ahmed', 'teacher')
    student, student_id = signup(client, 'sara')
    _, omar_id = signup(client, 'omar')
    client.post('/api/live/start', headers=teacher, json={})

    client.post('/api/live/hand', headers=student, json={'raised': True})
    assert client.calls[-1] == ('UpdateParticipant', {'room': client.calls[-1][1]['room'], 'identity': student_id,
                                                      'attributes': {'hand': '1'}})
    assert client.post('/api/live/allow-talk', headers=student, json={'identity': omar_id, 'allow': True}).status_code == 403

    res = client.post('/api/live/allow-talk', headers=teacher, json={'identity': student_id, 'allow': True}).get_json()
    assert res['speakers'] == [student_id]
    method, payload = client.calls[-1]
    assert method == 'UpdateParticipant' and payload['permission']['can_publish'] is True
    assert payload['permission']['can_publish_sources'] == ['MICROPHONE', 'CAMERA'] and payload['attributes'] == {'hand': ''}
    assert claims(client.post('/api/live/join', headers=student).get_json()['token'])['video']['canPublish'] is True

    client.participants[:] = [
        {'identity': teacher_id, 'attributes': {'role': 'host'}, 'tracks': []},
        {'identity': student_id, 'attributes': {'role': 'student'}, 'tracks': []},
        {'identity': omar_id, 'metadata': '{"role": "student"}', 'tracks': []},
    ]
    client.calls.clear()
    res = client.post('/api/live/open-mics', headers=teacher, json={'open': True}).get_json()
    assert res == {'open_mics': True, 'updated': 2}
    updates = {p['identity']: p['permission']['can_publish'] for m, p in client.calls if m == 'UpdateParticipant'}
    assert updates == {student_id: True, omar_id: True}

    client.calls.clear()
    client.post('/api/live/open-mics', headers=teacher, json={'open': False})
    updates = {p['identity']: p['permission']['can_publish'] for m, p in client.calls if m == 'UpdateParticipant'}
    assert updates == {student_id: True, omar_id: False}


def test_mute_all_remove_and_end(client):
    teacher, teacher_id = signup(client, 'ahmed', 'teacher')
    student, student_id = signup(client, 'sara')
    client.post('/api/live/start', headers=teacher, json={})
    client.participants[:] = [
        {'identity': teacher_id, 'attributes': {'role': 'host'}, 'tracks': [{'sid': 'TR_t', 'type': 'AUDIO', 'muted': False}]},
        {'identity': student_id, 'attributes': {'role': 'student'}, 'tracks': [
            {'sid': 'TR_a', 'type': 'AUDIO', 'muted': False},
            {'sid': 'TR_v', 'type': 'VIDEO', 'muted': False},
            {'sid': 'TR_b', 'type': 'AUDIO', 'muted': True}]},
    ]
    client.calls.clear()
    assert client.post('/api/live/mute-all', headers=teacher).get_json() == {'muted': 1}
    assert [p['track_sid'] for m, p in client.calls if m == 'MutePublishedTrack'] == ['TR_a']

    assert client.post('/api/live/remove', headers=teacher, json={'identity': teacher_id}).status_code == 400
    assert client.post('/api/live/remove', headers=teacher, json={'identity': student_id}).status_code == 200
    assert client.calls[-1][0] == 'RemoveParticipant'
    assert client.post('/api/live/join', headers=student).status_code == 403

    assert client.post('/api/live/end', headers=teacher).status_code == 200
    assert client.calls[-1][0] == 'DeleteRoom'
    assert client.get('/api/live/status').get_json()['live'] is None
    assert client.post('/api/live/join', headers=teacher).status_code == 404


def test_forgotten_class_ends_itself(client):
    teacher, _ = signup(client, 'ahmed', 'teacher')
    client.post('/api/live/start', headers=teacher, json={})
    with client.app.app_context():
        cls = LiveClass.query.first()
        cls.started_at = cls.started_at - timedelta(hours=7)
        db.session.commit()
    assert client.get('/api/live/status').get_json()['live'] is None


def test_livekit_outage_returns_502(client, monkeypatch):
    teacher, _ = signup(client, 'ahmed', 'teacher')
    client.post('/api/live/start', headers=teacher, json={})

    def down(method, payload, room):
        raise livekit.LiveKitError(0, 'connection refused')

    monkeypatch.setattr(livekit, 'room_service', down)
    res = client.post('/api/live/mute-all', headers=teacher)
    assert res.status_code == 502 and 'live class server' in res.get_json()['error']
