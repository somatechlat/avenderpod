#!/usr/bin/env bash
set -e

echo "==============================================="
echo "¡A VENDER! REAL E2E Verification Pipeline"
echo "==============================================="

echo "1. Checking Container Availability..."
if ! docker exec avender_sysadmin echo "SysAdmin Container Active"; then
    echo "ERROR: avender_sysadmin container is not running."
    exit 1
fi

echo "2. Installing Playwright Tooling inside Container..."
docker exec avender_sysadmin /bin/bash -c "pip install pytest-playwright"
docker exec avender_sysadmin /bin/bash -c "playwright install chromium --with-deps"

echo "3. Copying Real Test Script into Container..."
docker exec avender_sysadmin /bin/bash -c "mkdir -p /app/tenants/tests/e2e"
docker cp admin/tenants/tests/e2e/test_real_lifecycle.py avender_sysadmin:/app/tenants/tests/e2e/test_real_lifecycle.py

echo "4. Fetching Real Credentials..."
REAL_PASSWORD=$(cat deployments/avender/secrets/django_superuser_password 2>/dev/null || docker exec avender_sysadmin cat /run/secrets/django_superuser_password)

if [ -z "$REAL_PASSWORD" ]; then
    echo "ERROR: Could not fetch REAL_PASSWORD."
    exit 1
fi

echo "5. Starting Dedicated E2E Test Server (to bypass SSL loop)..."
docker exec avender_sysadmin python -c "import os, signal; [os.kill(int(p), signal.SIGKILL) for p in os.listdir('/proc') if p.isdigit() and (lambda: '8080' in open(f'/proc/{p}/cmdline', 'r').read() if os.path.exists(f'/proc/{p}/cmdline') else False)()]" || true
docker exec -d -e DJANGO_DEBUG=true -e SYSADMIN_API_URL="http://avender_sysadmin:8000/api/saas" avender_sysadmin /bin/bash -c "cd /app && gunicorn core.wsgi:application --bind 0.0.0.0:8080 --workers 2 --timeout 120"

# Give the server 5 seconds to start
sleep 5

echo "6. Executing REAL Playwright E2E Tests (NO MOCKS)..."
# Pass the real password and use port 8080
docker exec -e TEST_PASSWORD="$REAL_PASSWORD" avender_sysadmin /bin/bash -c "cd /app && pytest tenants/tests/e2e/test_real_lifecycle.py -v -s"

echo "7. Cleaning up..."
docker exec avender_sysadmin python -c "import os, signal; [os.kill(int(p), signal.SIGKILL) for p in os.listdir('/proc') if p.isdigit() and (lambda: '8080' in open(f'/proc/{p}/cmdline', 'r').read() if os.path.exists(f'/proc/{p}/cmdline') else False)()]" || true

echo "==============================================="
echo "REAL E2E Pipeline Execution Complete."
echo "==============================================="
