FROM python:3.11-slim

WORKDIR /app

RUN mkdir -p /app/staticfiles

RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser

# Simple system dependencies
RUN apt-get update && apt-get install -y libpq-dev gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

USER appuser

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]