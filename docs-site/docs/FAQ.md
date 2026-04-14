# FAQ

### How do I run the app locally?

You can use `docker-compose.yml` to start services. Alternatively, run the Django backend from the `backend/` folder:

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

### Is there a Docker setup?

Yes — see `docker-compose.yml` and `backend/Dockerfile` for containerized development and deployment instructions.

### How do I install dependencies without Docker?

Create a virtualenv and run `pip install -r backend/requirements.txt` from the repository root or from `backend/`.

### How do I run database migrations?

From `backend/` run `python manage.py migrate`. Migration files are in each app’s `migrations/` folder.

### How do I create an admin/superuser?

From `backend/` run `python manage.py createsuperuser` and follow the prompts.

### Where are the main Django apps located?

The main apps live under `backend/`: `clinic_reports/`, `core/`, `api/`, and `user_logging/`.

### How do I run tests?

From `backend/` run `python manage.py test` to execute Django tests.

### How do I export dashboard data to Excel?

There is a script at `scripts/export_dashboard_raw_to_excel.py`. Ensure required settings and data are available before running it.

### Where are templates and static files?

Templates live in each app’s `templates/` folder (e.g., `core/templates/core/`). Static files are under `core/static/` and `staticfiles/`.

### How do I configure environment variables (DB, secrets)?

Configuration is in `config/settings.py`. Provide production secrets and DB settings via environment variables when running Docker or deploying to a host.

### How do I access API endpoints?

The API app is `backend/api/`. Check `config/urls.py` and `backend/api/views.py` for available endpoints and auth requirements.

### How do I contribute code or run the docs site?

See `docs-site/README.md` and `docs-site/mkdocs.yml` for docs instructions. For code contributions, follow the repo’s branch/PR process (default branch is `main`).

### How are user actions and logs tracked?

The `user_logging/` app contains models, middleware, and signals for tracking user events — see `backend/user_logging/`.

### Are there data privacy or export considerations?

Yes — exports and logs can contain personal or health-related data. Follow applicable data protection policies before exporting or sharing data.

### Where do I find deployment or production guidance?

Check `backend/Dockerfile`, `docker-compose.yml`, and adapt `config/settings.py` for production (security, allowed hosts, static file serving, DB credentials).

### What if static assets aren’t served in production?

Run `python manage.py collectstatic` and ensure a web server (e.g., nginx) or storage backend serves `STATIC_ROOT`.

### How do I change or add clinic report fields?

Update models in `clinic_reports/models.py`, run `makemigrations` and `migrate`, and update related forms/templates in `clinic_reports/templates/clinic_reports/`.

### Where are deliverables and project docs?

See `docs-site/docs/`, including `deliverables.md` for project deliverables and other documentation.
