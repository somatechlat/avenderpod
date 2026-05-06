#!/usr/bin/env bash
set -e

echo "==============================================="
echo "¡A VENDER! Full Flow Verification Pipeline"
echo "==============================================="

echo "1. Checking Container Availability..."
if ! docker exec avender_sysadmin echo "SysAdmin Container Active"; then
    echo "ERROR: avender_sysadmin container is not running."
    exit 1
fi

echo "2. Installing Verification Tooling inside Container..."
docker exec avender_sysadmin /bin/bash -c "/opt/venv/bin/pip install black ruff pyright pytest pytest-playwright requests"

echo "3. Running Linters (Black, Ruff, Pyright)..."
docker exec avender_sysadmin /bin/bash -c "cd /app/admin && /opt/venv/bin/black tenants/ --check"
docker exec avender_sysadmin /bin/bash -c "cd /app/admin && /opt/venv/bin/ruff check tenants/"
docker exec avender_sysadmin /bin/bash -c "cd /app/admin && /opt/venv/bin/pyright tenants/"

echo "4. Running Backend Tests (Docker Deployment)..."
docker exec avender_sysadmin /bin/bash -c "cd /app/admin && /opt/venv/bin/pytest tenants/test_docker_deployment.py -v"

echo "5. Running E2E Playwright Tests..."
docker exec avender_sysadmin /bin/bash -c "/opt/venv/bin/playwright install chromium"
docker exec avender_sysadmin /bin/bash -c "cd /app/admin && /opt/venv/bin/pytest tenants/tests/e2e/test_sysadmin.py -v"

echo "==============================================="
echo "Pipeline Execution Complete: ALL TESTS PASSED."
echo "==============================================="
