"""
SAT 1 & EST 1 Study Platform - Main Flask Application
Teacher: Ahmed Labib
"""

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///estsat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

# Import models and routes
from models import User, Course, Chapter, Quiz, Question, QuizAttempt, StudentProgress, StudyNote
from routes import auth_bp, courses_bp, quiz_bp, progress_bp, admin_bp, user_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(courses_bp)
app.register_blueprint(quiz_bp)
app.register_blueprint(progress_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({'error': 'Unauthorized access'}), 401

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'SAT 1 & EST 1 Study Platform'
    }), 200

# Root endpoint
@app.route('/api', methods=['GET'])
def api_info():
    return jsonify({
        'name': 'SAT 1 & EST 1 Study Platform API',
        'version': '1.0.0',
        'teacher': 'Ahmed Labib',
        'description': 'Complete study platform for SAT 1 & EST 1 Mathematics and Physics',
        'endpoints': {
            'auth': '/api/auth',
            'courses': '/api/courses',
            'quizzes': '/api/quizzes',
            'progress': '/api/progress',
            'admin': '/api/admin',
            'user': '/api/user'
        }
    }), 200

# Database initialization
def init_db():
    """Initialize database with sample data"""
    with app.app_context():
        db.create_all()

        # Check if data already exists
        if Course.query.first():
            print("Database already initialized")
            return

        # Create sample courses
        math_course = Course(
            name='Mathematics SAT 1 & EST 1',
            description='Complete mathematics curriculum for SAT 1 & EST 1',
            teacher='Ahmed Labib',
            difficulty='Intermediate',
            duration_weeks=12
        )

        physics_course = Course(
            name='Physics SAT 1 & EST 1',
            description='Complete physics curriculum for SAT 1 & EST 1',
            teacher='Ahmed Labib',
            difficulty='Intermediate',
            duration_weeks=12
        )

        db.session.add(math_course)
        db.session.add(physics_course)
        db.session.commit()

        print("Database initialized with sample data")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
