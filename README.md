# Flask Todo App

**Production-Ready Multi-User Task Management with Vercel Serverless Deployment**

---

### 🌐 Live Deployment
- **App**: *Deploy on Vercel and add your URL here*

---

## Overview

**Flask Todo App** is a production-ready multi-user task management SaaS application built with a clean **Flask + PostgreSQL** stack and deployed as a serverless application on **Vercel**.

The system is engineered with production concerns in mind:
- **Per-user data isolation** — each user sees only their own tasks
- **Secure session management** — HTTPONLY, SameSite, and Secure cookie flags
- **Serverless-safe architecture** — no persistent filesystem dependency, auto-created schema
- **Environment-aware configuration** — distinct behaviour between development and production

---

## Core Capabilities

- **Multi-User Authentication**: Registration, login, and logout with bcrypt-hashed passwords.
- **Task Lifecycle Management**: Create, update, toggle completion, and delete todos.
- **Due Date Tracking**: Assign and display optional due dates per task.
- **Serverless-Safe Database**: `db.create_all()` auto-provisions schema on cold start — no migration CLI required.
- **Environment-Aware Config**: SQLite fallback for local dev; PostgreSQL enforced in production.
- **Secure Session Handling**: `HTTPONLY`, `SameSite=Lax`, and `Secure` flags enforced in production.
- **Error Pages**: Custom 404 and 500 handlers with consistent UI.
- **Vercel Deployment**: Fully configured with `vercel.json` for zero-configuration deploys.

---

## Architecture

### Request Flow

```mermaid
graph TD
    A[Browser Request] --> B[Vercel Edge]
    B --> C[api/index.py - WSGI Entry]
    C --> D[Flask App - app.py]
    D --> E{Authenticated?}
    E -->|No| F[Redirect to /login]
    E -->|Yes| G[Route Handler]
    G --> H[SQLAlchemy ORM]
    H --> I[(PostgreSQL - Production)]
    H --> J[(SQLite - Local Dev)]
    G --> K[Jinja2 Template]
    K --> L[HTML Response]
```

> **Architecture Diagram**
> ![Architecture Diagram](<docs/screenshots/Todo Architecture.png>)

---

## Screenshots

### Login Page
> ![Login Page](<docs/screenshots/Screenshot 2026-02-22 063908.png>)

### Dashboard
> ![Dashboard](<docs/screenshots/Screenshot 2026-02-22 063940.png>)

### Add Todo
> ![Add Todo](<docs/screenshots/Screenshot 2026-02-22 064101.png>)

---

## Engineering Decisions & Design Rationale

### Why `db.create_all()` Instead of Migrations?
Vercel's serverless runtime has no persistent shell — you cannot run `flask db upgrade` on deploy. Instead, `db.create_all()` runs inside an app context at module load time, safely provisioning the schema on the first cold start. This makes the app truly zero-touch deployable.

### Why Serverless (Vercel)?
Vercel removes the need to manage servers, handle scaling, or configure reverse proxies. The app receives traffic via Vercel's edge network and runs as a Python WSGI function — paying only for actual requests, not idle uptime.

### Why Per-User Query Filtering?
Every database query includes `filter_by(user_id=current_user.id)`. This prevents horizontal privilege escalation — a logged-in user cannot access, modify, or delete another user's tasks even by guessing task IDs.

### Why Cookie Security Flags?
- `HTTPONLY` — prevents JavaScript from reading session cookies (XSS mitigation)
- `SameSite=Lax` — reduces CSRF attack surface from cross-origin form submissions
- `Secure` (production only) — ensures cookies are only transmitted over HTTPS

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.x, Flask 3.x |
| ORM | Flask-SQLAlchemy 3.x |
| Database (Production) | PostgreSQL via `psycopg2-binary` |
| Database (Development) | SQLite (auto-created, no setup needed) |
| Auth | Werkzeug password hashing (`pbkdf2:sha256`) |
| Frontend | Jinja2 Templates, Bootstrap 5.x (CDN) |
| Hosting | Vercel Serverless (Python 3.x runtime) |

