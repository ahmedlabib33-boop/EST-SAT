"""API routes for the SAT 1 & EST 1 study platform."""

import re
import secrets
from datetime import timedelta
from functools import wraps

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, current_user, jwt_required
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db
from .models import (Chapter, Course, LoginAttempt, Quiz, QuizAttempt, StudentProgress, StudyNote,
                     User, UserState, utcnow)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
courses_bp = Blueprint('courses', __name__, url_prefix='/api/courses')
quiz_bp = Blueprint('quiz', __name__, url_prefix='/api/quizzes')
progress_bp = Blueprint('progress', __name__, url_prefix='/api/progress')
user_bp = Blueprint('user', __name__, url_prefix='/api/user')
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')
blueprints = [auth_bp, courses_bp, quiz_bp, progress_bp, user_bp, admin_bp]

USERNAME_RE = re.compile(r'^[A-Za-z0-9_.]{3,30}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
CHAPTER_RE = re.compile(r'^(math|physics|english)-\d{1,2}$')
QUESTION_ID_RE = re.compile(r'^(math|english|physics)-practice-\d{1,5}$')
LESSON_ID_RE = re.compile(r'^(math|english|physics)-lesson-\d{1,5}$')
TOPIC_KEY_RE = re.compile(r"^(math|english|physics)\|[A-Za-z0-9 .,&'-]{1,60}$")
ASSIGNMENT_ID_RE = re.compile(r'^a-\d{1,16}$')
GOAL_ID_RE = re.compile(r'^g-\d{1,16}$')
ATTEMPT_SUBJECTS = ('math', 'english', 'physics', 'mixed')
ATTEMPT_LEVELS = ('standard', 'challenge')
GOAL_KINDS = ('level', 'streak', 'exam', 'topic')
MAX_MISTAKES = 100
STAFF_ROLES = ('admin', 'teacher')
FAIL_WINDOW = timedelta(minutes=15)
MAX_FAILS_PER_ACCOUNT = 8
# Generous because a whole classroom often shares one school IP address.
MAX_FAILS_PER_IP = 150
# Checked when the username doesn't exist, so a wrong username takes as long as a wrong password.
_DUMMY_HASH = generate_password_hash('estsat-timing-equaliser')


# ==================== HELPERS ====================

def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def error(message, status):
    return jsonify({'error': message}), status


def clean_text(data, key, max_len):
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(key)
    return value.strip()[:max_len]


def token_for(user):
    return create_access_token(identity=str(user.id), additional_claims={'role': user.role})


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                return error('You do not have access to this.', 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def can_view(user_id):
    return current_user.id == user_id or current_user.role in STAFF_ROLES


def client_ip():
    ip = request.headers.get('X-Real-IP') or request.headers.get('X-Forwarded-For', '').split(',')[0]
    return (ip.strip() or request.remote_addr or 'unknown')[:64]


def recent_failures(key):
    since = utcnow() - FAIL_WINDOW
    return LoginAttempt.query.filter(LoginAttempt.key == key, LoginAttempt.created_at >= since).count()


def _count(value, upper):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, min(int(value), upper))


def clean_state(raw):
    """Validate the practice-progress blob the website syncs, dropping anything unexpected."""
    if not isinstance(raw, dict):
        raise ValueError('state')
    stats = raw.get('stats') if isinstance(raw.get('stats'), dict) else {}
    answered = _count(stats.get('answered'), 10 ** 7)

    days_in = raw.get('days') if isinstance(raw.get('days'), dict) else {}
    days = {}
    for key in sorted(k for k in days_in if isinstance(k, str) and DATE_RE.match(k))[-400:]:
        n = _count(days_in[key], 100000)
        if n:
            days[key] = n

    chapters = []
    for c in raw.get('chapters') if isinstance(raw.get('chapters'), list) else []:
        if isinstance(c, str) and CHAPTER_RE.match(c) and c not in chapters:
            chapters.append(c)

    exam = raw.get('exam')
    exam = exam if isinstance(exam, str) and DATE_RE.match(exam) else ''

    mission = raw.get('mission') if isinstance(raw.get('mission'), dict) else {}
    m_date = mission.get('date')
    m_date = m_date if isinstance(m_date, str) and DATE_RE.match(m_date) else ''
    done = []
    for i in mission.get('done') if isinstance(mission.get('done'), list) else []:
        if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < 1000 and i not in done:
            done.append(i)

    # Questions answered wrongly, for the review list. Only the id and the date are
    # kept: the question text, correct answer and explanation stay on the server and
    # are fetched from /api/practice/review, so the blob stays small and nothing here
    # can be used to recover an answer key.
    mistakes, seen = [], set()
    for m in raw.get('mistakes') if isinstance(raw.get('mistakes'), list) else []:
        if not isinstance(m, dict):
            continue
        qid = m.get('id')
        if not isinstance(qid, str) or not QUESTION_ID_RE.match(qid) or qid in seen:
            continue
        date = m.get('date')
        seen.add(qid)
        mistakes.append({'id': qid, 'date': date if isinstance(date, str) and DATE_RE.match(date) else ''})
    kept = mistakes[-MAX_MISTAKES:]

    return {
        'stats': {
            'answered': answered,
            'correct': min(_count(stats.get('correct'), 10 ** 7), answered),
            'time': _count(stats.get('time'), 10 ** 9),
        },
        'days': days,
        'chapters': chapters[:20],
        'exam': exam,
        'mission': {'date': m_date, 'done': done[:20]},
        'mistakes': kept,
        **clean_study_extras(raw, {m['id'] for m in kept}),
    }


def _date_or_blank(value):
    return value if isinstance(value, str) and DATE_RE.match(value) else ''


def _short_text(value, max_len):
    return value.strip()[:max_len] if isinstance(value, str) else ''


def _map(raw, key):
    value = raw.get(key)
    return value if isinstance(value, dict) else {}


def _list(raw, key):
    value = raw.get(key)
    return value if isinstance(value, list) else []


def _date_list(values, limit):
    out = []
    for d in values:
        if isinstance(d, str) and DATE_RE.match(d) and d not in out:
            out.append(d)
    return out[-limit:]


def clean_study_extras(raw, keep_mistakes=None):
    """The fields behind Today, Review, Exam, Rewards, Focus and the Parent view. All bounded."""
    # A review schedule is looked up by mistake id, so only the mistakes that were kept need one.
    # Capping this list on its own used to keep the oldest schedules and drop the newest.
    reviews = {}
    for question_id, entry in _map(raw, 'reviews').items():
        if not isinstance(question_id, str) or not QUESTION_ID_RE.match(question_id) or not isinstance(entry, dict):
            continue
        if keep_mistakes is not None and question_id not in keep_mistakes:
            continue
        if len(reviews) >= MAX_MISTAKES:
            break
        reviews[question_id] = {
            'stage': _count(entry.get('stage'), 4),
            'due': _date_or_blank(entry.get('due')),
            'last': _date_or_blank(entry.get('last')),
        }

    # Keep the topics with the most answers, not whichever arrived first.
    rows = []
    for key, pair in _map(raw, 'topics').items():
        if isinstance(key, str) and TOPIC_KEY_RE.match(key) and isinstance(pair, list) and len(pair) == 2:
            answered = _count(pair[0], 10 ** 6)
            if answered:
                rows.append((answered, key, [answered, min(_count(pair[1], 10 ** 6), answered)]))
    rows.sort(key=lambda row: (-row[0], row[1]))
    topics = {key: pair for _, key, pair in rows[:80]}

    lessons = []
    for lesson_id in _list(raw, 'lessons'):
        if isinstance(lesson_id, str) and LESSON_ID_RE.match(lesson_id) and lesson_id not in lessons:
            lessons.append(lesson_id)

    attempts = []
    for a in _list(raw, 'attempts'):
        if not isinstance(a, dict) or a.get('subject') not in ATTEMPT_SUBJECTS or not _date_or_blank(a.get('date')):
            continue
        total = _count(a.get('total'), 100)
        if total:
            attempts.append({
                'date': a['date'],
                'subject': a['subject'],
                'score': min(_count(a.get('score'), 100), total),
                'total': total,
                'percent': _count(a.get('percent'), 100),
                'seconds': _count(a.get('seconds'), 6 * 3600),
                'level': a['level'] if a.get('level') in ATTEMPT_LEVELS else 'standard',
            })

    time_in = _map(raw, 'time')
    study_time = {}
    for key in sorted(k for k in time_in if isinstance(k, str) and DATE_RE.match(k))[-60:]:
        seconds = _count(time_in[key], 86400)
        if seconds:
            study_time[key] = seconds

    week = _map(raw, 'week')
    freezes = _map(raw, 'freezes')

    assignments = []
    for a in _list(raw, 'assignments'):
        if not isinstance(a, dict) or a.get('kind') not in ('lesson', 'exam'):
            continue
        target = _short_text(a.get('target'), 60)
        if isinstance(a.get('id'), str) and ASSIGNMENT_ID_RE.match(a['id']) and target:
            assignments.append({
                'id': a['id'],
                'kind': a['kind'],
                'target': target,
                'title': _short_text(a.get('title'), 120),
                'due': _date_or_blank(a.get('due')),
                'note': _short_text(a.get('note'), 140),
                'created': _date_or_blank(a.get('created')),
                'sameDay': _count(a.get('sameDay'), 100),
            })

    goals = []
    for g in _list(raw, 'goals'):
        if not isinstance(g, dict) or g.get('kind') not in GOAL_KINDS:
            continue
        target = g.get('target')
        target = str(target)[:60] if isinstance(target, (str, int)) and not isinstance(target, bool) else ''
        if isinstance(g.get('id'), str) and GOAL_ID_RE.match(g['id']) and target:
            goals.append({
                'id': g['id'],
                'kind': g['kind'],
                'target': target,
                'label': _short_text(g.get('label'), 120),
                'message': _short_text(g.get('message'), 600),
                'hasVoice': g.get('hasVoice') is True,
                'created': _date_or_blank(g.get('created')),
                'unlockedAt': _date_or_blank(g.get('unlockedAt')),
            })

    music = raw.get('music')
    music = music if isinstance(music, str) and music.startswith('https://') and len(music) <= 300 else ''

    return {
        'reviews': reviews,
        'topics': topics,
        'lessons': lessons[:400],
        'attempts': attempts[:30],
        'time': study_time,
        'week': {
            'start': _date_or_blank(week.get('start')),
            'lessons': _count(week.get('lessons'), 10 ** 5),
            'practice': _count(week.get('practice'), 10 ** 5),
            'reviews': _count(week.get('reviews'), 10 ** 5),
            'exams': _count(week.get('exams'), 10 ** 5),
        },
        'xp': _count(raw.get('xp'), 10 ** 7),
        'freezes': {
            'usedDays': _date_list(_list(freezes, 'usedDays'), 200),
            'earnedOn': _date_list(_list(freezes, 'earnedOn'), 200),
        },
        'assignments': assignments[:40],
        'goals': goals[:30],
        'music': music,
    }


def summarize_state(data):
    data = data or {}
    stats = data.get('stats') or {}
    days = data.get('days') or {}
    answered = stats.get('answered', 0)
    return {
        'answered': answered,
        'accuracy': round(stats.get('correct', 0) / answered * 100) if answered else None,
        'chapters_done': len(data.get('chapters') or []),
        'active_days': len(days),
        'last_active': max(days) if days else None,
        'exam': data.get('exam') or None,
        'to_review': len(data.get('mistakes') or []),
    }


# ==================== AUTH ====================

@auth_bp.post('/register')
def register():
    data = body()
    try:
        full_name = clean_text(data, 'full_name', 120) or ''
        username = clean_text(data, 'username', 80) or ''
        email = (clean_text(data, 'email', 120) or '').lower()
        grade_level = clean_text(data, 'grade_level', 20) or None
        school = clean_text(data, 'school', 120) or None
    except ValueError:
        return error('Please check the form and try again.', 400)
    password = data.get('password')

    if not full_name:
        return error('Please enter your full name.', 400)
    if not USERNAME_RE.match(username):
        return error('Usernames are 3–30 characters: letters, numbers, dots or underscores.', 400)
    if not EMAIL_RE.match(email):
        return error('Please enter a valid email address.', 400)
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        return error('Your password needs at least 8 characters.', 400)
    if User.query.filter(func.lower(User.username) == username.lower()).first():
        return error('That username is taken. Try another one.', 409)
    if User.query.filter(func.lower(User.email) == email).first():
        return error('An account with this email already exists. Try logging in.', 409)

    user = User(username=username, email=email, full_name=full_name, grade_level=grade_level,
                school=school, role='student')
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error('That username or email is already registered.', 409)

    return jsonify({'message': 'Account created', 'access_token': token_for(user), 'user': user.to_dict()}), 201


@auth_bp.post('/login')
def login():
    data = body()
    ident = data.get('username') or data.get('email') or data.get('login')
    password = data.get('password')
    if not isinstance(ident, str) or not ident.strip() or not isinstance(password, str) or not password:
        return error('Enter your username or email and your password.', 400)
    ident = ident.strip().lower()[:120]

    account_key, ip_key = 'acct:' + ident, 'ip:' + client_ip()
    if recent_failures(account_key) >= MAX_FAILS_PER_ACCOUNT or recent_failures(ip_key) >= MAX_FAILS_PER_IP:
        resp = jsonify({'error': 'Too many failed attempts. Please wait 15 minutes and try again.'})
        resp.headers['Retry-After'] = str(int(FAIL_WINDOW.total_seconds()))
        return resp, 429

    user = User.query.filter(or_(func.lower(User.username) == ident, func.lower(User.email) == ident)).first()
    if user is None:
        check_password_hash(_DUMMY_HASH, password)
        valid = False
    else:
        valid = user.check_password(password)

    if not valid:
        db.session.add_all([LoginAttempt(key=account_key), LoginAttempt(key=ip_key)])
        LoginAttempt.query.filter(LoginAttempt.created_at < utcnow() - timedelta(days=1)).delete(synchronize_session=False)
        db.session.commit()
        return error('Wrong username/email or password.', 401)
    if not user.is_active:
        return error('This account is disabled. Please contact your teacher.', 403)

    LoginAttempt.query.filter_by(key=account_key).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'message': 'Login successful', 'access_token': token_for(user), 'user': user.to_dict()}), 200


