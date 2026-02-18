FROM python:3.11-slim

WORKDIR /app

RUN mkdir -p /app/staticfiles

# You can change this local GID/UID if you are running into system permission issues
# But make sure to keep the uid/gid above 1000
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser

# Simple system dependencies
RUN apt-get update && apt-get install -y libpq-dev gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000
ENV PORT=8000
CMD ["sh", "-c", "gunicorn --worker-tmp-dir /dev/shm --bind 0.0.0.0:${PORT} --workers 3 --access-logfile - --error-logfile - --log-level debug config.wsgi:application"]