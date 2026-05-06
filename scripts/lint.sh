#!/usr/bin/env bash
set -e

echo "Running Black formatting..."
black admin/tenants/

echo "Running Ruff linter..."
ruff check admin/tenants/ --fix

echo "Running Pyright type checking..."
pyright admin/tenants/