@auth_bp.get('/me')
@jwt_required()
def me():
    return jsonify({'user': current_user.to_dict()}), 200


@auth_bp.post('/logout')
@jwt_required()
def logout():
    return jsonify({'message': 'Logged out'}), 200


@auth_bp.post('/refresh')
@jwt_required()
def refresh_token():
    return jsonify({'access_token': token_for(current_user)}), 200


# ==================== USER ====================

@user_bp.get('/profile')
@jwt_required()
def get_profile():
    return jsonify(current_user.to_dict()), 200


@user_bp.put('/profile')
@jwt_required()
def update_profile():
    data = body()
    try:
        full_name = clean_text(data, 'full_name', 120)
        grade_level = clean_text(data, 'grade_level', 20)
        school = clean_text(data, 'school', 120)
    except ValueError:
        return error('Please check the form and try again.', 400)
    if full_name is not None:
        if not full_name:
            return error('Please enter your full name.', 400)
        current_user.full_name = full_name
    if grade_level is not None:
        current_user.grade_level = grade_level or None
    if school is not None:
        current_user.school = school or None
    db.session.commit()
    return jsonify({'message': 'Profile updated', 'user': current_user.to_dict()}), 200


@user_bp.put('/password')
@jwt_required()
def change_password():
    data = body()
    current_password, new_password = data.get('current_password'), data.get('new_password')
    if not isinstance(current_password, str) or not current_user.check_password(current_password):
        return error('Your current password is not correct.', 400)
    if not isinstance(new_password, str) or not 8 <= len(new_password) <= 128:
        return error('Your new password needs at least 8 characters.', 400)
    current_user.set_password(new_password)
    db.session.commit()
    return jsonify({'message': 'Password updated'}), 200


