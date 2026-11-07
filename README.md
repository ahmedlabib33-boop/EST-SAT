# SAT 1 & EST 1 Complete Study Platform

**Teacher:** Ahmed Labib  
**Version:** 2.0 (Full Stack)

---

## 🎯 Overview

A **comprehensive, production-grade educational platform** for SAT 1 & EST 1 preparation in **Mathematics and Physics**. Includes:
- ✅ Interactive web interface
- ✅ Powerful Python backend API
- ✅ Complete database system
- ✅ Quiz engine with auto-grading
- ✅ Student progress tracking
- ✅ Teacher dashboard
- ✅ Admin controls
- ✅ Study notes and bookmarks

---

## 📚 Contents

### 📐 Mathematics (SAT 1 & EST 1)
1. **Algebra & Polynomials** - Quadratic equations, factorization, systems
2. **Trigonometry** - Ratios, identities, special angles, functions
3. **Logarithms & Exponentials** - Properties, growth, decay, change of base
4. **Calculus Basics** - Limits, derivatives, integration, applications
5. **Geometry & Vectors** - Conic sections, vector operations, 3D geometry

### ⚛️ Physics (SAT 1 & EST 1)
1. **Mechanics & Motion** - Kinematics, Newton's Laws, friction, circular motion
2. **Energy & Work** - Kinetic/potential energy, conservation, power
3. **Waves & Oscillations** - SHM, wave properties, sound, light, Doppler effect
4. **Electricity & Current** - Charges, fields, current, circuits, Kirchhoff's Laws
5. **Magnetism & Electromagnetism** - Fields, induction, Faraday's Law, transformers
6. **Modern Physics** - Quantum theory, atomic structure, nuclear physics, relativity

---

## 🚀 Quick Start

### Option 1: Use Web Interface Only
```bash
1. Open index.html in browser
2. Navigate between Mathematics and Physics
3. Read materials, view formulas, review examples
4. Works offline - no installation needed
```

### Option 2: Full Stack (Recommended)
```bash
# 1. Clone repository
git clone https://github.com/ahmedlabib33-boop/EST-SAT.git
cd EST-SAT

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. (Optional) add local demo accounts to the SQLite database
python -m backend.seed --demo

# 5. Run the site and API together
python app.py

# 6. Open http://localhost:5000 (API at http://localhost:5000/api)

# Run the tests
python -m pytest tests
```

Production runs on Vercel: pages are served from `public/`, the API from `api/index.py`,
and data lives in the Supabase project `est-sat` (schema `estsat`). Vercel needs
`DATABASE_URL` and `JWT_SECRET_KEY` set as environment variables.

---

## 📋 Project Structure

```
EST-SAT/
├── public/                    # Website (served by Vercel)
│   ├── index.html             # Mission Control homepage + practice
│   ├── login.html             # Log in / create account
│   ├── student-portal.html    # Student portal + teacher view
│   └── assets/                # site.css, auth.js
├── api/index.py               # Vercel entry point for the API
├── backend/                   # Flask app: models, routes, seed data
├── app.py                     # Local runner (site + API on one port)
├── tests/                     # API tests (pytest)
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── README.md                  # This file
├── API_DOCUMENTATION.md       # Complete API docs
├── SETUP.md                   # Deployment guide
├── math-guide.md              # Math study guide
├── physics-guide.md           # Physics study guide
└── practice-problems.md       # 50+ problems with solutions
```

---

## 🎯 Key Features

### 📚 Frontend (HTML/CSS/JavaScript)
- ✅ Interactive responsive design
- ✅ Complete study materials
- ✅ Formula library
- ✅ Practice problems
- ✅ Offline support
- ✅ Mobile-friendly interface

### 🔧 Backend (Python/Flask)
- ✅ RESTful API (20+ endpoints)
- ✅ JWT authentication
- ✅ User management (students, teachers, admins)
- ✅ Role-based access control
- ✅ Quiz engine with auto-grading
- ✅ Student progress tracking
- ✅ Study notes and bookmarks
- ✅ Admin dashboard with statistics
- ✅ Database persistence
- ✅ Production-ready error handling

### 🗄️ Database
- ✅ SQLAlchemy ORM
- ✅ 8 database models
- ✅ SQLite (dev) / PostgreSQL (production)
- ✅ Data relationships and constraints
- ✅ Migration support

---

## 💻 API Endpoints

### 🔐 Authentication
```
POST   /api/auth/register       # Register new user
POST   /api/auth/login          # Login and get token
POST   /api/auth/refresh        # Refresh token
POST   /api/auth/logout         # Logout
```

