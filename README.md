# 🧠 Quiz Generator

An AI-powered full-stack quiz generation platform built with Next.js, FastAPI, and OpenAI.

The platform allows users to:

* Generate quizzes using AI
* Organize quizzes into folders
* View quiz history
* Share quizzes with others
* Authenticate securely with email verification

---

# ✨ Features

* 🤖 AI-powered quiz generation
* 🔐 JWT authentication & email verification
* 📂 Folder-based quiz organization
* 🕘 Quiz history tracking
* 🔗 Quiz sharing functionality
* 📧 Email notification support
* 🐳 Dockerized development environment
* ⚡ FastAPI backend with async support

---

# 🏗️ Project Architecture

```
quiz-generator/
├── client/                           # Next.js frontend
│   ├── pages/                        # Next.js routes
│   │   ├── admin/                    # Admin pages
│   │   ├── auth/                     # Authentication pages
│   │   ├── folders/                  # Folder management
│   │   ├── generate/                 # Quiz generation
│   │   ├── live-quiz/                # Live quiz sessions
│   │   ├── popular/                  # Popular quizzes
│   │   ├── quiz-access/              # Quiz access
│   │   ├── quiz_display/             # Quiz display
│   │   ├── quiz_history/             # Quiz history
│   │   ├── saved_quiz/               # Saved quizzes
│   │   ├── share/                    # Quiz sharing
│   │   ├── _app.tsx                  # App wrapper
│   │   ├── _document.tsx             # Document wrapper
│   │   ├── index.tsx                 # Homepage
│   │   ├── notifications.tsx         # Notifications page
│   │   ├── profile.tsx               # User profile
│   │   └── quiz.tsx                  # Quiz page
│   ├── src/                          # Source files
│   │   ├── app/                      # App-level code
│   │   ├── features/                 # Domain features
│   │   └── shared/                   # Shared utilities
│   ├── public/                       # Static assets
│   ├── __tests__/                    # Frontend tests
│   └── config files                  # Config files
│
├── server/                           # FastAPI backend
│   ├── app/                          # Core application
│   │   ├── api/                      # API routes
│   │   ├── auth/                     # Authentication
│   │   ├── core/                     # Shared infrastructure
│   │   ├── db/                       # Database layer
│   │   │   ├── core/                 # DB core
│   │   │   ├── crud/                 # CRUD operations
│   │   │   ├── models/               # MongoDB models
│   │   │   ├── routes/               # DB routes
│   │   │   ├── schemas/              # DB schemas
│   │   │   ├── seed_data/            # Seed data
│   │   │   ├── services/             # DB services
│   │   │   └── v2/                   # Database v2
│   │   ├── email_platform/           # Email services
│   │   ├── notifications/            # Notifications module
│   │   ├── quiz/                     # Quiz module
│   │   │   ├── mock_data/            # Mock data
│   │   │   ├── models/               # Quiz models
│   │   │   ├── repositories/         # Quiz repositories
│   │   │   ├── routers/              # Quiz routers
│   │   │   ├── routes/               # Quiz routes
│   │   │   ├── schemas/              # Quiz schemas
│   │   │   ├── seed_data/            # Quiz seed data
│   │   │   ├── services/             # Quiz services
│   │   │   └── utils/                # Quiz utilities
│   │   ├── schemas/                  # Pydantic schemas
│   │   ├── services/                 # Business logic
│   │   ├── share/                    # Quiz sharing
│   │   ├── users/                    # Users module
│   │   ├── databaseSeeding.py        # DB seeding
│   │   ├── restoreDataSeed.py        # Restore seed
│   │   ├── seed.py                   # Seed script
│   │   └── seed_data.py              # Seed data
│   ├── api/                          # API route handlers
│   ├── core/                         # Core utilities
│   ├── schemas/                      # Pydantic schemas
│   ├── scripts/                      # Helper scripts
│   ├── tests/                        # Backend tests
│   └── main.py                       # FastAPI entry point
│
├── docs/                             # Documentation
│   ├── API.md                        # API documentation
│   └── testing.md                    # Testing guide
│
├── docker-compose.yml                # Container orchestration
├── Dockerfile                        # Main Dockerfile
├── Dockerfile.mongo                  # MongoDB Dockerfile
├── README.md                         # This file
├── .env-example                      # Example environment variables
└── generator.py                      # Utility scripts
```

---

# 🚀 Tech Stack

| Layer          | Technology                        |
| -------------- | --------------------------------- |
| Frontend       | Next.js, TypeScript, Tailwind CSS |
| Backend        | FastAPI, Python                   |
| Database       | MongoDB                           |
| AI Services    | OpenAI, Pinecone, HuggingFace     |
| Queue System   | Celery + Redis                    |
| Authentication | JWT + Email Verification          |
| DevOps         | Docker & Docker Compose           |

---

# 📋 Prerequisites

Before running the project, ensure you have:

* Docker Desktop
* WSL2 (Windows users)
* Node.js v18+
* Python 3.12+ (recommended)
* Git

