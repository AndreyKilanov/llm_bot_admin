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

if [ ! -d "migrations/models" ] || [ -z "$(ls -A migrations/models 2>/dev/null)" ]; then
    echo "No migrations found. Initializing database with initial schema..."
    uv run aerich init-db
else
    echo "Migrations exist. Applying existing migrations..."
    # Применяем все существующие миграции к базе данных
    uv run aerich upgrade || echo "Database might be already up to date or empty."

    echo "Checking for new model changes..."
    if uv run aerich migrate 2>&1 | grep -q "No changes detected"; then
        echo "No model changes detected. Database is up to date."
    else
        echo "New migration created. Applying it..."
        uv run aerich upgrade
    fi
fi

echo "Creating superuser..."
uv run python scripts/create_superuser.py

echo "Starting app..."
exec uv run python -m src.main