"""AI coach and flashcards, powered by Groq.

Every call spends the server's API key, so each one needs a signed-in account and counts towards a
daily allowance. Teachers and admins are not counted. Calls are logged as rows in `login_attempts`
(key `ai:<user id>`), because production has no migration tooling for a new table and that table
already has the indexes, and is already pruned after a day by the login route.

Set GROQ_API_KEY to turn this on. AI_DAILY_LIMIT changes the allowance, GROQ_MODEL the first model tried.
"""

import json
import os
import re
import urllib.error
import urllib.request
from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from .extensions import db
from .models import LoginAttempt, utcnow

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
# Groq retires models over time and not every key can use every model, so try a short list.
FALLBACK_MODELS = ['llama-3.3-70b-versatile', 'openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'llama-3.1-8b-instant']
VISION_MODELS = ['meta-llama/llama-4-scout-17b-16e-instruct', 'meta-llama/llama-4-maverick-17b-128e-instruct']

DEFAULT_DAILY_LIMIT = 150
WINDOW = timedelta(hours=24)
STAFF_ROLES = ('admin', 'teacher')
MAX_QUESTION = 3000
MAX_PHOTO_QUESTION = 1500
MAX_CARDS = 8
# The browser shrinks photos before sending; requests are capped at 256 KB by the app.
MAX_IMAGE = 220 * 1024
IMAGE_RE = re.compile(r'^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$')

COACH_PROMPT = (
    'You are an experienced teacher preparing a student for the SAT 1 and EST 1 exams in Math, English and Physics. '
    'Teach like a professional: work out what the student is missing, explain the rule and WHY it works, show one short '
    'worked example with every step, then end with one quick check question. When the student is wrong, point out the '
    'exact mistake. In Math and Physics, show the formula, substitute the numbers and include units. In English, name '
    'the grammar rule or the reading strategy, and show why the wrong options fail. Stay on exam study; if asked about '
    'anything else, say so briefly and steer back. If the student writes in Arabic, answer in clear Egyptian Arabic and '
    'keep exam terms in English. Never invent official score tables, exam dates or rules: if you are unsure, say so. '
    'Write plain text without markdown. Keep answers under 250 words unless more detail is requested.'
)
PHOTO_PROMPT = COACH_PROMPT + (
    ' The student has sent a photo of a homework or practice question. First say in one line what it asks. Then guide '
    'them: name the topic and the rule, work out the first step, and ask them to try the next step. Do not give the '
    'final answer outright unless they ask for it after trying. If the photo is unreadable or not about these subjects, '
    'say so politely.'
)
CARDS_PROMPT = (
    "You turn an SAT 1 or EST 1 student's wrong answers into revision flashcards. For each item, write: "
    '"front": a short question that tests the same idea and can be answered on its own, including every figure needed, '
    'at most 35 words. "back": the correct answer with the key reason or working, at most 45 words. "hook": a memory '
    'trick or rule of thumb, at most 15 words, exactly consistent with the back; if no accurate hook fits, give the rule '
    'in plain words. Use only the facts given and do not invent figures. Return JSON only: '
    '{"cards":[{"id":"...","front":"...","back":"...","hook":"..."}]}'
)


class GroqError(Exception):
    """Something went wrong upstream. The message is safe to show to students."""


def _configured():
    return bool(os.getenv('GROQ_API_KEY'))


def _post(model, messages, max_tokens, temperature, json_mode):
    payload = {'model': model, 'temperature': temperature, 'max_tokens': max_tokens, 'messages': messages}
    if json_mode:
        payload['response_format'] = {'type': 'json_object'}
    req = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': 'Bearer ' + os.getenv('GROQ_API_KEY', ''),
            'Content-Type': 'application/json',
            'User-Agent': 'est-sat-study-platform/2.0',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            return res.status, json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode('utf-8'))
        except ValueError:
            return exc.code, {}


