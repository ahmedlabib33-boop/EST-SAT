"""Course content seed data.

Local use:
    python -m backend.seed          # create tables and add courses/chapters/quiz
    python -m backend.seed --demo   # also add demo accounts (local SQLite only)
"""

import sys

from .extensions import db
from .models import Chapter, Course, Question, Quiz, User

COURSES = [
    {
        'name': 'Mathematics SAT 1 & EST 1',
        'description': 'Complete mathematics curriculum covering algebra, trigonometry, logarithms, calculus and geometry',
        'subject': 'Mathematics',
        'chapters': [
            ('Algebra & Polynomials', 'Quadratic equations, factorization, systems and inequalities',
             'Topics:\n1. Quadratic Equations\n2. Factorization Methods\n3. Systems of Equations\n4. Inequalities'),
            ('Trigonometry', 'Trigonometric ratios, identities and equations',
             'Topics:\n1. Trigonometric Ratios\n2. Special Angles\n3. Trigonometric Identities\n4. Trigonometric Equations'),
            ('Logarithms & Exponentials', 'Logarithmic and exponential functions and equations',
             'Topics:\n1. Logarithmic Properties\n2. Exponential Equations\n3. Growth and Decay\n4. Change of Base'),
            ('Calculus Basics', 'Limits, derivatives and basic integration',
             'Topics:\n1. Limits\n2. Derivatives\n3. Differentiation Rules\n4. Integration Basics'),
            ('Geometry & Vectors', 'Conic sections, vectors and the dot product',
             'Topics:\n1. Conic Sections\n2. Vector Operations\n3. Dot and Cross Products'),
        ],
    },
    {
        'name': 'Physics SAT 1 & EST 1',
        'description': 'Complete physics curriculum covering mechanics, energy, waves, electricity, magnetism and modern physics',
        'subject': 'Physics',
        'chapters': [
            ('Mechanics & Motion', 'Kinematics, forces, circular motion and gravitation',
             "Topics:\n1. Kinematics\n2. Newton's Laws\n3. Friction\n4. Circular Motion\n5. Gravitation"),
            ('Energy & Work', 'Work, energy and power',
             'Topics:\n1. Work\n2. Kinetic and Potential Energy\n3. Energy Conservation\n4. Power'),
            ('Waves & Oscillations', 'Simple harmonic motion, waves and sound',
             'Topics:\n1. Simple Harmonic Motion\n2. Wave Properties\n3. Sound Waves\n4. Doppler Effect\n5. Light Waves'),
            ('Electricity & Current', 'Electric charge, current and circuits',
             "Topics:\n1. Coulomb's Law\n2. Electric Field\n3. Current and Resistance\n4. Circuits"),
            ('Magnetism & Electromagnetism', 'Magnetic fields and electromagnetic induction',
             "Topics:\n1. Magnetic Force\n2. Electromagnetic Induction\n3. Faraday's Law\n4. Transformers"),
            ('Modern Physics', 'Quantum theory, atomic structure, nuclear physics and relativity',
             'Topics:\n1. Photons\n2. Atomic Structure\n3. Nuclear Physics\n4. Relativity'),
        ],
    },
]

ALGEBRA_QUIZ = {
    'title': 'Algebra Quiz 1',
    'description': 'Quadratic equations and factorization',
    'time_limit_minutes': 15,
    'passing_score': 70.0,
    'questions': [
        ('Solve: x² − 5x + 6 = 0', {'a': 'x = 2 or x = 3', 'b': 'x = 1 or x = 6', 'c': 'x = −2 or x = −3', 'd': 'x = 2 or x = −3'},
         'a', 'Factor: (x − 2)(x − 3) = 0, so x = 2 or x = 3.', 'Easy', 1),
        ('Factor: 2x² − 8x', {'a': '2x(x − 4)', 'b': '2(x² − 4)', 'c': 'x(2x − 4)', 'd': '2x(x − 2)'},
         'a', 'Take out the common factor 2x: 2x(x − 4).', 'Easy', 1),
        ('What is the sum of the roots of x² − 7x + 12 = 0?', {'a': '7', 'b': '−7', 'c': '12', 'd': '−12'},
         'a', 'For ax² + bx + c = 0 the sum of the roots is −b/a = 7.', 'Medium', 2),
    ],
}


def seed_content():
    """Add the two courses, their chapters and a sample quiz. Does nothing if courses exist."""
    if Course.query.first():
        return False
    first_chapter = None
    for spec in COURSES:
        course = Course(name=spec['name'], description=spec['description'], teacher='Ahmed Labib',
                        subject=spec['subject'], difficulty='Intermediate', duration_weeks=12)
        db.session.add(course)
        for order, (name, description, content) in enumerate(spec['chapters'], start=1):
            chapter = Chapter(course=course, name=name, description=description, content=content, order=order)
            db.session.add(chapter)
            first_chapter = first_chapter or chapter
    quiz = Quiz(chapter=first_chapter, title=ALGEBRA_QUIZ['title'], description=ALGEBRA_QUIZ['description'],
                total_questions=len(ALGEBRA_QUIZ['questions']), time_limit_minutes=ALGEBRA_QUIZ['time_limit_minutes'],
                passing_score=ALGEBRA_QUIZ['passing_score'])
    db.session.add(quiz)
    for order, (text, options, answer, explanation, difficulty, points) in enumerate(ALGEBRA_QUIZ['questions'], start=1):
        db.session.add(Question(quiz=quiz, question_text=text, question_type='multiple_choice', options=options,
                                correct_answer=answer, explanation=explanation, difficulty=difficulty,
                                points=points, order=order))
    db.session.commit()
    return True


def seed_demo_users():
    """Demo accounts with well-known passwords. Never run this against the production database."""
    if not db.engine.url.drivername.startswith('sqlite'):
        raise SystemExit('Refusing to create demo accounts outside local SQLite.')
    demo = [('admin', 'admin@example.com', 'Administrator', 'admin', 'admin123'),
            ('ahmed_labib', 'teacher@example.com', 'Ahmed Labib', 'teacher', 'teacher123')]
    demo += [(f'student{i}', f'student{i}@example.com', f'Student {i}', 'student', 'student123') for i in range(1, 6)]
    for username, email, name, role, password in demo:
        if User.query.filter_by(username=username).first():
            continue
        user = User(username=username, email=email, full_name=name, role=role)
        user.set_password(password)
        db.session.add(user)
    db.session.commit()


if __name__ == '__main__':
    from . import create_app

    app = create_app()
    with app.app_context():
        db.create_all()
        print('Content added.' if seed_content() else 'Content already present.')
        if '--demo' in sys.argv:
            seed_demo_users()
            print('Demo accounts: admin/admin123, ahmed_labib/teacher123, student1-5/student123')
