"""Server-side LiveKit helpers: access tokens and RoomService calls, using only PyJWT + urllib.

Works with LiveKit Cloud or a self-hosted LiveKit server. Configure with
LIVEKIT_URL (wss://...), LIVEKIT_API_KEY and LIVEKIT_API_SECRET.
"""

import json
import os
import time
import urllib.error
import urllib.request

import jwt

STUDENT_SOURCES = ['microphone', 'camera']
HOST_SOURCES = ['camera', 'microphone', 'screen_share', 'screen_share_audio']


class LiveKitError(Exception):
    def __init__(self, status, message):
        super().__init__(f'LiveKit {status}: {message}')
        self.status = status


def config():
    url = os.getenv('LIVEKIT_URL', '').strip()
    key = os.getenv('LIVEKIT_API_KEY', '').strip()
    secret = os.getenv('LIVEKIT_API_SECRET', '').strip()
    return (url, key, secret) if url and key and secret else None


def configured():
    return config() is not None


def public_url():
    return config()[0]


def access_token(identity, name, room, role, can_publish, ttl_seconds=4 * 3600):
    _, key, secret = config()
    now = int(time.time())
    sources = HOST_SOURCES if role == 'host' else STUDENT_SOURCES
    claims = {
        'iss': key,
        'sub': identity,
        'name': name,
        'nbf': now - 10,
        'exp': now + ttl_seconds,
        # Participants cannot edit their own name/metadata/attributes, so these stay trustworthy.
        'metadata': json.dumps({'role': role}),
        'attributes': {'role': role},
        'video': {
            'room': room,
            'roomJoin': True,
            'canSubscribe': True,
            'canPublishData': True,
            'canPublish': bool(can_publish),
            'canPublishSources': sources if can_publish else [],
            'canUpdateOwnMetadata': False,
        },
    }
    return jwt.encode(claims, secret, algorithm='HS256')


def room_service(method, payload, room):
    """Call a LiveKit RoomService method (Twirp over HTTP)."""
    url, key, secret = config()
    base = url.rstrip('/').replace('wss://', 'https://', 1).replace('ws://', 'http://', 1)
    now = int(time.time())
    admin = jwt.encode({
        'iss': key, 'sub': 'estsat-server', 'nbf': now - 10, 'exp': now + 60,
        'video': {'room': room, 'roomAdmin': True, 'roomCreate': True, 'roomList': True},
    }, secret, algorithm='HS256')
    request = urllib.request.Request(
        f'{base}/twirp/livekit.RoomService/{method}',
        data=json.dumps(payload).encode(),
        method='POST',
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {admin}'},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        raise LiveKitError(e.code, e.read().decode('utf-8', 'replace')[:300]) from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise LiveKitError(0, str(e)) from None


def permission(can_publish, role='student'):
    sources = HOST_SOURCES if role == 'host' else STUDENT_SOURCES
    return {
        'can_subscribe': True,
        'can_publish': bool(can_publish),
        'can_publish_data': True,
        'can_publish_sources': [s.upper() for s in sources] if can_publish else [],
    }


def participant_role(p):
    attributes = p.get('attributes') or {}
    if attributes.get('role'):
        return attributes['role']
    try:
        return json.loads(p.get('metadata') or '{}').get('role', 'student')
    except ValueError:
        return 'student'


def is_audio(track):
    return track.get('type') in ('AUDIO', 0)
