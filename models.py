"""
Database Models for SAT 1 & EST 1 Study Platform
"""

from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    """User model for students and teachers"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='student')  # student, teacher, admin
    grade_level = db.Column(db.String(20))
    school = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True)
    study_notes = db.relationship('StudyNote', backref='user', lazy=True)
    progress = db.relationship('StudentProgress', backref='user', lazy=True)

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
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }

class Course(db.Model):
    """Course model"""
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text)
    teacher = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(50))  # Mathematics, Physics
    difficulty = db.Column(db.String(20))  # Beginner, Intermediate, Advanced
    duration_weeks = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    chapters = db.relationship('Chapter', backref='course', lazy=True, cascade='all, delete-orphan')

    def to_dict(self, include_chapters=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'teacher': self.teacher,
            'subject': self.subject,
            'difficulty': self.difficulty,
            'duration_weeks': self.duration_weeks,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }
        if include_chapters:
            data['chapters'] = [ch.to_dict() for ch in self.chapters]
        return data

class Chapter(db.Model):
    """Chapter model"""
    __tablename__ = 'chapters'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)  # Study material content
    order = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
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
            'created_at': self.created_at.isoformat()
        }
        if include_quizzes:
            data['quizzes'] = [q.to_dict() for q in self.quizzes]
        return data

class Quiz(db.Model):
    """Quiz model"""
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    total_questions = db.Column(db.Integer)
    time_limit_minutes = db.Column(db.Integer)  # 0 means no time limit
    passing_score = db.Column(db.Float, default=70.0)  # Percentage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
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
            'created_at': self.created_at.isoformat()
        }
        if include_questions:
            data['questions'] = [q.to_dict() for q in self.questions]
        return data

class Question(db.Model):
    """Question model for quizzes"""
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20))  # multiple_choice, true_false, short_answer
    options = db.Column(db.JSON)  # For multiple choice: {'a': '...', 'b': '...', 'c': '...', 'd': '...'}
    correct_answer = db.Column(db.String(255), nullable=False)
    explanation = db.Column(db.Text)  # Explanation for the correct answer
    difficulty = db.Column(db.String(20))  # Easy, Medium, Hard
    points = db.Column(db.Integer, default=1)
    order = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self, include_answer=False):
        data = {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'options': self.options,
            'difficulty': self.difficulty,
            'points': self.points,
            'order': self.order
        }
        if include_answer:
            data['correct_answer'] = self.correct_answer
            data['explanation'] = self.explanation
        return data

class QuizAttempt(db.Model):
    """Student quiz attempts"""
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    score = db.Column(db.Float)
    max_score = db.Column(db.Float)
    percentage = db.Column(db.Float)
    passed = db.Column(db.Boolean)
    time_taken_minutes = db.Column(db.Integer)
    answers = db.Column(db.JSON)  # {question_id: answer}
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='completed')  # in_progress, completed

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
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status
        }

class StudentProgress(db.Model):
    """Track student progress through courses"""
    __tablename__ = 'student_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    status = db.Column(db.String(20), default='not_started')  # not_started, in_progress, completed
    completion_percentage = db.Column(db.Float, default=0)
    quizzes_passed = db.Column(db.Integer, default=0)
    quizzes_total = db.Column(db.Integer, default=0)
    average_score = db.Column(db.Float)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
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
            'last_accessed': self.last_accessed.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class StudyNote(db.Model):
    """Student study notes and bookmarks"""
    __tablename__ = 'study_notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=False)
    title = db.Column(db.String(120))
    content = db.Column(db.Text, nullable=False)
    is_bookmark = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'chapter_id': self.chapter_id,
            'title': self.title,
            'content': self.content,
            'is_bookmark': self.is_bookmark,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
