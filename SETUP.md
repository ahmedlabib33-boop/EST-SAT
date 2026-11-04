# Setup and Deployment Guide

**SAT 1 & EST 1 Study Platform**  
**Teacher:** Ahmed Labib

---

## Table of Contents
1. [Local Development](#local-development)
2. [Production Deployment](#production-deployment)
3. [Database Setup](#database-setup)
4. [Environment Configuration](#environment-configuration)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- SQLite (included with Python) or PostgreSQL
- Git

### 1. Clone Repository
```bash
git clone https://github.com/ahmedlabib33-boop/EST-SAT.git
cd EST-SAT
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
```bash
# Copy the example file
cp .env.example .env

# Edit .env file with your settings
# For development, default SQLite is fine
# Generate a new JWT secret:
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Initialize Database
```bash
python
>>> from app import app, init_db
>>> init_db()
>>> exit()
```

### 6. Run Development Server
```bash
python app.py
```

Server runs on `http://localhost:5000`

### 7. Test API
```bash
# Register a user
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student1",
    "email": "student1@example.com",
    "password": "password123",
    "full_name": "Ahmed Student"
  }'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student1",
    "password": "password123"
  }'

# Get courses
curl -X GET http://localhost:5000/api/courses
```

---

## Production Deployment

### Option 1: Deploy on Heroku

**1. Install Heroku CLI**
```bash
# macOS
brew install heroku/brew/heroku

# Windows
# Download from https://devcenter.heroku.com/articles/heroku-cli
```

**2. Create Procfile**
```
web: gunicorn app:app
```

**3. Create runtime.txt**
```
python-3.11.0
```

**4. Login and Deploy**
```bash
heroku login
heroku create your-app-name
heroku config:set JWT_SECRET_KEY=your-secret-key
heroku config:set DATABASE_URL=postgresql://...
git push heroku main
```

### Option 2: Deploy on AWS

**1. Create EC2 Instance**
- Select Ubuntu 20.04 LTS
- t2.micro (free tier)
- Configure security group (allow ports 22, 80, 443)

**2. Connect and Setup**
```bash
ssh -i your-key.pem ubuntu@your-instance-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Clone repository
git clone https://github.com/ahmedlabib33-boop/EST-SAT.git
cd EST-SAT

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

**3. Setup Nginx Reverse Proxy**
```bash
sudo apt install nginx -y

# Create nginx config
sudo nano /etc/nginx/sites-available/estsat

# Add:
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/estsat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**4. Setup SSL with Let's Encrypt**
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

### Option 3: Deploy with Docker

**1. Create Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

**2. Create docker-compose.yml**
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/estsat
      JWT_SECRET_KEY: your-secret-key
    depends_on:
      - db
  
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: estsat
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

**3. Run with Docker**
```bash
docker-compose up -d
```

---

## Database Setup

### SQLite (Development)
- Automatic setup with `init_db()`
- File: `estsat.db`
- Good for testing and development

### PostgreSQL (Production)

**1. Install PostgreSQL**
```bash
# macOS
brew install postgresql

# Ubuntu
sudo apt install postgresql postgresql-contrib -y
```

**2. Create Database and User**
```bash
sudo -u postgres psql

CREATE DATABASE estsat;
CREATE USER estsat_user WITH PASSWORD 'strong_password';
ALTER ROLE estsat_user SET client_encoding TO 'utf8';
ALTER ROLE estsat_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE estsat_user SET default_transaction_deferrable TO on;
ALTER ROLE estsat_user SET default_transaction_read_committed TO on;
GRANT ALL PRIVILEGES ON DATABASE estsat TO estsat_user;
\q
```

**3. Update .env**
```
DATABASE_URL=postgresql://estsat_user:strong_password@localhost:5432/estsat
```

**4. Backup Database**
```bash
pg_dump -U estsat_user estsat > backup.sql

# Restore
psql -U estsat_user estsat < backup.sql
```

---

## Environment Configuration

### Required Variables
```bash
# Database
DATABASE_URL=sqlite:///estsat.db  # or PostgreSQL URL

# JWT
JWT_SECRET_KEY=min-32-characters-long-secret-key

# Flask
FLASK_ENV=production
FLASK_DEBUG=False
```

### Optional Variables
```bash
# Application
APP_NAME=SAT 1 & EST 1 Study Platform
APP_VERSION=1.0.0

# Email (for future notifications)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

---

## Testing

### Run Unit Tests
```bash
pytest tests/
```

### Test Coverage
```bash
pytest --cov=. tests/
```

### Load Testing
```bash
pip install locust

# Create locustfile.py and run
locust -f locustfile.py --host=http://localhost:5000
```

---

## Monitoring

### View Logs
```bash
# Development
# Check console output

# Production with Heroku
heroku logs --tail

# Production with AWS
tail -f /var/log/syslog
```

### Performance Monitoring
```bash
# Install New Relic (optional)
pip install newrelic
newrelic-admin run-program gunicorn app:app
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 5000
lsof -i :5000

# Kill process
kill -9 <PID>
```

### Database Connection Error
```bash
# Check DATABASE_URL in .env
# Verify database is running
# Check credentials
psql postgresql://user:password@localhost:5432/dbname
```

### JWT Token Issues
```bash
# Generate new secret
python -c "import secrets; print(secrets.token_hex(32))"

# Update in .env
JWT_SECRET_KEY=new_secret_here
```

### Import Errors
```bash
# Reinstall dependencies
pip install --upgrade --force-reinstall -r requirements.txt

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

### CORS Issues
```python
# Already handled in app.py with:
CORS(app)

# If issues persist, update app.py:
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://yourdomain.com"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

---

## Performance Optimization

### Database
- Add indexes to frequently queried columns
- Use connection pooling
- Regular backups

### Application
- Enable caching with Flask-Caching
- Use Celery for async tasks
- Compress responses with gzip

### Server
- Use CDN for static files
- Enable HTTP/2
- Setup rate limiting

---

## Security Best Practices

1. **Secrets Management**
   - Never commit .env file
   - Use environment variables
   - Rotate JWT secrets regularly

2. **Data Protection**
   - Use HTTPS only in production
   - Hash passwords with werkzeug
   - Validate all inputs

3. **Access Control**
   - Implement proper JWT expiration
   - Use role-based access (RBAC)
   - Regular security audits

4. **Dependencies**
   - Keep packages updated
   - Use pip-audit for vulnerabilities
   - Regular dependency reviews

---

## Maintenance

### Regular Tasks
- Monitor database size
- Check error logs
- Update dependencies monthly
- Backup database weekly
- Review user access logs

### Performance Tuning
- Monitor query performance
- Optimize slow endpoints
- Update database statistics
- Clear old session data

---

**Support:** For issues, contact Ahmed Labib  
**Last Updated:** 2024-01-05