@user_bp.get('/state')
@jwt_required()
def get_state():
    state = db.session.get(UserState, current_user.id)
    return jsonify({
        'data': state.data if state else {},
        'updated_at': state.updated_at.isoformat() if state and state.updated_at else None,
    }), 200


@user_bp.put('/state')
@jwt_required()
def put_state():
    try:
        cleaned = clean_state(body().get('data'))
    except ValueError:
        return error('Invalid progress data.', 400)
    state = db.session.get(UserState, current_user.id)
    if state is None:
        state = UserState(user_id=current_user.id, data=cleaned)
        db.session.add(state)
    else:
        state.data = cleaned
        state.updated_at = utcnow()
    db.session.commit()
    return jsonify({'data': cleaned, 'updated_at': state.updated_at.isoformat()}), 200


@user_bp.get('/notes')
@jwt_required()
def get_user_notes():
    notes = StudyNote.query.filter_by(user_id=current_user.id).order_by(StudyNote.updated_at.desc()).all()
    return jsonify({'total_notes': len(notes), 'notes': [n.to_dict() for n in notes]}), 200


@user_bp.post('/notes')
@jwt_required()
def create_note():
    data = body()
    content = data.get('content')
    if not isinstance(content, str) or not content.strip():
        return error('Note content is required.', 400)
    chapter_id = data.get('chapter_id')
    if chapter_id is not None and (not isinstance(chapter_id, int) or not db.session.get(Chapter, chapter_id)):
        return error('Chapter not found.', 400)
    title = data.get('title') if isinstance(data.get('title'), str) else None
    note = StudyNote(user_id=current_user.id, chapter_id=chapter_id, title=(title or '')[:120] or None,
                     content=content[:20000], is_bookmark=bool(data.get('is_bookmark', False)))
    db.session.add(note)
    db.session.commit()
    return jsonify({'message': 'Note created', 'note': note.to_dict()}), 201


