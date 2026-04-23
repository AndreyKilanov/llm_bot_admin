#!/bin/sh
set -e

cd -- "$(dirname -- "$0")"

export PYTHONPATH="${PYTHONPATH}:."
export TORTOISE_ORM="src.database.config.CONFIG"

echo "Running database migrations..."

if [ ! -f "pyproject.toml" ] || ! grep -q "\[tool.aerich\]" pyproject.toml; then
    echo "Initializing Aerich config..."
    uv run aerich init -t "$TORTOISE_ORM"
fi

if [ ! -d "migrations/models" ] || ! ls migrations/models/*.py 1>/dev/null 2>&1; then
    echo "No migrations found. Creating initial migration and applying..."
    rm -rf migrations/*
    uv run aerich init -t "$TORTOISE_ORM"
    uv run aerich init-db
else
    echo "Migrations exist. Syncing database with existing files..."
    uv run aerich upgrade || echo "Database already contains all existing migrations or a non-critical error occurred."

    echo "Checking for model changes..."
    MIGRATE_OUT=$(uv run aerich migrate 2>&1 || true)
    
    if echo "$MIGRATE_OUT" | grep -q "No changes detected"; then
        echo "No model changes detected. Skipping."
    else
        echo "$MIGRATE_OUT"
        echo "Model changes detected. Creating and applying new migration..."
        uv run aerich upgrade
    fi
fi

echo "Creating superuser..."
uv run python scripts/create_superuser.py

echo "Starting app..."
exec uv run python -m src.main