### 📚 Courses
```
GET    /api/courses             # Get all courses
GET    /api/courses/{id}        # Get specific course
GET    /api/courses/{id}/chapters  # Get course chapters
POST   /api/courses             # Create course (admin)
```

### 📝 Quizzes
```
GET    /api/quizzes/{id}        # Get quiz details
POST   /api/quizzes/{id}/start  # Start quiz attempt
POST   /api/quizzes/{id}/submit # Submit answers
GET    /api/quizzes/attempts/{user_id}  # Get attempts
```

### 📊 Progress
```
GET    /api/progress/student/{user_id}  # Student progress
GET    /api/progress/course/{id}/students  # Course stats (admin)
```

### 📝 Study Notes
```
GET    /api/user/notes          # Get notes
POST   /api/user/notes          # Create note
PUT    /api/user/notes/{id}     # Update note
DELETE /api/user/notes/{id}     # Delete note
```

### 👤 User Profile
```
GET    /api/user/profile        # Get profile
PUT    /api/user/profile        # Update profile
```

### 🛡️ Admin
```
GET    /api/admin/users         # Get all users
GET    /api/admin/statistics    # Platform stats
```

---

## 📊 Database Models

1. **User** - Students, teachers, admins
2. **Course** - Mathematics, Physics
3. **Chapter** - Course sections
4. **Quiz** - Quiz per chapter
5. **Question** - Quiz questions
6. **QuizAttempt** - Student quiz submissions
7. **StudentProgress** - Completion tracking
8. **StudyNote** - Student notes/bookmarks

---

## 👥 User Roles

| Role | Permissions |
|------|------------|
| **Student** | Take quizzes, track progress, write notes |
| **Teacher** | Create courses, manage content, view progress |
| **Admin** | Full platform control, user management, statistics |

---

## 🧪 Testing

### Sample Credentials (local only, after `python -m backend.seed --demo`)
```
Admin:    admin / admin123
Teacher:  ahmed_labib / teacher123
Student:  student1 / student123
```
These demo accounts are refused outside local SQLite and never exist in production.

### Test API
```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123","email":"test@example.com"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'

# Get Courses
curl -X GET http://localhost:5000/api/courses
```

---

## 📚 Study Materials

### Included Documents
- **math-guide.md** - 6KB comprehensive mathematics study guide
- **physics-guide.md** - 9KB comprehensive physics study guide
- **practice-problems.md** - 50+ solved practice problems
- **API_DOCUMENTATION.md** - Complete API reference
- **SETUP.md** - Deployment and setup guide

---

## 🚀 Deployment

### Supported Platforms
- ✅ Heroku
- ✅ AWS (EC2 + RDS)
- ✅ Docker
- ✅ DigitalOcean
- ✅ Any server with Python 3.8+

### Quick Deployment
```bash
# Heroku
heroku create your-app
git push heroku main

# Docker
docker-compose up -d

# AWS
# Follow SETUP.md for detailed instructions
```

---

## 🔒 Security Features

- ✅ JWT authentication
- ✅ Password hashing (werkzeug)
- ✅ CORS enabled
- ✅ Input validation
- ✅ Error handling
- ✅ Role-based access control
- ✅ Secure environment variables

---

## 📈 Performance

- ✅ Database indexing
- ✅ Efficient queries
- ✅ Response caching (ready for Flask-Caching)
- ✅ Connection pooling
- ✅ Optimized for 1000+ concurrent users

---

## 🛠️ Technology Stack

### Frontend
- HTML5
- CSS3
- JavaScript (Vanilla)

### Backend
- Python 3.11
- Flask 3.0
- SQLAlchemy 2.0
- Flask-JWT-Extended 4.5
- PostgreSQL / SQLite

### DevOps
- Docker
- Docker Compose
- Gunicorn
- Nginx

---

## 📝 Documentation

1. **README.md** - This file
2. **API_DOCUMENTATION.md** - Complete API guide with examples
3. **SETUP.md** - Installation, deployment, troubleshooting
4. **math-guide.md** - Mathematics curriculum
5. **physics-guide.md** - Physics curriculum
6. **practice-problems.md** - Practice problems with solutions

---

## 🎓 Study Features

### For Students
- ✅ Interactive course content
- ✅ Self-paced learning
- ✅ Quiz system with instant feedback
- ✅ Progress tracking
- ✅ Study notes and bookmarks
- ✅ Performance analytics
- ✅ Practice problems with solutions

### For Teachers
- ✅ Course creation and management
- ✅ Content organization
- ✅ Quiz creation with auto-grading
- ✅ Student performance tracking
- ✅ Progress analytics
- ✅ Classroom management

