"""Lesson and practice-question API.

The question banks live as JSON files under `backend/content/` rather than in the
database: production runs on Postgres with no migration tooling, and the `Question`
model has nowhere to put a lesson title, formula, rule or Arabic translation.
Regenerate the files with `python scripts/import_content.py`.

Nothing here ever sends a correct answer to the browser. `strip()` removes the
answer and explanation from every question on the way out; `/grade` is the only
way to learn whether a choice was right, and `/review` only returns answers for
questions the signed-in student has already got wrong.
"""

import json
import os
import random
import re
from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

practice_bp = Blueprint('practice', __name__, url_prefix='/api/practice')

CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content')
SUBJECTS = ('math', 'english', 'physics')
DAY_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
MAX_DAILY = 20
MAX_GRADE_ITEMS = 100
MAX_RANDOM = 100
MAX_BY_ID = 60


def _load():
    """Read the banks once at import. Returns (content, answer_index)."""
    content, index = {}, {}
    for subject in SUBJECTS:
        path = os.path.join(CONTENT_DIR, subject + '.json')
        if not os.path.exists(path):
            content[subject] = {'subject': subject, 'topics': [], 'lessons': [], 'practice': []}
            continue
        with open(path, encoding='utf-8') as handle:
            payload = json.load(handle)
        content[subject] = payload
        for question in payload.get('practice', []):
            index[question['id']] = question
    return content, index


CONTENT, BY_ID = _load()


def _topic_names(subject):
    return {t['id']: t['name'] for t in CONTENT[subject].get('topics', [])}


def strip(question, subject):
    """A question as the browser is allowed to see it: no answer, no explanation."""
    return {
        'id': question['id'],
        'subject': subject,
        'topicId': question.get('topicId', ''),
        'topic': _topic_names(subject).get(question.get('topicId', ''), ''),
        'lessonId': question.get('lessonId', ''),
        'lessonKey': question.get('lessonKey', ''),
        'domain': question.get('domain', ''),
        'difficulty': question.get('difficulty', ''),
        'question': question.get('question', ''),
        'choices': question.get('choices', []),
    }


def _subject(name):
    name = (name or '').strip().lower()
    return name if name in SUBJECTS else None


def _subject_of(question_id):
    name = question_id.split('-', 1)[0]
    return name if name in SUBJECTS else 'math'


def error(message, status):
    return jsonify({'error': message}), status


# ---------------------------------------------------------------------- routes

@practice_bp.get('/subjects')
def subjects():
    out = []
    for subject in SUBJECTS:
        payload = CONTENT[subject]
        out.append({
            'subject': subject,
            'topics': len(payload.get('topics', [])),
            'lessons': len(payload.get('lessons', [])),
            'questions': len(payload.get('practice', [])),
        })
    return jsonify({'subjects': out})


@practice_bp.get('/<subject>/topics')
def topics(subject):
    name = _subject(subject)
    if not name:
        return error('Unknown subject.', 400)
    payload = CONTENT[name]
    counts = {}
    for question in payload.get('practice', []):
        key = question.get('lessonId', '')
        counts[key] = counts.get(key, 0) + 1

    lessons = []
    for lesson in payload.get('lessons', []):
        lessons.append({
            'id': lesson['id'],
            'topicId': lesson.get('topicId', ''),
            'title': lesson.get('title', ''),
            'domain': lesson.get('domain', ''),
            'difficulty': lesson.get('difficulty', ''),
            'questions': counts.get(lesson['id'], 0),
        })
    return jsonify({'subject': name, 'topics': payload.get('topics', []), 'lessons': lessons})


@practice_bp.get('/<subject>/lessons/<lesson_id>')
def lesson(subject, lesson_id):
    name = _subject(subject)
    if not name:
        return error('Unknown subject.', 400)
    payload = CONTENT[name]
    found = next((l for l in payload.get('lessons', []) if l['id'] == lesson_id), None)
    if not found:
        return error('Lesson not found.', 404)

    questions = [strip(q, name) for q in payload.get('practice', [])
                 if q.get('lessonId') == lesson_id]
    detail = dict(found)
    detail['topic'] = _topic_names(name).get(found.get('topicId', ''), '')
    return jsonify({'subject': name, 'lesson': detail, 'questions': questions})


