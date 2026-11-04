"""
API Routes for SAT 1 & EST 1 Study Platform
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app import db
from models import User, Course, Chapter, Quiz, Question, QuizAttempt, StudentProgress, StudyNote
from datetime import datetime
from functools import wraps

# Define blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
courses_bp = Blueprint('courses', __name__, url_prefix='/api/courses')
quiz_bp = Blueprint('quiz', __name__, url_prefix='/api/quizzes')
progress_bp = Blueprint('progress', __name__, url_prefix='/api/progress')
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')
user_bp = Blueprint('user', __name__, url_prefix='/api/user')

# Helper function for admin check
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    return wrapper

# ==================== AUTHENTICATION ROUTES ====================

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()

    # Validation
    if not data or not data.get('username') or not data.get('password') or not data.get('email'):
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if user exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409

    # Create new user
    user = User(
        username=data['username'],
        email=data['email'],
        full_name=data.get('full_name', ''),
        grade_level=data.get('grade_level'),
        school=data.get('school'),
        role='student'
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict()
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400

    user = User.query.filter_by(username=data['username']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401

    if not user.is_active:
        return jsonify({'error': 'User account is inactive'}), 403

    # Create JWT token
    access_token = create_access_token(identity=user.id)

    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client should discard token)"""
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required()
def refresh_token():
    """Refresh JWT token"""
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    return jsonify({'access_token': access_token}), 200

# ==================== COURSE ROUTES ====================

@courses_bp.route('', methods=['GET'])
def get_courses():
    """Get all courses"""
    courses = Course.query.filter_by(is_active=True).all()
    return jsonify({
        'total': len(courses),
        'courses': [course.to_dict(include_chapters=True) for course in courses]
    }), 200

@courses_bp.route('/<int:course_id>', methods=['GET'])
def get_course(course_id):
    """Get specific course"""
    course = Course.query.get(course_id)

    if not course:
        return jsonify({'error': 'Course not found'}), 404

    return jsonify(course.to_dict(include_chapters=True)), 200

@courses_bp.route('/<int:course_id>/chapters', methods=['GET'])
def get_course_chapters(course_id):
    """Get all chapters in a course"""
    course = Course.query.get(course_id)

    if not course:
        return jsonify({'error': 'Course not found'}), 404

    chapters = Chapter.query.filter_by(course_id=course_id).order_by(Chapter.order).all()

    return jsonify({
        'course': course.to_dict(),
        'chapters': [ch.to_dict(include_quizzes=True) for ch in chapters]
    }), 200

@courses_bp.route('', methods=['POST'])
@admin_required
def create_course():
    """Create new course (admin only)"""
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({'error': 'Course name required'}), 400

    course = Course(
        name=data['name'],
        description=data.get('description'),
        teacher=data.get('teacher', 'Ahmed Labib'),
        subject=data.get('subject'),
        difficulty=data.get('difficulty'),
        duration_weeks=data.get('duration_weeks')
    )

    db.session.add(course)
    db.session.commit()

    return jsonify({
        'message': 'Course created successfully',
        'course': course.to_dict()
    }), 201

# ==================== QUIZ ROUTES ====================

