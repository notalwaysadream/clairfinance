#!/usr/bin/env bash
# ClairFinance backend startup script

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"
DATA_DIR="$ROOT_DIR/data"

echo "--------------------------------------------------"
echo "Starting ClairFinance backend"
echo "Working directory: $ROOT_DIR"
echo "--------------------------------------------------"

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH."
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at backend/venv..."
    python3 -m venv "$VENV_DIR"
    echo "Installing dependencies..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
    else
        echo "requirements.txt not found. Installing packages..."
        "$VENV_DIR/bin/pip" install fastapi "uvicorn[standard]" sqlalchemy aiosqlite \
            python-multipart pydantic python-dotenv pandas numpy scipy scikit-learn \
            httpx "python-jose[cryptography]" passlib greenlet
    fi
fi

if [ ! -f "$DATA_DIR/salaried_transactions.csv" ]; then
    echo "Generating test data files..."
    "$VENV_DIR/bin/python3" "$ROOT_DIR/scripts/generate_test_data.py" --output-dir "$DATA_DIR"
fi

if [ ! -f "$BACKEND_DIR/.env" ] && [ -f "$BACKEND_DIR/.env.example" ]; then
    echo "Creating backend/.env from .env.example"
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

echo "Backend starting on http://localhost:8000"
echo "Swagger docs available at: http://localhost:8000/docs"
echo "Press Ctrl+C to stop."
echo "--------------------------------------------------"

cd "$BACKEND_DIR"
exec "$VENV_DIR/bin/uvicorn" app.main:app --reload --host 0.0.0.0 --port 8000