@user_bp.put('/notes/<int:note_id>')
@jwt_required()
def update_note(note_id):
    note = db.session.get(StudyNote, note_id)
    if not note or note.user_id != current_user.id:
        return error('Note not found.', 404)
    data = body()
    if isinstance(data.get('title'), str):
        note.title = data['title'][:120]
    if isinstance(data.get('content'), str) and data['content'].strip():
        note.content = data['content'][:20000]
    if 'is_bookmark' in data:
        note.is_bookmark = bool(data['is_bookmark'])
    db.session.commit()
    return jsonify({'message': 'Note updated', 'note': note.to_dict()}), 200


@user_bp.delete('/notes/<int:note_id>')
@jwt_required()
def delete_note(note_id):
    note = db.session.get(StudyNote, note_id)
    if not note or note.user_id != current_user.id:
        return error('Note not found.', 404)
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted'}), 200


# ==================== COURSES ====================

@courses_bp.get('')
def get_courses():
    courses = Course.query.filter_by(is_active=True).order_by(Course.id).all()
    return jsonify({'total': len(courses), 'courses': [c.to_dict(include_chapters=True) for c in courses]}), 200


@courses_bp.get('/<int:course_id>')
def get_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        return error('Course not found.', 404)
    return jsonify(course.to_dict(include_chapters=True)), 200


