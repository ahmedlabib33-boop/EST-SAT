# Vercel Deployment Guide

**SAT 1 & EST 1 Study Platform**  
**Teacher:** Ahmed Labib

---

## 📋 Quick Start (3 Steps)

### Step 1: Connect Repository
1. Go to [vercel.com](https://vercel.com)
2. Sign up or log in
3. Click "Add New" → "Project"
4. Select your GitHub repository
5. Click "Import"

### Step 2: Configure Project
- **Framework Preset:** Other
- **Build Command:** `npm run build`
- **Output Directory:** `.`
- **Install Command:** `npm install`

### Step 3: Deploy
1. Click "Deploy"
2. Wait for deployment to complete
3. Your platform is live! 🎉

---

## 🌐 Deployment Architecture

```
Frontend (Vercel Static)
├── index.html (Original)
├── premium-dashboard.html
├── student-portal.html
└── Math & Physics guides

Backend (Separate Service)
├── Python/Flask API
├── SQLAlchemy Database
└── Authentication (JWT)
```

---

## 📦 What Gets Deployed

### Frontend on Vercel
- ✅ `index.html` (Original interface)
- ✅ `premium-dashboard.html` (Premium dashboard)
- ✅ `student-portal.html` (Student interface)
- ✅ All study materials (md files)
- ✅ CSS/JavaScript included

### Backend (Deploy Separately)
Deploy Python backend to:
- **Railway** (Recommended - $5/month, free tier available)
- **Render** (Great free tier)
- **Heroku** (Free tier deprecated)
- **Fly.io** (Fast, scalable)

---

## 🚀 Full Deployment Steps

### Frontend Deployment (Vercel)

#### 1. Connect GitHub Account
```bash
# Ensure your repository is on GitHub
git remote -v
# Should show your repository URL
```

#### 2. Deploy to Vercel via Web UI
1. Visit [vercel.com/import](https://vercel.com/import)
2. Select "GitHub" as source
3. Authenticate and select repository
4. Click "Import"
5. Choose project settings (defaults are fine)
6. Click "Deploy"

#### 3. Set Custom Domain (Optional)
1. In Vercel dashboard, go to "Settings" → "Domains"
2. Add your custom domain
3. Follow DNS instructions
4. Domain links in 24-48 hours

### Backend Deployment (Railway)

#### 1. Create Railway Account
- Visit [railway.app](https://railway.app)
- Sign up with GitHub
- Connect GitHub account

#### 2. Deploy Backend
```bash
# Initialize Railway
railway login

# Deploy
railway init
railway deploy

# Set environment variables
railway env
```

#### 3. Set Environment Variables
In Railway dashboard:
```
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=your-secret-key
FLASK_ENV=production
```

#### 4. Get Backend URL
- Copy the Railway project URL
- Update frontend API calls to point to this URL

---

## 🔧 Environment Setup

### Frontend Environment Variables (None needed for static files)

### Backend Environment Variables (Railway/Render)
```env
DATABASE_URL=postgresql://user:password@host:5432/estsat
JWT_SECRET_KEY=min-32-characters-long-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=False
```

---

## 🔗 Connecting Frontend to Backend

### Update API Calls
Create a config file:

**api-config.js** (optional)
```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

export const apiCall = async (endpoint, options = {}) => {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });
  return response.json();
};
```

### In HTML Files
```html
<script>
const API_URL = 'https://your-backend-on-railway.railway.app/api';

// Example API call
async function login(username, password) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  return response.json();
}
</script>
```

---

## 📊 Deployment Comparison

| Platform | Frontend | Backend | Cost | SSL | Scaling |
|----------|----------|---------|------|-----|---------|
| **Vercel** | ⭐⭐⭐⭐⭐ | ❌ | Free | ✅ | Auto |
| **Railway** | Good | ⭐⭐⭐⭐⭐ | $5/mo | ✅ | Auto |
| **Render** | Good | ⭐⭐⭐⭐⭐ | Free | ✅ | Limited |
| **Heroku** | Good | ⭐⭐⭐⭐⭐ | Paid | ✅ | Manual |

---

## 📈 Recommended Setup

**Best Combination:**
- **Frontend:** Vercel (Free, fast, CDN)
- **Backend:** Railway ($5/month, reliable, scalable)
- **Database:** PostgreSQL on Railway ($10-15/month)
- **Total Cost:** ~$15/month (or less with free tiers)

---

## 🔒 Security Checklist

Before deploying:

- [ ] JWT_SECRET_KEY is strong (32+ chars)
- [ ] DATABASE_URL uses SSL connection
- [ ] No secrets in code or git
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] HTTPS enforced
- [ ] Input validation active
- [ ] Password hashing working

---

## 📝 Deployment Checklist

### Pre-Deployment
- [ ] All code committed to GitHub
- [ ] Tests passing (if applicable)
- [ ] Environment variables documented
- [ ] Database migrations ready
- [ ] API endpoints tested locally

### During Deployment
- [ ] Frontend deployed to Vercel
- [ ] Backend deployed to Railway/Render
- [ ] Environment variables set
- [ ] Database connected
- [ ] Domains configured

### Post-Deployment
- [ ] Frontend accessible at Vercel URL
- [ ] Backend API responding
- [ ] Login working
- [ ] Quiz system functional
- [ ] Data persisting
- [ ] Emails configured (if applicable)
- [ ] Monitoring enabled

---

## 🧪 Testing Deployment

### Frontend
```bash
# Test Vercel deployment
curl https://your-domain.vercel.app/

# Should return HTML content
```

### Backend
```bash
# Test API
curl https://your-backend.railway.app/api/

# Should return JSON with API info
```

### Integration
```bash
# Test login
curl -X POST https://your-backend.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"student1","password":"student123"}'
```

---

## 🚨 Troubleshooting

### Issue: Frontend shows "Cannot find module"
**Solution:** Clear cache and redeploy
```bash
vercel --prod --force
```

### Issue: Backend connection refused
**Solution:** 
1. Check backend is running
2. Verify DATABASE_URL is correct
3. Check CORS settings
4. Ensure JWT_SECRET_KEY is set

### Issue: Database connection timeout
**Solution:**
1. Verify PostgreSQL is running
2. Check connection string
3. Ensure whitelist includes Railway IP
4. Test connection locally

### Issue: High latency/slow performance
**Solution:**
1. Enable caching on Vercel
2. Optimize database queries
3. Add CDN for static files
4. Monitor backend resources

---

## 📊 Performance Optimization

### Frontend (Vercel)
- ✅ Automatic CDN distribution
- ✅ Edge caching enabled
- ✅ Automatic compression
- ✅ Image optimization

### Backend (Railway)
- ✅ Database connection pooling
- ✅ Query optimization
- ✅ Response caching headers
- ✅ Gzip compression

---

## 🔄 CI/CD Pipeline

### GitHub Actions (Optional)
Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Vercel

on:
  push:
    branches: [main, claude/quirky-carson-vnhe5v]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: vercel/action@master
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
```

---

## 📞 Support Links

- **Vercel Docs:** https://vercel.com/docs
- **Railway Docs:** https://docs.railway.app
- **Render Docs:** https://render.com/docs
- **Flask Deployment:** https://flask.palletsprojects.com/deployment
- **PostgreSQL:** https://www.postgresql.org/docs

---

## ✅ Deployment Complete!

Once deployed:

1. **Frontend URL:** `https://your-domain.vercel.app`
2. **Backend URL:** `https://your-backend.railway.app`
3. **API Endpoint:** `https://your-backend.railway.app/api`
4. **Status Page:** `https://your-domain.vercel.app/`

---

**Teacher:** Ahmed Labib  
**Platform:** SAT 1 & EST 1 Study System  
**Status:** ✅ Ready for Production

For questions or issues, refer to the documentation or contact support.
