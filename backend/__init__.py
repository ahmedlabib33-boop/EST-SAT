"""SAT 1 & EST 1 study platform API (Flask). Teacher: Ahmed Labib."""

import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from sqlalchemy import text
from werkzeug.exceptions import HTTPException

from .extensions import db, jwt
from .models import User, utcnow

load_dotenv()


def _database_url():
    url = os.getenv('DATABASE_URL') or 'sqlite:///estsat.db'
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return url


def _engine_options(url):
    if not url.startswith('postgresql'):
        return {}
    # Small client-side pool in front of Supabase's transaction pooler; pre-ping drops connections
    # that went stale while the serverless instance was idle.
    return {
        'pool_pre_ping': True,
        'pool_recycle': 280,
        'pool_size': 2,
        'max_overflow': 3,
        'connect_args': {'sslmode': 'require', 'connect_timeout': 10},
    }


def create_app(config=None):
    app = Flask(__name__)

    secret = os.getenv('JWT_SECRET_KEY')
    if not secret:
        if os.getenv('VERCEL'):
            raise RuntimeError('JWT_SECRET_KEY must be set in production.')
        secret = 'local-development-only-secret-key-change-me'

    url = _database_url()
    app.config.update(
        SQLALCHEMY_DATABASE_URI=url,
        SQLALCHEMY_ENGINE_OPTIONS=_engine_options(url),
        JWT_SECRET_KEY=secret,
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(days=14),
        MAX_CONTENT_LENGTH=256 * 1024,
    )
    if config:
        app.config.update(config)

    db.init_app(app)
    jwt.init_app(app)

    origins = [o.strip() for o in os.getenv('CORS_ORIGINS', '').split(',') if o.strip()]
    if origins:
        from flask_cors import CORS
        CORS(app, resources={r'/api/*': {'origins': origins}})

    _register_jwt_handlers()
    _register_error_handlers(app)

    from .ai import ai_bp
    from .live_routes import live_bp
    from .practice import practice_bp
    from .routes import blueprints
    for bp in blueprints + [live_bp, practice_bp, ai_bp]:
        app.register_blueprint(bp)

    @app.get('/api')
    def api_info():
        return jsonify({
            'name': 'SAT 1 & EST 1 Study Platform API',
            'version': '2.0.0',
            'teacher': 'Ahmed Labib',
            'endpoints': ['/api/health', '/api/auth', '/api/user', '/api/courses', '/api/quizzes',
                          '/api/practice', '/api/ai', '/api/progress', '/api/admin'],
        }), 200

    @app.get('/api/health')
    def health_check():
        try:
            db.session.execute(text('select 1'))
            database = 'ok'
        except Exception:
            db.session.rollback()
            app.logger.exception('Database health check failed')
            database = 'unavailable'
        healthy = database == 'ok'
        return jsonify({'status': 'healthy' if healthy else 'degraded', 'database': database,
                        'timestamp': utcnow().isoformat()}), 200 if healthy else 503

    @app.after_request
    def no_store(response):
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    if url.startswith('sqlite'):
        with app.app_context():
            db.create_all()
            from .seed import seed_content
            seed_content()

    return app


def _register_jwt_handlers():
    def session_ended(*_):
        return jsonify({'error': 'Your session has ended. Please log in again.'}), 401

    @jwt.user_lookup_loader
    def load_user(_header, payload):
        try:
            user = db.session.get(User, int(payload['sub']))
        except (KeyError, TypeError, ValueError):
            return None
        return user if user and user.is_active else None

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return jsonify({'error': 'Please log in first.'}), 401

    jwt.user_lookup_error_loader(session_ended)
    jwt.expired_token_loader(session_ended)
    jwt.invalid_token_loader(session_ended)
    jwt.revoked_token_loader(session_ended)


def _register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def http_error(e):
        messages = {404: 'Not found.', 405: 'Method not allowed.', 413: 'Request is too large.'}
        return jsonify({'error': messages.get(e.code, e.description)}), e.code

    @app.errorhandler(Exception)
    def server_error(e):
        db.session.rollback()
        app.logger.exception('Unhandled error')
        return jsonify({'error': 'Something went wrong on our side. Please try again.'}), 500
