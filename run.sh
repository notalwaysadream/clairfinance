#!/usr/bin/env bash
# Clairfinance Startup Script
# Boots both FastAPI backend (port 8000) and Frontend (port 3000), seeds datasets, and opens the browser.

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"
DATA_DIR="$ROOT_DIR/data"

echo "=================================================="
echo "🏦 Launching Clairfinance Operating System"
echo "Root directory: $ROOT_DIR"
echo "=================================================="

# 1. Verify python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed or not in PATH."
    exit 1
fi

# 2. Virtual Environment & Dependencies
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment at backend/venv..."
    python3 -m venv "$VENV_DIR"
    echo "📦 Installing backend dependencies..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
    else
        echo "requirements.txt not found. Installing packages..."
        "$VENV_DIR/bin/pip" install fastapi "uvicorn[standard]" sqlalchemy aiosqlite \
            python-multipart pydantic python-dotenv pandas numpy scipy scikit-learn \
            httpx "python-jose[cryptography]" passlib greenlet google-genai
    fi
fi

# 3. Generate synthetic datasets if needed
if [ ! -f "$DATA_DIR/salaried_transactions.csv" ] || [ ! -f "$DATA_DIR/freelancer_transactions.csv" ] || [ ! -f "$DATA_DIR/student_transactions.csv" ]; then
    echo "📊 Generating synthetic 12-month test statement datasets..."
    "$VENV_DIR/bin/python3" "$ROOT_DIR/scripts/generate_test_data.py" --persona all --output-dir "$DATA_DIR"
fi

# 4. Environment config
if [ ! -f "$BACKEND_DIR/.env" ] && [ -f "$BACKEND_DIR/.env.example" ]; then
    echo "⚙️ Creating backend/.env from .env.example..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

# 5. Pre-seed DB Personas
echo "🌱 Ensuring database and test personas (Salaried, Freelancer, Student) are seeded..."
"$VENV_DIR/bin/python3" "$ROOT_DIR/scripts/init_db.py"

# 6. Process Cleanup Handler for Ctrl+C
cleanup() {
    echo ""
    echo "🛑 Shutting down Clairfinance (backend & frontend)..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait "$BACKEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
    echo "✅ Clairfinance processes stopped cleanly. Goodbye!"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 6.5 Free ports 8000 and 3000 if already occupied by lingering processes
for PORT in 8000 3000; do
    PIDS=$(lsof -ti :$PORT 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "🧹 Port $PORT is already in use by PID(s): $PIDS. Freeing port..."
        kill -9 $PIDS 2>/dev/null || true
    fi
done
sleep 0.5

# 7. Start FastAPI Backend on Port 8000
echo "🚀 Starting FastAPI Backend on http://localhost:8000..."
cd "$BACKEND_DIR"
"$VENV_DIR/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 8. Start Frontend Web Server on Port 3000
echo "🎨 Starting Frontend Server on http://localhost:3000..."
cd "$ROOT_DIR"
python3 "$ROOT_DIR/scripts/serve_frontend.py" 3000 "$FRONTEND_DIR" > /dev/null 2>&1 &
FRONTEND_PID=$!

# 9. Wait for Backend to become healthy
"$VENV_DIR/bin/python3" "$ROOT_DIR/scripts/wait_for_backend.py" "http://localhost:8000/api/health"

# 10. Open Web Browser
TARGET_URL="http://localhost:3000"
echo "🌐 Opening web browser at $TARGET_URL..."
if command -v open &> /dev/null; then
    open "$TARGET_URL" 2>/dev/null || true
elif command -v xdg-open &> /dev/null; then
    xdg-open "$TARGET_URL" 2>/dev/null || true
else
    python3 -m webbrowser "$TARGET_URL" 2>/dev/null || true
fi

echo "=================================================="
echo "✨ Clairfinance is LIVE!"
echo "=================================================="
echo "💻 Frontend App:     http://localhost:3000"
echo "⚙️ Backend API:      http://localhost:8000"
echo "📖 Swagger API Docs: http://localhost:8000/docs"
echo "🔍 Health Check:     http://localhost:8000/api/health"
echo ""
echo "👥 Available Personas for Demo Testing:"
echo "   1. Salaried Employee: Rahul Sharma (Fixed monthly salary, car loan EMI, rent)"
echo "   2. Freelancer:        Priya Patel  (Irregular client invoices, subscriptions)"
echo "   3. Student:           Amit Verma   (Allowance, mess fees, semester fee spikes)"
echo "=================================================="
echo "Press Ctrl+C at any time to shut down both servers."
echo "=================================================="

# Wait for background servers
wait "$BACKEND_PID" "$FRONTEND_PID"