---

## Project Structure

```text
Todo-app/
├── api/
│   └── index.py          # Vercel WSGI entry point
├── docs/
│   └── screenshots/      # Architecture diagram & app screenshots
├── templates/
│   ├── base.html         # Shared layout, navbar, Bootstrap
│   ├── index.html        # Dashboard — task list + add form
│   ├── login.html        # Login page
│   ├── register.html     # Registration page
│   ├── update.html       # Edit task page
│   ├── 404.html          # Custom Not Found page
│   └── 500.html          # Custom Server Error page
├── app.py                # Flask app, models, routes, config
├── vercel.json           # Vercel deployment configuration
├── requirements.txt      # Pinned Python dependencies
├── .gitignore
└── README.md
```

---

## Local Development

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/Lohith0204/flask-todo-app
cd flask-todo-app

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the App

```bash
python app.py
```

No environment variables needed — `SECRET_KEY` auto-generates a random value and SQLite is used automatically for the database.

Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

> **Optional:** To use a local PostgreSQL database instead of SQLite:
> ```bash
> set DATABASE_URL=postgresql://user:password@localhost:5432/todo_db   # Windows
> export DATABASE_URL=postgresql://user:password@localhost:5432/todo_db # macOS/Linux
> ```

---

## Vercel Deployment

### Prerequisites
- GitHub account with this repo pushed
- [Vercel](https://vercel.com) account (free tier available)
- PostgreSQL database — recommended providers:
  - [Neon](https://neon.tech) (free tier, serverless Postgres)
  - [Supabase](https://supabase.com) (free tier)
  - [Railway](https://railway.app)

### Steps

**1. Push to GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/Lohith0204/flask-todo-app
git push -u origin main
```

**2. Import to Vercel**
- Go to [vercel.com](https://vercel.com) → **New Project** → import your GitHub repo
- Framework preset: **Other** (Vercel auto-detects `vercel.json`)

**3. Set Environment Variables** *(Settings → Environment Variables)*

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Strong random string — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Your PostgreSQL connection URL |
| `ENV` | `production` |

**4. Deploy**

Vercel builds and deploys automatically. Database tables are created on the first request — no manual steps needed.

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ Production | Flask session signing key — must be a long, random string |
| `DATABASE_URL` | ✅ Production | PostgreSQL connection string (`postgresql://...`) |
| `ENV` | ✅ Production | Set to `production` to enable secure cookies and enforce env vars |

---

## Security Model

| Control | Implementation |
|---------|----------------|
| Password Storage | `pbkdf2:sha256` via Werkzeug — never stored in plaintext |
| Session Security | HTTPONLY + SameSite + Secure cookie flags |
| Authorization | Every query filtered by `user_id` — no cross-user data access |
| Input Handling | `strip()` on all user inputs, `nullable=False` on required DB columns |
| Error Handling | Custom 404/500 pages — no stack traces exposed to users |

---

## Future Enhancements

- Task priority levels and labels/tags.
- Search and filter by status, due date, or keyword.
- Email notifications for approaching due dates.
- REST API layer for mobile client support.
- OAuth login (Google / GitHub) via Flask-Dance.

---

## Highlights

- Multi-user authentication system with secure password hashing.
- Serverless Flask deployment using Vercel — zero server management.
- PostgreSQL production database integration with automatic schema provisioning.
- Secure session management with HTTPONLY, SameSite, and Secure cookie flags.

---

## What This Project Demonstrates

- Building a secure, multi-user web application with Flask from scratch.
- Designing a serverless-compatible backend — no reliance on persistent disk or CLI tooling.
- Implementing environment-aware configuration for seamless dev-to-production transitions.
- Applying defence-in-depth at the session, query, and cookie layer.
- Clean project structure ready for GitHub portfolio and production deployment.