def call_groq(messages, max_tokens=420, temperature=0.35, json_mode=False, models=None):
    candidates = models or [os.getenv('GROQ_MODEL')] + FALLBACK_MODELS
    candidates = [m for i, m in enumerate(candidates) if m and m not in candidates[:i]]
    status, data = 0, {}
    try:
        for model in candidates:
            status, data = _post(model, messages, max_tokens, temperature, json_mode)
            code = (data.get('error') or {}).get('code') if isinstance(data, dict) else None
            if status != 404 and code not in ('model_not_found', 'model_decommissioned'):
                break
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise GroqError('Could not reach the AI service. Please try again.') from exc
    if status == 429:
        raise GroqError('The AI service is busy right now. Please try again in a minute.')
    if status != 200:
        raise GroqError('The AI service could not answer that. Please try again.')
    try:
        text = data['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        text = ''
    if not text:
        raise GroqError('The AI service returned an empty answer. Please try again.')
    return text


def parse_json_reply(text):
    try:
        return json.loads(text)
    except ValueError:
        match = re.search(r'\{.*\}', text, re.S)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except ValueError:
            return None


# ==================== ALLOWANCE ====================

def daily_limit():
    try:
        value = int(os.getenv('AI_DAILY_LIMIT', DEFAULT_DAILY_LIMIT))
    except ValueError:
        return DEFAULT_DAILY_LIMIT
    return value if value > 0 else DEFAULT_DAILY_LIMIT


def _quota_key():
    return 'ai:%d' % current_user.id


def calls_used():
    since = utcnow() - WINDOW
    return LoginAttempt.query.filter(LoginAttempt.key == _quota_key(), LoginAttempt.created_at >= since).count()


def is_exempt():
    return current_user.role in STAFF_ROLES


def _gate():
    """Returns an error response, or None when the student may ask."""
    if not _configured():
        return jsonify({'error': 'The AI coach is not switched on yet. Ask your teacher.'}), 503
    if is_exempt():
        return None
    if calls_used() >= daily_limit():
        return jsonify({'error': "You have used today's AI allowance. Everything else keeps working, and it comes back within a day."}), 429
    return None


def _charge():
    """Counts the call before it is made, so two tabs at once cannot both slip through."""
    if is_exempt():
        return None
    row = LoginAttempt(key=_quota_key())
    db.session.add(row)
    db.session.commit()
    return row


def _refund(row):
    """Gives the call back when the AI service failed. The student got nothing for it."""
    if row is None:
        return
    db.session.delete(row)
    db.session.commit()


# ==================== ROUTES ====================

@ai_bp.get('/status')
@jwt_required()
def status():
    limit = daily_limit()
    used = calls_used()
    return jsonify({
        'configured': _configured(),
        'limit': None if is_exempt() else limit,
        'left': None if is_exempt() else max(0, limit - used),
    }), 200


@ai_bp.post('/coach')
@jwt_required()
def coach():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    question = data.get('question', '')
    image = data.get('image', '')
    if not isinstance(question, str) or not isinstance(image, str):
        return jsonify({'error': 'Send a valid coach question.'}), 400
    question = question.strip()
    if image and (len(image) > MAX_IMAGE or not IMAGE_RE.match(image)):
        return jsonify({'error': 'That photo could not be read. Try a smaller JPEG or PNG.'}), 400
    if not question and not image:
        return jsonify({'error': 'Write a question for the coach first.'}), 400

    blocked = _gate()
    if blocked:
        return blocked
    charged = _charge()

    try:
        if image:
            reply = call_groq([
                {'role': 'system', 'content': PHOTO_PROMPT},
                {'role': 'user', 'content': [
                    {'type': 'text', 'text': question[:MAX_PHOTO_QUESTION] or 'Help me with this question.'},
                    {'type': 'image_url', 'image_url': {'url': image}},
                ]},
            ], max_tokens=600, models=VISION_MODELS)
        else:
            reply = call_groq([
                {'role': 'system', 'content': COACH_PROMPT},
                {'role': 'user', 'content': question[:MAX_QUESTION]},
            ])
    except GroqError as exc:
        # Always 502: a 401 from Groq must never look like the student's own session expiring.
        _refund(charged)
        return jsonify({'error': str(exc)}), 502
    return jsonify({'reply': reply}), 200


@ai_bp.post('/cards')
@jwt_required()
def cards():
    data = request.get_json(silent=True)
    items = data.get('items') if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'Send at least one mistake.'}), 400

    clean = []
    for item in items[:MAX_CARDS]:
        if isinstance(item, dict):
            clean.append({
                'id': str(item.get('id', ''))[:60],
                'question': str(item.get('question', ''))[:600],
                'correct': str(item.get('answer', ''))[:600],
                'explanation': str(item.get('explanation', ''))[:800],
            })
    if not clean:
        return jsonify({'error': 'Send at least one mistake.'}), 400

    blocked = _gate()
    if blocked:
        return blocked
    charged = _charge()

    try:
        text = call_groq([
            {'role': 'system', 'content': CARDS_PROMPT},
            {'role': 'user', 'content': json.dumps(clean)},
        ], max_tokens=1400, temperature=0.3, json_mode=True)
    except GroqError as exc:
        _refund(charged)
        return jsonify({'error': str(exc)}), 502

    parsed = parse_json_reply(text)
    wanted = {item['id'] for item in clean}
    out = []
    for card in (parsed or {}).get('cards') or [] if isinstance(parsed, dict) else []:
        if isinstance(card, dict) and card.get('id') in wanted and card.get('front') and card.get('back'):
            out.append({
                'id': card['id'],
                'front': str(card['front'])[:300],
                'back': str(card['back'])[:500],
                'hook': str(card.get('hook') or '')[:200],
            })
    return jsonify({'cards': out}), 200
