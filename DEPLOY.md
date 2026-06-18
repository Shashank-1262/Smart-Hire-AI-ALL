# SmartHire AI — Deployment Guide

## ⚠️ Why NOT Netlify?

Netlify only supports **static sites** and serverless functions.
This app is a full **Python Flask** backend with SQLite, file uploads, and PDF generation — it **cannot run on Netlify**.

---

## ✅ Deploy on Render (Free, Recommended)

Render.com is the easiest free platform for Flask apps.

### Step 1 — Push code to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
# Create a new repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/smarthire-ai.git
git push -u origin main
```

### Step 2 — Deploy on Render

1. Go to **https://render.com** and sign up (free)
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — click **Apply**
5. Wait ~3 minutes for build to finish
6. Your app is live at `https://smarthire-ai.onrender.com`

### What gets configured automatically (render.yaml):
- Build: `pip install -r requirements.txt`
- Start: `bash startup.sh` (copies seeded DB to `/tmp`, then starts gunicorn)
- Environment variables: `SECRET_KEY` (auto-generated), `RENDER=true`

---

## 🚂 Alternative: Deploy on Railway

1. Go to **https://railway.app** and sign up
2. Click **New Project → Deploy from GitHub Repo**
3. Select your repo
4. Railway auto-detects Python — set start command to: `bash startup.sh`
5. Add env var: `RAILWAY_ENVIRONMENT=production`

---

## 💻 Local Development

```bash
pip install -r requirements.txt
python seed_data.py   # First time only
python app.py
# Open http://127.0.0.1:5001
```

---

## 🔐 Demo Login Credentials

| Role    | Email                     | Password    |
|---------|---------------------------|-------------|
| Admin   | admin@smarthire.ai        | admin123    |
| Student | arjun.sharma@student.edu  | pass@123    |
| Company | hr@tcs.com                | tcs@123     |

---

## 📝 Important Notes

- **File uploads** on Render are stored in `/tmp` — they reset on each deploy/restart.
  For persistent uploads, connect an S3 bucket or Cloudinary.
- **SQLite DB** is copied from the repo to `/tmp` on startup — data also resets on restart.
  For persistent data, upgrade to PostgreSQL (free on Render).
- **Email/Telegram** features require setting `MAIL_USERNAME`, `MAIL_PASSWORD`, and `TELEGRAM_TOKEN`
  environment variables in the Render dashboard.
