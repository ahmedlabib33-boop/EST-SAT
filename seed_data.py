"""
Seed Sample Data for Development
Teacher: Ahmed Labib
"""

from app import app, db
from models import User, Course, Chapter, Quiz, Question

def seed_database():
    """Add sample data to database"""
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()

        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            full_name='Administrator',
            role='admin'
        )
        admin.set_password('admin123')

        # Create teacher account
        teacher = User(
            username='ahmed_labib',
            email='ahmed.labib@estsat.com',
            full_name='Ahmed Labib',
            role='teacher'
        )
        teacher.set_password('teacher123')

        # Create student accounts
        students = []
        for i in range(1, 6):
            student = User(
                username=f'student{i}',
                email=f'student{i}@example.com',
                full_name=f'Student {i}',
                grade_level='Grade 12',
                school=f'School {i}',
                role='student'
            )
            student.set_password('student123')
            students.append(student)

        db.session.add(admin)
        db.session.add(teacher)
        for student in students:
            db.session.add(student)

        # Create Mathematics Course
        math_course = Course(
            name='Mathematics SAT 1 & EST 1',
            description='Complete mathematics curriculum covering algebra, trigonometry, calculus, and geometry',
            teacher='Ahmed Labib',
            subject='Mathematics',
            difficulty='Intermediate',
            duration_weeks=12
        )

        # Create Physics Course
        physics_course = Course(
            name='Physics SAT 1 & EST 1',
            description='Complete physics curriculum covering mechanics, energy, waves, electricity, and modern physics',
            teacher='Ahmed Labib',
            subject='Physics',
            difficulty='Intermediate',
            duration_weeks=12
        )

        db.session.add(math_course)
        db.session.add(physics_course)
        db.session.commit()

        # Create Math Chapters
        math_chapters = [
            {
                'name': 'Algebra & Polynomials',
                'description': 'Quadratic equations, factorization, and polynomial operations',
                'content': 'Chapter 1: Algebra\n\nTopics:\n1. Quadratic Equations\n2. Factorization Methods\n3. Systems of Equations\n4. Inequalities',
                'order': 1
            },
            {
                'name': 'Trigonometry',
                'description': 'Trigonometric ratios, identities, and equations',
                'content': 'Chapter 2: Trigonometry\n\nTopics:\n1. Trigonometric Ratios\n2. Special Angles\n3. Trigonometric Identities\n4. Trigonometric Equations',
                'order': 2
            },
            {
                'name': 'Logarithms & Exponentials',
                'description': 'Logarithmic and exponential functions and equations',
                'content': 'Chapter 3: Logarithms & Exponentials\n\nTopics:\n1. Logarithmic Properties\n2. Exponential Equations\n3. Growth and Decay\n4. Change of Base',
                'order': 3
            },
            {
                'name': 'Calculus Basics',
                'description': 'Limits, derivatives, and basic integration',
                'content': 'Chapter 4: Calculus\n\nTopics:\n1. Limits\n2. Derivatives\n3. Differentiation Rules\n4. Integration Basics',
                'order': 4
            },
            {
                'name': 'Geometry & Vectors',
                'description': 'Conic sections, vectors, and 3D geometry',
                'content': 'Chapter 5: Geometry & Vectors\n\nTopics:\n1. Conic Sections\n2. Vector Operations\n3. Dot and Cross Products\n4. 3D Geometry',
                'order': 5
            }
        ]

        math_chapter_objects = []
        for ch_data in math_chapters:
            chapter = Chapter(
                course_id=math_course.id,
                **ch_data
            )
            math_chapter_objects.append(chapter)
            db.session.add(chapter)

        db.session.commit()

        # Create Physics Chapters
        physics_chapters = [
            {
                'name': 'Mechanics & Motion',
                'description': 'Kinematics, forces, and circular motion',
                'content': 'Chapter 1: Mechanics\n\nTopics:\n1. Kinematics\n2. Newton\'s Laws\n3. Friction\n4. Circular Motion',
                'order': 1
            },
            {
                'name': 'Energy & Work',
                'description': 'Work, energy, and power concepts',
                'content': 'Chapter 2: Energy\n\nTopics:\n1. Work\n2. Kinetic and Potential Energy\n3. Energy Conservation\n4. Power',
                'order': 2
            },
            {
                'name': 'Waves & Oscillations',
                'description': 'Simple harmonic motion, waves, and sound',
                'content': 'Chapter 3: Waves\n\nTopics:\n1. Simple Harmonic Motion\n2. Wave Properties\n3. Sound Waves\n4. Light Waves',
                'order': 3
            },
            {
                'name': 'Electricity & Current',
                'description': 'Electric charge, current, and circuits',
                'content': 'Chapter 4: Electricity\n\nTopics:\n1. Electric Charge\n2. Electric Field\n3. Current and Resistance\n4. Electric Circuits',
                'order': 4
            },
            {
                'name': 'Magnetism & Electromagnetism',
                'description': 'Magnetic fields and electromagnetic induction',
                'content': 'Chapter 5: Magnetism\n\nTopics:\n1. Magnetic Fields\n2. Electromagnetic Induction\n3. Faraday\'s Law\n4. Transformers',
                'order': 5
            },
            {
                'name': 'Modern Physics',
                'description': 'Quantum theory, atomic structure, and nuclear physics',
                'content': 'Chapter 6: Modern Physics\n\nTopics:\n1. Quantum Theory\n2. Atomic Structure\n3. Nuclear Physics\n4. Relativity',
                'order': 6
            }
        ]

        physics_chapter_objects = []
        for ch_data in physics_chapters:
            chapter = Chapter(
                course_id=physics_course.id,
                **ch_data
            )
            physics_chapter_objects.append(chapter)
            db.session.add(chapter)

        db.session.commit()

        # Create sample quiz for first math chapter
        if math_chapter_objects:
            quiz = Quiz(
                chapter_id=math_chapter_objects[0].id,
                title='Algebra Quiz 1',
                description='Test your understanding of quadratic equations and factorization',
                total_questions=5,
                time_limit_minutes=30,
                passing_score=70.0
            )
            db.session.add(quiz)
            db.session.commit()

            # Add questions to quiz
            questions_data = [
                {
                    'question_text': 'Solve: x² - 5x + 6 = 0',
                    'question_type': 'multiple_choice',
                    'options': {
                        'a': 'x = 2 or x = 3',
                        'b': 'x = 1 or x = 6',
                        'c': 'x = -2 or x = -3',
                        'd': 'x = 2 or x = -3'
                    },
                    'correct_answer': 'a',
                    'explanation': 'Using factorization: (x-2)(x-3) = 0, so x = 2 or x = 3',
                    'difficulty': 'Easy',
                    'points': 1,
                    'order': 1
                },
                {
                    'question_text': 'Factor: 2x² - 8x',
                    'question_type': 'multiple_choice',
                    'options': {
                        'a': '2x(x - 4)',
                        'b': '2(x² - 4)',
                        'c': 'x(2x - 8)',
                        'd': '2x(x - 2)'
                    },
                    'correct_answer': 'a',
                    'explanation': 'Factor out the GCF: 2x(x - 4)',
                    'difficulty': 'Easy',
                    'points': 1,
                    'order': 2
                },
                {
                    'question_text': 'What is the sum of roots of x² - 7x + 12 = 0?',
                    'question_type': 'multiple_choice',
                    'options': {
                        'a': '7',
                        'b': '-7',
                        'c': '12',
                        'd': '-12'
                    },
                    'correct_answer': 'a',
                    'explanation': 'For equation ax² + bx + c = 0, sum of roots = -b/a = 7/1 = 7',
                    'difficulty': 'Medium',
                    'points': 2,
                    'order': 3
                }
            ]

            for q_data in questions_data:
                question = Question(quiz_id=quiz.id, **q_data)
                db.session.add(question)

            db.session.commit()

        print("✅ Database seeded successfully!")
        print("\n📊 Sample Data Created:")
        print("- 1 Admin (admin / admin123)")
        print("- 1 Teacher (ahmed_labib / teacher123)")
        print("- 5 Students (student1-5 / student123)")
        print("- 2 Courses (Mathematics & Physics)")
        print("- 11 Chapters total")
        print("- 1 Sample Quiz with 3 questions")
        print("\n🚀 Ready to test!")

if __name__ == '__main__':
    seed_database()