@practice_bp.get('/random')
def random_questions():
    wanted = request.args.get('subject', 'all')
    names = SUBJECTS if wanted == 'all' else ([_subject(wanted)] if _subject(wanted) else None)
    if not names:
        return error('Unknown subject.', 400)

    try:
        count = int(request.args.get('n', 10))
    except (TypeError, ValueError):
        count = 10
    count = max(1, min(count, MAX_RANDOM))

    pool = [(subject, q) for subject in names for q in CONTENT[subject].get('practice', [])]
    topics = {t.strip() for t in request.args.get('topics', '').split(',') if t.strip()}
    if topics:
        pool = [(subject, q) for subject, q in pool if q.get('topicId') in topics]
    if not pool:
        return jsonify({'questions': []})
    chosen = random.sample(pool, min(count, len(pool)))
    return jsonify({'questions': [strip(q, subject) for subject, q in chosen]})


@practice_bp.get('/daily')
def daily():
    """Today's mission: the same questions for everyone, a different set each day.

    The day comes from the browser so the mission turns over at the student's own
    midnight, which is the date their streak and progress already use.
    """
    try:
        count = int(request.args.get('n', 6))
    except (TypeError, ValueError):
        count = 6
    count = max(1, min(count, MAX_DAILY))
    day = request.args.get('day', '')
    if not DAY_RE.match(day):
        day = date.today().isoformat()

    pool = sorted(((subject, q) for subject in SUBJECTS for q in CONTENT[subject].get('practice', [])),
                  key=lambda pair: pair[1]['id'])
    if not pool:
        return jsonify({'day': day, 'questions': []})
    chosen = random.Random(day).sample(pool, min(count, len(pool)))
    return jsonify({'day': day, 'questions': [strip(q, subject) for subject, q in chosen]})


@practice_bp.get('/questions')
def questions_by_id():
    """Specific questions, without their answers. Used to bring back saved mistakes for review."""
    ids = [i.strip() for i in request.args.get('ids', '').split(',') if i.strip()][:MAX_BY_ID]
    out = []
    for question_id in ids:
        question = BY_ID.get(question_id)
        if question:
            out.append(strip(question, _subject_of(question_id)))
    return jsonify({'questions': out})


@practice_bp.get('/<subject>/revision')
def revision(subject):
    """Every lesson's rule, formula, example and tip, for the one-page revision sheet."""
    name = _subject(subject)
    if not name:
        return error('Unknown subject.', 400)
    payload = CONTENT[name]
    lessons = [{
        'id': lesson['id'],
        'topicId': lesson.get('topicId', ''),
        'title': lesson.get('title', ''),
        'formula': lesson.get('formula', ''),
        'example': lesson.get('example', ''),
        'tip': lesson.get('tip', ''),
        'arabic': lesson.get('arabic', ''),
        'explanation': lesson.get('explanation', []),
    } for lesson in payload.get('lessons', [])]
    return jsonify({'subject': name, 'topics': payload.get('topics', []), 'lessons': lessons})


@practice_bp.post('/grade')
def grade():
    data = request.get_json(silent=True)
    items = data.get('items') if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return error('Send items: [{id, answer}].', 400)
    if len(items) > MAX_GRADE_ITEMS:
        return error('Too many items (max %d).' % MAX_GRADE_ITEMS, 400)

    results, correct, total = [], 0, 0
    for item in items:
        if not isinstance(item, dict):
            continue
        question = BY_ID.get(str(item.get('id', '')))
        if not question:
            results.append({'id': str(item.get('id', ''))[:60], 'error': 'Question not found.'})
            continue
        chosen = str(item.get('answer', '')).strip().upper()[:1]
        is_right = bool(chosen) and chosen == question['answer']
        total += 1
        if is_right:
            correct += 1
        results.append({
            'id': question['id'],
            'correct': is_right,
            'selected': chosen,
            'answer': question['answer'],
            'explanation': question.get('explanation', []),
        })

    percent = int(round(correct * 100.0 / total)) if total else 0
    return jsonify({'results': results, 'score': correct, 'total': total, 'percent': percent})


@practice_bp.get('/review')
@jwt_required()
def review():
    """The signed-in student's own wrong answers, with the explanations.

    Answers are revealed here only for questions this account has already missed,
    which is why it reads the id list from the server's copy of their state rather
    than trusting a list of ids sent by the caller.
    """
    state = getattr(current_user, 'state', None)
    stored = (state.data if state and isinstance(state.data, dict) else {}) or {}
    mistakes = stored.get('mistakes') if isinstance(stored.get('mistakes'), list) else []

    out = []
    for entry in mistakes:
        if not isinstance(entry, dict):
            continue
        question = BY_ID.get(str(entry.get('id', '')))
        if not question:
            continue
        detail = strip(question, _subject_of(question['id']))
        detail['answer'] = question['answer']
        detail['explanation'] = question.get('explanation', [])
        detail['date'] = entry.get('date', '')
        out.append(detail)
    return jsonify({'total': len(out), 'questions': out})
