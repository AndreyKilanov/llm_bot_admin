#!/bin/sh
set -e

cd -- "$(dirname -- "$0")"

export PYTHONPATH="${PYTHONPATH}:."
export TORTOISE_ORM="src.database.config.CONFIG"

echo "Running migrations..."

if [ ! -f "pyproject.toml" ] || ! grep -q "aerich" pyproject.toml; then
    echo "Initializing Aerich config..."
    aerich init -t "$TORTOISE_ORM"
fi

if [ ! -d "migrations/models" ] || [ -z "$(ls -A migrations/models)" ]; then
    echo "No migrations found. Initializing database and creating initial migration..."
    aerich init-db
else
    echo "Migrations exist. Checking for model changes and applying pending migrations..."
    aerich migrate --name "auto_$(date +%Y%m%d_%H%M%S)" || echo "No model changes detected."
    aerich upgrade
fi

echo "Creating superuser..."
python scripts/create_superuser.py

echo "Starting app (webhook)..."
exec python -m src.main