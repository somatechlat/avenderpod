#!/bin/bash
set -e

# Ensure Django settings are configured
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-core.settings}

echo "🔧 Running Django migrations..."
python manage.py migrate --noinput

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

read_secret() {
    local name="$1"
    local file_var="${name}_FILE"
    local file_path="${!file_var:-}"
    if [ -n "$file_path" ] && [ -f "$file_path" ]; then
        cat "$file_path"
    else
        printf '%s' "${!name:-}"
    fi
}

# Create superuser from non-secret username plus password secret file if not exists.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$(read_secret DJANGO_SUPERUSER_PASSWORD)" ]; then
    echo "👤 Creating superuser (if not exists)..."
    python manage.py shell <<'PY'
import os
from pathlib import Path
from django.contrib.auth import get_user_model

username = os.environ["DJANGO_SUPERUSER_USERNAME"]
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@avender.local")
password_file = os.environ.get("DJANGO_SUPERUSER_PASSWORD_FILE", "")
password = Path(password_file).read_text(encoding="utf-8").strip()
user_model = get_user_model()
user, created = user_model.objects.get_or_create(
    username=username,
    defaults={"email": email, "is_staff": True, "is_superuser": True},
)
# Always sync password from secret file (handles rotation + persistent volumes)
if created or not user.check_password(password):
    user.set_password(password)
    user.save(update_fields=["password"])
PY
fi

echo "🏗️  Seeding SaaS plans..."
python manage.py seed_plans

# In dev mode, register the local Agent Zero container as a tenant
# so it appears in the SysAdmin dashboard with management actions.
if [ "${DJANGO_DEBUG:-false}" = "true" ]; then
    echo "🐳 Registering dev tenant (Docker mode)..."
    python manage.py register_dev_tenant
fi

if [ $# -gt 0 ]; then
    echo "⚙️ Executing custom command: $@"
    exec "$@"
else
    echo "🚀 Starting SysAdmin Control Plane on port 8000..."
    exec gunicorn core.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 2 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -
fi