@courses_bp.get('/<int:course_id>/chapters')
def get_course_chapters(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        return error('Course not found.', 404)
    chapters = Chapter.query.filter_by(course_id=course_id).order_by(Chapter.order).all()
    return jsonify({'course': course.to_dict(), 'chapters': [ch.to_dict(include_quizzes=True) for ch in chapters]}), 200


@courses_bp.post('')
@roles_required('admin')
def create_course():
    data = body()
    name = data.get('name')
    if not isinstance(name, str) or not name.strip():
        return error('Course name is required.', 400)
    course = Course(name=name.strip()[:120], description=data.get('description'),
                    teacher=data.get('teacher') or 'Ahmed Labib', subject=data.get('subject'),
                    difficulty=data.get('difficulty'), duration_weeks=data.get('duration_weeks'))
    db.session.add(course)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error('A course with this name already exists.', 409)
    return jsonify({'message': 'Course created', 'course': course.to_dict()}), 201


# ==================== QUIZZES ====================

@quiz_bp.get('/<int:quiz_id>')
def get_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        return error('Quiz not found.', 404)
    return jsonify(quiz.to_dict(include_questions=True)), 200


@quiz_bp.post('/<int:quiz_id>/start')
@jwt_required()
def start_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        return error('Quiz not found.', 404)
    attempt = QuizAttempt(user_id=current_user.id, quiz_id=quiz_id, status='in_progress')
    db.session.add(attempt)
    db.session.commit()
    return jsonify({'message': 'Quiz started', 'attempt_id': attempt.id, 'quiz': quiz.to_dict(include_questions=True)}), 200


@quiz_bp.post('/<int:quiz_id>/submit')
@jwt_required()
def submit_quiz(quiz_id):
    data = body()
    answers = data.get('answers') if isinstance(data.get('answers'), dict) else {}
    attempt = db.session.get(QuizAttempt, data.get('attempt_id')) if isinstance(data.get('attempt_id'), int) else None
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz:
        return error('Quiz not found.', 404)
    if not attempt or attempt.user_id != current_user.id or attempt.quiz_id != quiz_id:
        return error('Quiz attempt not found.', 404)
    if attempt.status == 'completed':
        return error('This attempt was already submitted.', 409)

    score, max_score, review = 0, 0, {}
    for question in quiz.questions:
        max_score += question.points or 0
        answer = answers.get(str(question.id))
        if answer is None:
            continue
        is_correct = str(answer).strip().lower() == question.correct_answer.strip().lower()
        review[str(question.id)] = {'user_answer': str(answer), 'correct_answer': question.correct_answer,
                                    'is_correct': is_correct, 'explanation': question.explanation}
        if is_correct:
            score += question.points or 0

    percentage = (score / max_score * 100) if max_score else 0
    attempt.score, attempt.max_score, attempt.percentage = score, max_score, percentage
    attempt.passed = percentage >= (quiz.passing_score or 0)
    attempt.answers = {k: str(v) for k, v in answers.items()}
    attempt.completed_at = utcnow()
    attempt.status = 'completed'

    chapter = quiz.chapter
    progress = StudentProgress.query.filter_by(user_id=current_user.id, chapter_id=chapter.id).first()
    if not progress:
        progress = StudentProgress(user_id=current_user.id, chapter_id=chapter.id, course_id=chapter.course_id,
                                   quizzes_passed=0, quizzes_total=0)
        db.session.add(progress)
    previous_total = progress.quizzes_total or 0
    progress.quizzes_total = previous_total + 1
    progress.quizzes_passed = (progress.quizzes_passed or 0) + (1 if attempt.passed else 0)
    progress.average_score = ((progress.average_score or 0) * previous_total + percentage) / progress.quizzes_total
    progress.last_accessed = utcnow()
    db.session.commit()

    return jsonify({'message': 'Quiz submitted', 'score': score, 'max_score': max_score, 'percentage': percentage,
                    'passed': attempt.passed, 'answers_review': review}), 200


@quiz_bp.get('/attempts/<int:user_id>')
@jwt_required()
def get_user_attempts(user_id):
    if not can_view(user_id):
        return error('You do not have access to this.', 403)
    attempts = QuizAttempt.query.filter_by(user_id=user_id).order_by(QuizAttempt.started_at.desc()).all()
    return jsonify({'user_id': user_id, 'total_attempts': len(attempts), 'attempts': [a.to_dict() for a in attempts]}), 200


# ==================== PROGRESS ====================

@progress_bp.get('/student/<int:user_id>')
@jwt_required()
def get_student_progress(user_id):
    if not can_view(user_id):
        return error('You do not have access to this.', 403)
    progress = StudentProgress.query.filter_by(user_id=user_id).all()
    return jsonify({'user_id': user_id, 'total_progress_entries': len(progress), 'progress': [p.to_dict() for p in progress]}), 200


@progress_bp.get('/course/<int:course_id>/students')
@roles_required(*STAFF_ROLES)
def get_course_student_progress(course_id):
    if not db.session.get(Course, course_id):
        return error('Course not found.', 404)
    progress = StudentProgress.query.filter_by(course_id=course_id).all()
    return jsonify({'course_id': course_id, 'total_students': len({p.user_id for p in progress}),
                    'progress': [p.to_dict() for p in progress]}), 200


# ==================== TEACHER / ADMIN ====================

@admin_bp.get('/users')
@roles_required(*STAFF_ROLES)
def get_all_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({'total_users': len(users), 'users': [u.to_dict() for u in users]}), 200


@admin_bp.get('/students')
@roles_required(*STAFF_ROLES)
def get_students():
    rows = (db.session.query(User, UserState)
            .outerjoin(UserState, UserState.user_id == User.id)
            .filter(User.role == 'student')
            .order_by(User.created_at.desc())
            .all())
    students = [dict(user.to_dict(), progress=summarize_state(state.data if state else None)) for user, state in rows]
    return jsonify({'total': len(students), 'students': students}), 200


@admin_bp.get('/students/<int:user_id>')
@roles_required(*STAFF_ROLES)
def get_student(user_id):
    user = db.session.get(User, user_id)
    if not user or user.role != 'student':
        return error('Student not found.', 404)
    state = db.session.get(UserState, user_id)
    data = state.data if state else {}
    return jsonify({
        'student': dict(user.to_dict(), progress=summarize_state(data)),
        'state': data,
        'state_updated_at': state.updated_at.isoformat() if state and state.updated_at else None,
    }), 200


@admin_bp.patch('/users/<int:user_id>')
@roles_required(*STAFF_ROLES)
def update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return error('User not found.', 404)
    if user.id == current_user.id:
        return error('You can’t change your own account from here.', 400)
    if user.role == 'admin':
        return error('Admin accounts can’t be changed from here.', 403)
    data = body()
    if 'role' in data:
        if current_user.role != 'admin':
            return error('Only an admin can change roles.', 403)
        if data['role'] not in ('student', 'teacher'):
            return error('Role must be student or teacher.', 400)
        user.role = data['role']
    if 'is_active' in data:
        if user.role != 'student' and current_user.role != 'admin':
            return error('Only an admin can disable teacher accounts.', 403)
        user.is_active = bool(data['is_active'])
    db.session.commit()
    return jsonify({'user': user.to_dict()}), 200


@admin_bp.post('/users/<int:user_id>/reset-password')
@roles_required(*STAFF_ROLES)
def reset_password(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return error('User not found.', 404)
    if user.role != 'student' and current_user.role != 'admin':
        return error('Only an admin can reset staff passwords.', 403)
    temporary = secrets.token_urlsafe(9)
    user.set_password(temporary)
    db.session.commit()
    return jsonify({'message': 'Password reset. Share the temporary password with the student privately.',
                    'temporary_password': temporary}), 200


@admin_bp.get('/statistics')
@roles_required(*STAFF_ROLES)
def get_statistics():
    return jsonify({
        'total_users': User.query.count(),
        'total_students': User.query.filter_by(role='student').count(),
        'total_courses': Course.query.count(),
        'total_quizzes': Quiz.query.count(),
        'total_quiz_attempts': QuizAttempt.query.count(),
        'timestamp': utcnow().isoformat(),
    }), 200