### Recommended System Specs

* Minimum: 8GB RAM
* Recommended: 16GB RAM

---

# ⚙️ Environment Variables

## Frontend (`client/.env.local`)

```env
SHARE_URL=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SSR_API_BASE_URL=http://localhost:8000
```

## Backend (`.env`)

```env
# =========================
# JWT SECURITY
# =========================
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
VERIFICATION_TOKEN_EXPIRE_HOURS=1

# =========================
# EMAIL CONFIGURATION
# =========================
EMAIL_ADDRESS=
EMAIL_PASSWORD=
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
SENDER_EMAIL=
PRIMARY_EMAIL_PROVIDER=SMTP

# =========================
# DATABASE
# =========================
MONGO_URL=mongodb://localhost:27017
MONGO_URI=mongodb://localhost:27017
DB_NAME=quizApp_db
MONGO_PORT=27017

# =========================
# SERVER PORTS
# =========================
PORT=8000
BACKEND_PORT=8000
FRONTEND_PORT=3000

# =========================
# FRONTEND URLS
# =========================
SHARE_URL=http://localhost:3000
ALLOWED_ORIGINS=http://localhost:3000

# =========================
# REDIS
# =========================
REDIS_URL=redis://localhost:6379/0

# =========================
# OPTIONAL SERVICES
# =========================
HUGGINGFACEHUB_API_TOKEN=
FERNET_KEY=
```
> ⚠️ **Important:** The `EMAIL_PASSWORD` must be a **Google App Password**, not your regular Gmail login password. Regular passwords will fail with authentication errors.

---

# 🚀 Getting Started

## 1. Clone Repository

```bash
git clone https://github.com/Hacklift/quiz-generator.git
cd quiz-generator
```

---

## 2. Configure Environment Variables

```bash
cp .env-example .env
```

Create frontend environment file:

```bash
touch client/.env.local
```
Create `client/.env.local` and populate it using the values shown above.

---

# 🐳 Run with Docker (Recommended)

## Start Application

```bash
docker-compose up --build
```

## Run in Background

```bash
docker-compose up -d
```

---

# 🌐 Application URLs

| Service      | URL                        |
| ------------ | -------------------------- |
| Frontend     | http://localhost:3000      |
| Backend API  | http://localhost:8000      |
| Swagger Docs | http://localhost:8000/docs |

---

# 💻 Local Development Setup

## Backend Setup

```bash
cd server

pip install pipenv
pipenv install
pipenv shell

uvicorn main:app --reload --port 8000
```

---

## Frontend Setup

```bash
cd client

pnpm install
pnpm dev
```

---

# 🔑 API Keys & Services

| Service      | URL                                    |
| ------------ | -------------------------------------- |
| OpenAI       | https://platform.openai.com/api-keys   |
| Pinecone     | https://www.pinecone.io                |
| HuggingFace  | https://huggingface.co/settings/tokens |
| Google Cloud | https://console.cloud.google.com       |

---

# 🔐 Generate Security Keys

## JWT Secret

```bash
openssl rand -base64 64
```

## Fernet Key

```bash
pip install cryptography

python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

# 📧 Gmail App Password Setup

1. Enable 2-Step Verification on your Google account
2. Navigate to **App Passwords**
3. Select **Mail**
4. Generate password
5. Copy generated 16-character password

---

# 🐳 Docker Commands

| Command                     | Description                 |
| --------------------------- | --------------------------- |
| `docker-compose up`         | Start services              |
| `docker-compose up -d`      | Run in background           |
| `docker-compose up --build` | Rebuild containers          |
| `docker-compose down`       | Stop services               |
| `docker-compose down -v`    | Remove containers & volumes |
| `docker-compose logs -f`    | View live logs              |
| `docker-compose ps`         | View container status       |

---

# ❗ Troubleshooting

## Docker Desktop Not Running

* Start Docker Desktop
* Verify whale icon 🐳 appears in system tray
* Run:

```bash
docker ps
```

---

## WSL Performance Issues

❌ Avoid using:

```bash
/mnt/c/
```

✅ Recommended:

```bash
/home/username/
```

---

## Port Already in Use

```bash
sudo lsof -i :3000
```

Update ports inside `docker-compose.yml` if necessary.

---

## API Key & Service Errors

- Ensure `.env` variables are correctly set (no spaces around `=`)
- Gmail: Must use **App Password**, not regular password
- Redis: Must be running for Celery (`docker-compose ps`)
- Restart Docker after changes:

```bash
docker-compose down
docker-compose up -d
```

---

## Redis / Celery Issues

If Celery tasks are not executing:

```bash
# Check if Redis is running
docker-compose ps

# Redis should show "Up" status

# Restart Celery if needed
docker-compose restart celery

# View Celery logs
docker-compose logs celery
```
---

# 🤝 Contributing

## Branch Strategy

* Never push directly to `main`
* Create feature branches for all work

Example:

```bash
git checkout -b feature/quiz-sharing
```

---

# 📄 License

MIT License
