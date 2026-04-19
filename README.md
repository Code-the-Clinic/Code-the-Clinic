# Code-the-Clinic
Welcome to our CS 495 Capstone Project!

## About
Code the Clinic is a web application designed to help the Athletic Training department collect and analyze students' clinical interactions.

## What's in this repository?
The source code for the main application and its companion documentation website are co-located in this repository. The main application is located under `backend/` and the documentation website is located under `docs-site/`.

## Where can I find more documentation?
READMEs: `backend/README.md` (main application) and `docs-site/README.md` (project documentation website)
Project documentation website (detailed documentation and project deliverables): [Click here](https://code-the-clinic.github.io/Code-the-Clinic/)

## Where's the finished product?
Deployed application: [Click here](https://code-the-clinic-prod-1-gxc6a0cra4cvdxbf.northcentralus-01.azurewebsites.net/)

# Backend Project Setup Guide

## 0. Prerequisites

Before you begin, ensure you have the following installed:
- **Git**: [Download Git](https://git-scm.com/downloads)
- **Docker Desktop**: [Download Docker](https://www.docker.com/products/docker-desktop/) (**Must be running** before starting)
- **Python 3.10+**: (Optional) Only needed for local IDE indexing and autocomplete.

---

## 1. Initial Setup & Getting Started

Follow these steps to set up the project locally using Docker.

### Step 1: Clone the Repository
Open your terminal and run the following to pull the code and enter the directory:
```bash
git clone <your-repository-url-here>
cd <your-repository-name>
```

### Step 2: Environment Variables
Create a `.env` file in the root directory by copying the example template:
```bash
cp .env.example .env
```
Then configure your local variables (secret keys, database settings, etc.).

To generate a fresh Django Secret Key, run:
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

**Important:**
- Never commit `.env` to Git
- Do NOT store secrets in `.env.example`
- Store all credentials (Azure, etc.) in `.env`

---

### Step 3: Build and Start Containers

```bash
docker-compose up -d --build
```

---

### Step 4: Run Database Migrations

Check for migrations:
```bash
docker-compose exec backend python manage.py showmigrations
```

Apply migrations:
```bash
docker-compose exec backend python manage.py migrate
```

---

### Step 5: Create Admin Account

```bash
docker-compose exec backend python manage.py createsuperuser
```

---

## 2. Accessing the Application

- **Django Backend:** http://localhost:8000  
- **MkDocs Documentation:** http://localhost:8001  

> If these don’t load, check `docker-compose.yml` port mappings.

---

## 3. Project Structure

```
backend/            # Core Django application
config/             # Project settings and routing
core/               # Base templates and shared logic
clinic_reports/     # Domain-specific reports app
user_logging/       # Logging functionality
docs-site/          # MkDocs documentation
docker-compose.yml  # Container orchestration
```

**Notes:**
- Active apps: `core`, `clinic_reports`, `user_logging`
- `api` app was removed (unused)
- `scripts/export_dashboard_raw_to_excel.py` is a standalone script
- `backend/src` and `frontend` are placeholders

---

## 4. Modifying and Extending

### Managing Dependencies

Add to `requirements.txt`, then rebuild:

```bash
docker-compose up -d --build
```

---

### Modifying the Database

Generate migrations:
```bash
docker-compose exec backend python manage.py makemigrations
```

Apply migrations:
```bash
docker-compose exec backend python manage.py migrate
```

---

### Adding a New Django App

```bash
docker-compose exec backend python manage.py startapp [app_name]
```

Then:
- Move it into `/backend`
- Add to `INSTALLED_APPS` in `settings.py`

---

## 5. Running & Testing

Run everything:
```bash
docker-compose up
```

Run all tests:
```bash
docker-compose exec backend python manage.py test
```

Run tests for one app:
```bash
docker-compose exec backend python manage.py test clinic_reports
```

---

## 6. IDE Setup (VS Code)

- Install extensions: Python, Docker, Django  
- Create local venv (for autocomplete only):

```bash
python -m venv venv
pip install -r requirements.txt
```

- Select interpreter:
  - `Ctrl + Shift + P`
  - "Python: Select Interpreter"
  - Choose `venv`

---

## 7. Security Notes

- Never commit secrets to Git
- Always use `.env` for credentials
- Set `DEBUG=False` in production
- Avoid `@csrf_exempt` — use CSRF tokens instead

---

## 8. Troubleshooting

Stop containers:
```bash
docker-compose down
```

Hard reset (WARNING: deletes local DB data):
```bash
docker-compose down -v
docker system prune -f
docker-compose up --build
```

View logs:
```bash
docker-compose logs -f backend
```

Common issues:
- **Missing tables (e.g., django_session)** → run migrations
- **Docker issues after crash** → rebuild without cache

---

## 9. Azure / myBama Authentication Setup (Optional)

### 1. Create Azure App

- Go to Azure Portal → App Registrations → New Registration
- Account type: Multitenant
- Redirect URI:
  ```
  http://localhost:8000/accounts/microsoft/login/callback/
  ```

---

### 2. Get Credentials

- Copy **Client ID** → `.env` as `AZURE_CLIENT_ID`
- Create client secret → `.env` as `AZURE_SECRET`
- Add tenant ID to `.env`

---

### 3. Enable Admin Access

1. Log in via Microsoft
2. Log out
3. Create superuser:
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```
4. Log into admin panel
5. Grant your Microsoft user superuser permissions
6. Delete temporary superuser

---

## 10. Debug Tips

- Import errors after Docker restart → rebuild containers
- DB relation errors → rerun migrations
- Containers acting weird → full reset (see Troubleshooting)

---

## 11. Development Notes

- Docker is the source of truth (not local Python env)
- Local `venv` is only for IDE support
- Always rebuild after dependency changes
