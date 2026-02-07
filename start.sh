#!/bin/sh
set -e

cd -- "$(dirname -- "$0")"

export PYTHONPATH="${PYTHONPATH}:."
export TORTOISE_ORM="src.database.config.CONFIG"

echo "Running database migrations..."

if [ ! -f "pyproject.toml" ] || ! grep -q "\[tool.aerich\]" pyproject.toml; then
    echo "Initializing Aerich config..."
    aerich init -t "$TORTOISE_ORM"
fi

if [ ! -d "migrations/models" ] || [ -z "$(ls -A migrations/models 2>/dev/null)" ]; then
    echo "No migrations found. Initializing database with initial schema..."
    aerich init-db
else
    echo "Migrations exist. Checking for model changes..."

    if aerich migrate 2>&1 | grep -q "No changes detected"; then
        echo "No model changes detected. Skipping migration creation."
    else
        echo "New migration created. Applying it..."
        aerich upgrade
    fi
fi

echo "Creating superuser..."
python scripts/create_superuser.py

echo "Starting app..."
exec python -m src.main