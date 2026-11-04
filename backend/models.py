"""Database models for the SAT 1 & EST 1 study platform."""

from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value):
    return value.isoformat() if value else None


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False, default='')
    role = db.Column(db.String(20), nullable=False, default='student')  # student, teacher, admin
    grade_level = db.Column(db.String(20))
    school = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True)
    study_notes = db.relationship('StudyNote', backref='user', lazy=True)
    progress = db.relationship('StudentProgress', backref='user', lazy=True)
    state = db.relationship('UserState', backref='user', uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'grade_level': self.grade_level,
            'school': self.school,
            'created_at': iso(self.created_at),
            'is_active': self.is_active,
        }


class UserState(db.Model):
    """Practice progress synced from the website (streaks, answers, chapters, exam date)."""
    __tablename__ = 'user_state'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    data = db.Column(db.JSON, nullable=False, default=dict)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)


class LoginAttempt(db.Model):
    """Failed login attempts, used to slow down password guessing."""
    __tablename__ = 'login_attempts'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(160), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)


class LiveClass(db.Model):
    """A live audio/video class. Media runs through LiveKit; this row tracks who controls it."""
    __tablename__ = 'live_classes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    room = db.Column(db.String(64), nullable=False, unique=True)
    started_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    ended_at = db.Column(db.DateTime)
    open_mics = db.Column(db.Boolean, nullable=False, default=False)
    speakers = db.Column(db.JSON, nullable=False, default=list)  # user ids allowed to talk
    removed = db.Column(db.JSON, nullable=False, default=list)  # user ids removed by the teacher

    host = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'started_at': iso(self.started_at),
            'ended_at': iso(self.ended_at),
            'host_name': self.host.full_name if self.host else None,
            'open_mics': self.open_mics,
        }


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text)
    teacher = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(50))
    difficulty = db.Column(db.String(20))
    duration_weeks = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    chapters = db.relationship('Chapter', backref='course', lazy=True, cascade='all, delete-orphan', order_by='Chapter.order')

    def to_dict(self, include_chapters=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'teacher': self.teacher,
            'subject': self.subject,
            'difficulty': self.difficulty,
            'duration_weeks': self.duration_weeks,
            'created_at': iso(self.created_at),
            'is_active': self.is_active,
        }
        if include_chapters:
            data['chapters'] = [ch.to_dict() for ch in self.chapters]
        return data


class Chapter(db.Model):
    __tablename__ = 'chapters'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    order = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    quizzes = db.relationship('Quiz', backref='chapter', lazy=True, cascade='all, delete-orphan')
    progress = db.relationship('StudentProgress', backref='chapter', lazy=True)

    def to_dict(self, include_quizzes=False):
        data = {
            'id': self.id,
            'course_id': self.course_id,
            'name': self.name,
            'description': self.description,
            'content': self.content,
            'order': self.order,
            'created_at': iso(self.created_at),
        }
        if include_quizzes:
            data['quizzes'] = [q.to_dict() for q in self.quizzes]
        return data


class Quiz(db.Model):
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    total_questions = db.Column(db.Integer)
    time_limit_minutes = db.Column(db.Integer)
    passing_score = db.Column(db.Float, default=70.0)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan', order_by='Question.order')
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True)

    def to_dict(self, include_questions=False):
        data = {
            'id': self.id,
            'chapter_id': self.chapter_id,
            'title': self.title,
            'description': self.description,
            'total_questions': self.total_questions,
            'time_limit_minutes': self.time_limit_minutes,
            'passing_score': self.passing_score,
            'created_at': iso(self.created_at),
        }
        if include_questions:
            data['questions'] = [q.to_dict() for q in self.questions]
        return data


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20))
    options = db.Column(db.JSON)
    correct_answer = db.Column(db.String(255), nullable=False)
    explanation = db.Column(db.Text)
    difficulty = db.Column(db.String(20))
    points = db.Column(db.Integer, default=1)
    order = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self, include_answer=False):
        data = {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'options': self.options,
            'difficulty': self.difficulty,
            'points': self.points,
            'order': self.order,
        }
        if include_answer:
            data['correct_answer'] = self.correct_answer
            data['explanation'] = self.explanation
        return data


class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    score = db.Column(db.Float)
    max_score = db.Column(db.Float)
    percentage = db.Column(db.Float)
    passed = db.Column(db.Boolean)
    time_taken_minutes = db.Column(db.Integer)
    answers = db.Column(db.JSON)
    started_at = db.Column(db.DateTime, default=utcnow)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='in_progress')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'quiz_id': self.quiz_id,
            'score': self.score,
            'max_score': self.max_score,
            'percentage': self.percentage,
            'passed': self.passed,
            'time_taken_minutes': self.time_taken_minutes,
            'started_at': iso(self.started_at),
            'completed_at': iso(self.completed_at),
            'status': self.status,
        }


class StudentProgress(db.Model):
    __tablename__ = 'student_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    status = db.Column(db.String(20), default='not_started')
    completion_percentage = db.Column(db.Float, default=0)
    quizzes_passed = db.Column(db.Integer, default=0)
    quizzes_total = db.Column(db.Integer, default=0)
    average_score = db.Column(db.Float)
    last_accessed = db.Column(db.DateTime, default=utcnow)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'chapter_id': self.chapter_id,
            'course_id': self.course_id,
            'status': self.status,
            'completion_percentage': self.completion_percentage,
            'quizzes_passed': self.quizzes_passed,
            'quizzes_total': self.quizzes_total,
            'average_score': self.average_score,
            'last_accessed': iso(self.last_accessed),
            'completed_at': iso(self.completed_at),
        }


class StudyNote(db.Model):
    __tablename__ = 'study_notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'))
    title = db.Column(db.String(120))
    content = db.Column(db.Text, nullable=False)
    is_bookmark = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'chapter_id': self.chapter_id,
            'title': self.title,
            'content': self.content,
            'is_bookmark': self.is_bookmark,
            'created_at': iso(self.created_at),
            'updated_at': iso(self.updated_at),
        }