### For Admins
- ✅ User management
- ✅ Platform statistics
- ✅ Course administration
- ✅ System monitoring
- ✅ Data management

---

## 📚 The question bank

Lessons and practice questions live as JSON under `backend/content/`, one file per subject.
Answers never leave the server: `/api/practice/grade` is the only way to learn whether a choice
was right.

| Subject | Topics | Lessons | Questions |
|---|---|---|---|
| Math | 5 | 155 | 368 |
| English | 12 | 157 | 344 |
| Physics | 6 | 47 | 114 |

Each lesson has a question on its rule, a second that applies it a step further, and many
have a third marked `Hard`. The Exam Arena's **Challenge** paper draws on those first and
gives 75 seconds a question instead of 90.

Every practice question is written by hand in `scripts/items_math.py`, `scripts/items_english.py`
and `scripts/items_physics.py`. To change or add one, edit those files and run:

```bash
python scripts/import_content.py   # only to re-import Math and English from the source workbook
python scripts/build_practice.py   # writes the question banks and checks them
```

The builder refuses to write a question with a repeated choice, a missing explanation or an
unknown lesson, and `tests/test_practice.py` checks the shipped bank for the generated
placeholders it replaced.

---

## 🧭 Study Tools

Every tool shares one progress object. It is saved in the browser and synced to the account by `PUT /api/user/state`, which accepts only known, bounded fields (`clean_state` in `backend/routes.py`). The logic lives in `public/assets/study.js` and is unit-tested by `npm test`.

| Page | What it does |
|---|---|
| `today.html` | A 15-minute session: due reviews first, then fresh questions from the weakest topics. Streak, weekly challenge, readiness estimate. |
| `exam.html` | Timed exams: a quick paper (Standard or Challenge), or a full mock sat in timed sections with a break between them. Warnings at 15 and 5 minutes, automatic collection, resumes after a reload, and a review of where the time went. |
| `review.html` | Spaced review of wrong answers after 1, 3, 7 and 14 days, as a list or flashcards. |
| `progress.html` | Exam score chart, readiness estimate and accuracy by topic. The estimate is not an official SAT or EST score. |
| `rewards.html` | XP, levels, badges, a topic map and printable certificates. |
| `revision.html` | Every rule and formula, searchable and printable, a page of cards at a time. |
| `coach.html` | AI coach: type, speak in English or Arabic, or send a photo. |
| `pad.html` | Drawing pad, saved per account on the device. |
| `focus.html` | Focus timer that counts towards study time, with a YouTube, Spotify or SoundCloud link. |
| `parent.html` | Progress summary, assignments, and goals that unlock a message. Voice notes stay on the device that recorded them. |

The site also installs as a phone app (`manifest.webmanifest`, `sw.js`), with a tab bar on small screens.

**AI setup:** set `GROQ_API_KEY` in Vercel to switch on the coach and AI flashcards. Until then the coach page says it is not switched on and everything else keeps working. Each student gets `AI_DAILY_LIMIT` calls in any 24 hours (default 150); teachers and admins are not counted.

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | `lsof -i :5000` and kill process |
| DB connection error | Check DATABASE_URL in .env |
| Import errors | Run `pip install -r requirements.txt` |
| CORS issues | Already configured, check frontend URL |
| JWT token errors | Generate new secret with `python -c "import secrets; print(secrets.token_hex(32))"` |

---

## 📊 Statistics

- **50+** Practice problems with solutions
- **20+** API endpoints
- **8** Database models
- **6** Physics chapters
- **5** Mathematics chapters
- **2000+** Lines of Python code
- **1500+** Lines of documentation

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

## 📝 License

Free Educational Material - Use for learning purposes

---

## 👨‍🏫 Teacher

**Ahmed Labib**
- Specialized in SAT 1 & EST 1 preparation
- Expert in Mathematics and Physics
- Committed to student success

---

## 🔗 Links

- **API Docs:** See `API_DOCUMENTATION.md`
- **Setup Guide:** See `SETUP.md`
- **Math Guide:** See `math-guide.md`
- **Physics Guide:** See `physics-guide.md`
- **Practice Problems:** See `practice-problems.md`

---

## 📞 Support

For issues or questions:
1. Check the documentation
2. Review API_DOCUMENTATION.md
3. Check SETUP.md for troubleshooting
4. Contact: Ahmed Labib

---

**Last Updated:** 2024-01-05  
**Version:** 2.0 (Full Stack)  
**Status:** ✅ Production Ready