@quiz_bp.route('/<int:quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    """Get quiz details"""
    quiz = Quiz.query.get(quiz_id)

    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404

    return jsonify(quiz.to_dict(include_questions=True)), 200

@quiz_bp.route('/<int:quiz_id>/start', methods=['POST'])
@jwt_required()
def start_quiz(quiz_id):
    """Start a quiz attempt"""
    user_id = get_jwt_identity()
    quiz = Quiz.query.get(quiz_id)

    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404

    # Create new attempt
    attempt = QuizAttempt(
        user_id=user_id,
        quiz_id=quiz_id,
        status='in_progress'
    )

    db.session.add(attempt)
    db.session.commit()

    return jsonify({
        'message': 'Quiz started',
        'attempt_id': attempt.id,
        'quiz': quiz.to_dict(include_questions=True)
    }), 200

@quiz_bp.route('/<int:quiz_id>/submit', methods=['POST'])
@jwt_required()
def submit_quiz(quiz_id):
    """Submit quiz answers and calculate score"""
    user_id = get_jwt_identity()
    data = request.get_json()

    attempt_id = data.get('attempt_id')
    answers = data.get('answers', {})  # {question_id: answer}

    attempt = QuizAttempt.query.get(attempt_id)
    quiz = Quiz.query.get(quiz_id)

    if not attempt or attempt.user_id != user_id:
        return jsonify({'error': 'Quiz attempt not found'}), 404

    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404

    # Calculate score
    score = 0
    max_score = 0
    correct_answers = {}

    for question in quiz.questions:
        max_score += question.points

        if str(question.id) in answers:
            user_answer = answers[str(question.id)]
            correct_answers[str(question.id)] = {
                'user_answer': user_answer,
                'correct_answer': question.correct_answer,
                'is_correct': user_answer.lower() == question.correct_answer.lower()
            }

            if user_answer.lower() == question.correct_answer.lower():
                score += question.points

    # Update attempt
    percentage = (score / max_score * 100) if max_score > 0 else 0
    attempt.score = score
    attempt.max_score = max_score
    attempt.percentage = percentage
    attempt.passed = percentage >= quiz.passing_score
    attempt.answers = answers
    attempt.completed_at = datetime.utcnow()
    attempt.status = 'completed'

    db.session.commit()

    # Update student progress
    chapter = quiz.chapter
    progress = StudentProgress.query.filter_by(
        user_id=user_id,
        chapter_id=chapter.id
    ).first()

    if not progress:
        progress = StudentProgress(
            user_id=user_id,
            chapter_id=chapter.id,
            course_id=chapter.course_id
        )
        db.session.add(progress)

    if attempt.passed:
        progress.quizzes_passed += 1
    progress.quizzes_total += 1
    progress.average_score = (
        (progress.average_score * (progress.quizzes_total - 1) + attempt.percentage) /
        progress.quizzes_total
    ) if progress.quizzes_total > 0 else attempt.percentage

    db.session.commit()

    return jsonify({
        'message': 'Quiz submitted successfully',
        'score': score,
        'max_score': max_score,
        'percentage': percentage,
        'passed': attempt.passed,
        'answers_review': correct_answers
    }), 200

@quiz_bp.route('/attempts/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_attempts(user_id):
    """Get all quiz attempts for a user"""
    current_user_id = get_jwt_identity()

    # Users can only see their own attempts
    if current_user_id != user_id:
        user = User.query.get(current_user_id)
        if user.role != 'admin':
            return jsonify({'error': 'Access denied'}), 403

    attempts = QuizAttempt.query.filter_by(user_id=user_id).all()

    return jsonify({
        'user_id': user_id,
        'total_attempts': len(attempts),
        'attempts': [att.to_dict() for att in attempts]
    }), 200

# ==================== PROGRESS ROUTES ====================

@progress_bp.route('/student/<int:user_id>', methods=['GET'])
@jwt_required()
def get_student_progress(user_id):
    """Get student's overall progress"""
    current_user_id = get_jwt_identity()

    # Users can only see their own progress
    if current_user_id != user_id:
        user = User.query.get(current_user_id)
        if user.role != 'admin':
            return jsonify({'error': 'Access denied'}), 403

    progress = StudentProgress.query.filter_by(user_id=user_id).all()

    return jsonify({
        'user_id': user_id,
        'total_progress_entries': len(progress),
        'progress': [p.to_dict() for p in progress]
    }), 200

@progress_bp.route('/course/<int:course_id>/students', methods=['GET'])
@admin_required
def get_course_student_progress(course_id):
    """Get progress of all students in a course (admin only)"""
    course = Course.query.get(course_id)

    if not course:
        return jsonify({'error': 'Course not found'}), 404

    progress = StudentProgress.query.filter_by(course_id=course_id).all()

    return jsonify({
        'course_id': course_id,
        'total_students': len(set(p.user_id for p in progress)),
        'progress': [p.to_dict() for p in progress]
    }), 200

# ==================== STUDY NOTES ROUTES ====================

@user_bp.route('/notes', methods=['GET'])
@jwt_required()
def get_user_notes():
    """Get all study notes for current user"""
    user_id = get_jwt_identity()
    notes = StudyNote.query.filter_by(user_id=user_id).all()

    return jsonify({
        'total_notes': len(notes),
        'notes': [note.to_dict() for note in notes]
    }), 200

@user_bp.route('/notes', methods=['POST'])
@jwt_required()
def create_note():
    """Create a new study note"""
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or not data.get('content'):
        return jsonify({'error': 'Note content required'}), 400

    note = StudyNote(
        user_id=user_id,
        chapter_id=data.get('chapter_id'),
        title=data.get('title'),
        content=data['content'],
        is_bookmark=data.get('is_bookmark', False)
    )

    db.session.add(note)
    db.session.commit()

    return jsonify({
        'message': 'Note created successfully',
        'note': note.to_dict()
    }), 201

@user_bp.route('/notes/<int:note_id>', methods=['PUT'])
@jwt_required()
def update_note(note_id):
    """Update a study note"""
    user_id = get_jwt_identity()
    note = StudyNote.query.get(note_id)

    if not note or note.user_id != user_id:
        return jsonify({'error': 'Note not found'}), 404

    data = request.get_json()

    if 'title' in data:
        note.title = data['title']
    if 'content' in data:
        note.content = data['content']
    if 'is_bookmark' in data:
        note.is_bookmark = data['is_bookmark']

    note.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': 'Note updated successfully',
        'note': note.to_dict()
    }), 200

@user_bp.route('/notes/<int:note_id>', methods=['DELETE'])
@jwt_required()
def delete_note(note_id):
    """Delete a study note"""
    user_id = get_jwt_identity()
    note = StudyNote.query.get(note_id)

    if not note or note.user_id != user_id:
        return jsonify({'error': 'Note not found'}), 404

    db.session.delete(note)
    db.session.commit()

    return jsonify({'message': 'Note deleted successfully'}), 200

# ==================== USER PROFILE ROUTES ====================

@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user.to_dict()), 200

@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if 'full_name' in data:
        user.full_name = data['full_name']
    if 'grade_level' in data:
        user.grade_level = data['grade_level']
    if 'school' in data:
        user.school = data['school']

    user.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': 'Profile updated successfully',
        'user': user.to_dict()
    }), 200

# ==================== ADMIN ROUTES ====================

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users (admin only)"""
    users = User.query.all()

    return jsonify({
        'total_users': len(users),
        'users': [user.to_dict() for user in users]
    }), 200

@admin_bp.route('/statistics', methods=['GET'])
@admin_required
def get_statistics():
    """Get platform statistics (admin only)"""
    total_users = User.query.count()
    total_students = User.query.filter_by(role='student').count()
    total_courses = Course.query.count()
    total_quizzes = Quiz.query.count()
    total_attempts = QuizAttempt.query.count()

    return jsonify({
        'total_users': total_users,
        'total_students': total_students,
        'total_courses': total_courses,
        'total_quizzes': total_quizzes,
        'total_quiz_attempts': total_attempts,
        'timestamp': datetime.utcnow().isoformat()
    }), 200
