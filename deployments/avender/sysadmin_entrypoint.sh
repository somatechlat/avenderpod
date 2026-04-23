#!/bin/bash
set -e

# Use the volume-mounted db directory for SQLite
export DATABASE_PATH="/app/db/db.sqlite3"

# Override Django settings to point to the persistent volume
export DJANGO_SETTINGS_MODULE="core.settings"

echo "🔧 Running Django migrations..."
python manage.py migrate --noinput

# Create superuser from environment variables if not exists
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "👤 Creating superuser (if not exists)..."
    python manage.py createsuperuser \
        --noinput \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email "${DJANGO_SUPERUSER_EMAIL:-admin@avender.local}" \
        2>/dev/null || echo "  Superuser already exists."
fi

echo "🚀 Starting SysAdmin Control Plane on port 8000..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 120 \
    --reload \
    --access-logfile - \
    --error-logfile -
