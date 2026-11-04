"""Live class API: start/end a class, join tokens, raise hand, and teacher moderation."""

import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import current_user, jwt_required

from . import livekit
from .extensions import db
from .models import LiveClass, utcnow
from .routes import STAFF_ROLES, body, error, roles_required

live_bp = Blueprint('live', __name__, url_prefix='/api/live')

# A class nobody ended is treated as over after this long, so the "Live now" banner can't get stuck.
MAX_CLASS_LENGTH = timedelta(hours=6)


def identity_of(user):
    return f'u{user.id}'


def user_id_of(identity):
    if isinstance(identity, str) and identity.startswith('u') and identity[1:].isdigit():
        return int(identity[1:])
    return None


def active_class():
    cls = LiveClass.query.filter(LiveClass.ended_at.is_(None)).order_by(LiveClass.started_at.desc()).first()
    if cls and utcnow() - cls.started_at > MAX_CLASS_LENGTH:
        cls.ended_at = utcnow()
        db.session.commit()
        return None
    return cls


def require_live():
    if not livekit.configured():
        return None, error('Live classes are not switched on yet.', 503)
    cls = active_class()
    if not cls:
        return None, error('There is no live class right now.', 404)
    return cls, None


def call(method, payload, room):
    """RoomService call that treats 'participant/room not found' as already done."""
    try:
        return livekit.room_service(method, payload, room)
    except livekit.LiveKitError as e:
        if e.status == 404:
            return {}
        raise


def call_all(method, payloads, room):
    if not payloads:
        return 0
    with ThreadPoolExecutor(max_workers=min(10, len(payloads))) as pool:
        list(pool.map(lambda p: call(method, p, room), payloads))
    return len(payloads)


def students_in(cls):
    participants = call('ListParticipants', {'room': cls.room}, cls.room).get('participants') or []
    return [p for p in participants if livekit.participant_role(p) != 'host']


def speaker_identities(cls):
    return [f'u{i}' for i in cls.speakers or []]


@live_bp.errorhandler(livekit.LiveKitError)
def livekit_unavailable(e):
    current_app.logger.error('LiveKit call failed: %s', e)
    return error('The live class server did not respond. Please try again.', 502)


@live_bp.get('/status')
def status():
    on = livekit.configured()
    cls = active_class() if on else None
    return jsonify({'configured': on, 'live': cls.to_dict() if cls else None}), 200


@live_bp.post('/start')
@roles_required(*STAFF_ROLES)
def start():
    if not livekit.configured():
        return error('Live classes are not switched on yet.', 503)
    cls = active_class()
    if cls:
        return jsonify({'live': cls.to_dict(), 'already_live': True}), 200
    title = body().get('title')
    title = title.strip()[:120] if isinstance(title, str) and title.strip() else 'Live class'
    cls = LiveClass(title=title, room='estsat-' + secrets.token_hex(8), started_by=current_user.id,
                    speakers=[], removed=[])
    db.session.add(cls)
    db.session.commit()
    try:
        livekit.room_service('CreateRoom', {'name': cls.room, 'empty_timeout': 900, 'max_participants': 300}, cls.room)
    except livekit.LiveKitError as e:
        current_app.logger.warning('CreateRoom failed, room will be created on first join: %s', e)
    return jsonify({'live': cls.to_dict()}), 201


@live_bp.post('/join')
@jwt_required()
def join():
    cls, err = require_live()
    if err:
        return err
    if current_user.id in (cls.removed or []):
        return error('Your teacher removed you from this class.', 403)
    host = current_user.role in STAFF_ROLES
    role = 'host' if host else 'student'
    can_talk = host or cls.open_mics or current_user.id in (cls.speakers or [])
    token = livekit.access_token(identity_of(current_user), current_user.full_name or current_user.username,
                                 cls.room, role, can_talk)
    return jsonify({
        'url': livekit.public_url(),
        'token': token,
        'identity': identity_of(current_user),
        'role': role,
        'can_talk': can_talk,
        'live': cls.to_dict(),
        'speakers': speaker_identities(cls),
    }), 200


@live_bp.post('/end')
@roles_required(*STAFF_ROLES)
def end():
    cls = active_class()
    if not cls:
        return jsonify({'message': 'There is no live class to end.'}), 200
    cls.ended_at = utcnow()
    db.session.commit()
    if livekit.configured():
        call('DeleteRoom', {'room': cls.room}, cls.room)
    return jsonify({'message': 'Class ended.', 'live': cls.to_dict()}), 200


@live_bp.post('/hand')
@jwt_required()
def hand():
    cls, err = require_live()
    if err:
        return err
    raised = bool(body().get('raised'))
    call('UpdateParticipant', {'room': cls.room, 'identity': identity_of(current_user),
                               'attributes': {'hand': '1' if raised else ''}}, cls.room)
    return jsonify({'raised': raised}), 200


@live_bp.post('/allow-talk')
@roles_required(*STAFF_ROLES)
def allow_talk():
    cls, err = require_live()
    if err:
        return err
    data = body()
    identity, allow = data.get('identity'), bool(data.get('allow'))
    uid = user_id_of(identity)
    if uid is None:
        return error('Unknown participant.', 400)
    cls.speakers = [i for i in cls.speakers or [] if i != uid] + ([uid] if allow else [])
    db.session.commit()
    call('UpdateParticipant', {'room': cls.room, 'identity': identity,
                               'permission': livekit.permission(allow or cls.open_mics),
                               'attributes': {'hand': ''}}, cls.room)
    return jsonify({'identity': identity, 'allow': allow, 'speakers': speaker_identities(cls)}), 200


@live_bp.post('/open-mics')
@roles_required(*STAFF_ROLES)
def open_mics():
    cls, err = require_live()
    if err:
        return err
    cls.open_mics = bool(body().get('open'))
    db.session.commit()
    allowed = set(cls.speakers or [])
    payloads = [{'room': cls.room, 'identity': p['identity'],
                 'permission': livekit.permission(cls.open_mics or user_id_of(p['identity']) in allowed)}
                for p in students_in(cls)]
    updated = call_all('UpdateParticipant', payloads, cls.room)
    return jsonify({'open_mics': cls.open_mics, 'updated': updated}), 200


@live_bp.post('/mute-all')
@roles_required(*STAFF_ROLES)
def mute_all():
    cls, err = require_live()
    if err:
        return err
    payloads = [{'room': cls.room, 'identity': p['identity'], 'track_sid': t['sid'], 'muted': True}
                for p in students_in(cls) for t in p.get('tracks') or []
                if livekit.is_audio(t) and not t.get('muted')]
    muted = call_all('MutePublishedTrack', payloads, cls.room)
    return jsonify({'muted': muted}), 200


@live_bp.post('/remove')
@roles_required(*STAFF_ROLES)
def remove():
    cls, err = require_live()
    if err:
        return err
    identity = body().get('identity')
    uid = user_id_of(identity)
    if uid is None or uid == current_user.id:
        return error('Unknown participant.', 400)
    cls.speakers = [i for i in cls.speakers or [] if i != uid]
    cls.removed = [i for i in cls.removed or [] if i != uid] + [uid]
    db.session.commit()
    call('RemoveParticipant', {'room': cls.room, 'identity': identity}, cls.room)
    return jsonify({'removed': identity}), 200
