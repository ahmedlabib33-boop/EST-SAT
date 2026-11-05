# SAT 1 & EST 1 Study Platform - API Documentation

**Teacher:** Ahmed Labib  
**Version:** 1.0.0  
**Base URL:** `http://localhost:5000/api`

---

## Table of Contents
1. [Authentication](#authentication)
2. [Courses](#courses)
3. [Quizzes](#quizzes)
4. [Progress](#progress)
5. [User Profile](#user-profile)
6. [Study Notes](#study-notes)
7. [Admin](#admin)
8. [Error Handling](#error-handling)

---

## Authentication

### Register User
**POST** `/auth/register`

Register a new student account.

**Request Body:**
```json
{
  "username": "student123",
  "email": "student@example.com",
  "password": "securepassword",
  "full_name": "Ahmed Student",
  "grade_level": "Grade 12",
  "school": "Cairo High School"
}
```

**Response (201):**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "student123",
    "email": "student@example.com",
    "full_name": "Ahmed Student",
    "role": "student",
    "grade_level": "Grade 12",
    "school": "Cairo High School",
    "created_at": "2024-01-01T12:00:00"
  }
}
```

---

### Login
**POST** `/auth/login`

Login and receive JWT token.

**Request Body:**
```json
{
  "username": "student123",
  "password": "securepassword"
}
```

**Response (200):**
```json
{
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "student123",
    "email": "student@example.com",
    "full_name": "Ahmed Student",
    "role": "student"
  }
}
```

---

### Refresh Token
**POST** `/auth/refresh`

Get a new JWT token (requires valid token).

**Headers:** `Authorization: Bearer {token}`

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## Courses

### Get All Courses
**GET** `/courses`

Retrieve all available courses.

**Response (200):**
```json
{
  "total": 2,
  "courses": [
    {
      "id": 1,
      "name": "Mathematics SAT 1 & EST 1",
      "description": "Complete mathematics curriculum",
      "teacher": "Ahmed Labib",
      "subject": "Mathematics",
      "difficulty": "Intermediate",
      "duration_weeks": 12,
      "is_active": true,
      "chapters": [...]
    }
  ]
}
```

---

### Get Specific Course
**GET** `/courses/{course_id}`

Retrieve a specific course with all chapters.

**Response (200):**
```json
{
  "id": 1,
  "name": "Mathematics SAT 1 & EST 1",
  "description": "Complete mathematics curriculum",
  "teacher": "Ahmed Labib",
  "subject": "Mathematics",
  "difficulty": "Intermediate",
  "duration_weeks": 12,
  "chapters": [
    {
      "id": 1,
      "name": "Algebra & Polynomials",
      "description": "Equations and factorization",
      "order": 1
    }
  ]
}
```

---

### Get Course Chapters
**GET** `/courses/{course_id}/chapters`

Retrieve all chapters in a course.

**Response (200):**
```json
{
  "course": {...},
  "chapters": [
    {
      "id": 1,
      "course_id": 1,
      "name": "Algebra & Polynomials",
      "description": "Equations and factorization",
      "order": 1,
      "quizzes": [...]
    }
  ]
}
```

---

### Create Course (Admin)
**POST** `/courses`

Create a new course.

**Headers:** `Authorization: Bearer {admin_token}`

**Request Body:**
```json
{
  "name": "New Course",
  "description": "Course description",
  "teacher": "Ahmed Labib",
  "subject": "Mathematics",
  "difficulty": "Intermediate",
  "duration_weeks": 12
}
```

**Response (201):**
```json
{
  "message": "Course created successfully",
  "course": {...}
}
```

---

## Quizzes

### Get Quiz
**GET** `/quizzes/{quiz_id}`

Retrieve a specific quiz with all questions (hidden correct answers).

**Response (200):**
```json
{
  "id": 1,
  "chapter_id": 1,
  "title": "Algebra Quiz 1",
  "description": "Test your algebra skills",
  "total_questions": 10,
  "time_limit_minutes": 30,
  "passing_score": 70,
  "questions": [
    {
      "id": 1,
      "question_text": "Solve: x² + 5x + 6 = 0",
      "question_type": "multiple_choice",
      "options": {
        "a": "x = 2 or x = 3",
        "b": "x = -2 or x = -3",
        "c": "x = 1 or x = 6",
        "d": "x = -1 or x = -6"
      },
      "difficulty": "Easy",
      "points": 1
    }
  ]
}
```

---

### Start Quiz
**POST** `/quizzes/{quiz_id}/start`

Start a quiz attempt.

**Headers:** `Authorization: Bearer {token}`

**Response (200):**
```json
{
  "message": "Quiz started",
  "attempt_id": 1,
  "quiz": {...}
}
```

---

### Submit Quiz
**POST** `/quizzes/{quiz_id}/submit`

Submit quiz answers and get score.

**Headers:** `Authorization: Bearer {token}`

**Request Body:**
```json
{
  "attempt_id": 1,
  "answers": {
    "1": "b",
    "2": "c",
    "3": "a"
  }
}
```

**Response (200):**
```json
{
  "message": "Quiz submitted successfully",
  "score": 8,
  "max_score": 10,
  "percentage": 80,
  "passed": true,
  "answers_review": {
    "1": {
      "user_answer": "b",
      "correct_answer": "b",
      "is_correct": true
    }
  }
}
```

---

### Get User Quiz Attempts
**GET** `/quizzes/attempts/{user_id}`

Get all quiz attempts for a user.

**Headers:** `Authorization: Bearer {token}`

**Response (200):**
```json
{
  "user_id": 1,
  "total_attempts": 5,
  "attempts": [
    {
      "id": 1,
      "quiz_id": 1,
      "score": 8,
      "max_score": 10,
      "percentage": 80,
      "passed": true,
      "started_at": "2024-01-01T12:00:00",
      "completed_at": "2024-01-01T12:30:00",
      "status": "completed"
    }
  ]
}
```

---

## Progress

### Get Student Progress
**GET** `/progress/student/{user_id}`

Get overall progress for a student.

**Headers:** `Authorization: Bearer {token}`

**Response (200):**
```json
{
  "user_id": 1,
  "total_progress_entries": 3,
  "progress": [
    {
      "id": 1,
      "course_id": 1,
      "chapter_id": 1,
      "status": "in_progress",
      "completion_percentage": 75,
      "quizzes_passed": 3,
      "quizzes_total": 4,
      "average_score": 82.5,
      "last_accessed": "2024-01-05T14:30:00"
    }
  ]
}
```

---

### Get Course Student Progress (Admin)
**GET** `/progress/course/{course_id}/students`

Get progress of all students in a course.

**Headers:** `Authorization: Bearer {admin_token}`

**Response (200):**
```json
{
  "course_id": 1,
  "total_students": 15,
  "progress": [...]
}
```

---

## User Profile

### Get Current User Profile
**GET** `/user/profile`

Get authenticated user's profile.

**Headers:** `Authorization: Bearer {token}`

**Response (200):**
```json
{
  "id": 1,
  "username": "student123",
  "email": "student@example.com",
  "full_name": "Ahmed Student",
  "role": "student",
  "grade_level": "Grade 12",
  "school": "Cairo High School",
  "created_at": "2024-01-01T12:00:00",
  "is_active": true
}
```

---

### Update User Profile
**PUT** `/user/profile`

Update user profile information.

**Headers:** `Authorization: Bearer {token}`

**Request Body:**
```json
{
  "full_name": "Ahmed Student Updated",
  "grade_level": "Grade 12 A",
  "school": "New High School"
}
```

**Response (200):**
```json
{
  "message": "Profile updated successfully",
  "user": {...}
}
```

---

## Study Notes

### Get All Study Notes
**GET** `/user/notes`

Get all study notes for current user.

**Headers:** `Authorization: Bearer {token}`

**Response (200):**
```json
{
  "total_notes": 5,
  "notes": [
    {
      "id": 1,
      "chapter_id": 1,
      "title": "Important formulas",
      "content": "sin²θ + cos²θ = 1",
      "is_bookmark": false,
      "created_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-02T10:00:00"
    }
  ]
}
```

---

### Create Study Note
**POST** `/user/notes`

Create a new study note.

**Headers:** `Authorization: Bearer {token}`

**Request Body:**
```json
{
  "chapter_id": 1,
  "title": "Important formulas",
  "content": "sin²θ + cos²θ = 1\ntan θ = sin θ / cos θ",
  "is_bookmark": false
}
```

**Response (201):**
```json
{
  "message": "Note created successfully",
  "note": {...}
}
```

---

### Update Study Note
**PUT** `/user/notes/{note_id}`

Update a study note.

**Headers:** `Authorization: Bearer {token}`

**Request Body:**
```json
{
  "title": "Updated title",
  "content": "Updated content",
  "is_bookmark": true
}
```

**Response (200):**
```json
{
  "message": "Note updated successfully",
  "note": {...}
}
```

---

### Delete Study Note
**DELETE** `/user/notes/{note_id}`

Delete a study note.

**Headers:** `Authorization: Bearer {token}`

**Response (200):**
```json
{
  "message": "Note deleted successfully"
}
```

---

## Admin

### Get All Users
**GET** `/admin/users`

Get all users on the platform.

**Headers:** `Authorization: Bearer {admin_token}`

**Response (200):**
```json
{
  "total_users": 50,
  "users": [...]
}
```

---

### Get Platform Statistics
**GET** `/admin/statistics`

Get overall platform statistics.

**Headers:** `Authorization: Bearer {admin_token}`

**Response (200):**
```json
{
  "total_users": 50,
  "total_students": 45,
  "total_courses": 2,
  "total_quizzes": 24,
  "total_quiz_attempts": 320,
  "timestamp": "2024-01-05T15:30:00"
}
```

---

## Error Handling

### Error Response Format
```json
{
  "error": "Error message here"
}
```

### Common Status Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 500 | Internal Server Error |

---

## Authentication Headers

All protected endpoints require:
```
Authorization: Bearer {access_token}
```

---

## Rate Limiting

Current implementation has no rate limiting. For production:
- Consider implementing Flask-Limiter
- Set appropriate limits per endpoint
- Add X-RateLimit-* headers to responses

---

## Example: Complete Student Journey

**1. Register**
```bash
POST /auth/register
{
  "username": "student1",
  "password": "pass123",
  "email": "student1@example.com",
  "full_name": "Student One"
}
```

**2. Login**
```bash
POST /auth/login
{
  "username": "student1",
  "password": "pass123"
}
```

**3. Get Courses**
```bash
GET /courses
Authorization: Bearer {token}
```

**4. Get Course Chapters**
```bash
GET /courses/1/chapters
Authorization: Bearer {token}
```

**5. Start Quiz**
```bash
POST /quizzes/1/start
Authorization: Bearer {token}
```

**6. Submit Quiz**
```bash
POST /quizzes/1/submit
Authorization: Bearer {token}
{
  "attempt_id": 1,
  "answers": {"1": "b", "2": "c"}
}
```

**7. Check Progress**
```bash
GET /progress/student/1
Authorization: Bearer {token}
```

---

## Practice and AI

Questions never include their answers until they are graded. Subjects are math, english and physics.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/practice/subjects` | Public | Counts per subject |
| GET | `/api/practice/<subject>/topics` | Public | Topics and lessons, no questions |
| GET | `/api/practice/<subject>/lessons/<id>` | Public | A lesson and its questions, without answers |
| GET | `/api/practice/<subject>/revision` | Public | Every lesson's rule, formula, example and tip |
| GET | `/api/practice/random?subject=&n=&topics=&difficulty=` | Public | Up to 100 random questions, without answers. `difficulty` is an order of preference, so `hard,medium` fills with hard first |
| GET | `/api/practice/daily?day=&n=` | Public | Today's mission: the same questions for everyone, a new set each day |
| GET | `/api/practice/questions?ids=` | Public | Up to 60 questions by id, without answers |
| POST | `/api/practice/grade` | Public | `{items: [{id, answer}]}`, up to 100; returns the answer and explanation |
| GET | `/api/practice/review` | JWT | The account's own wrong answers, with explanations |
| GET | `/api/ai/status` | JWT | Whether AI is on, and the calls left today |
| POST | `/api/ai/coach` | JWT | `{question, image}`; returns `{reply}`. 429 when the daily allowance is used up |
| POST | `/api/ai/cards` | JWT | `{items}`, up to 8 mistakes; returns `{cards}` |

---

**Last Updated:** 2024-01-05  
**Maintained by:** Ahmed Labib
