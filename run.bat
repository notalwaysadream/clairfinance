@echo off
setlocal enabledelayedexpansion

REM ================================================================
REM ClairFinance Windows Startup Script
REM Boots both FastAPI backend (port 8000) and Frontend (port 3000),
REM seeds datasets, installs requirements, and opens the browser.
REM ================================================================

title ClairFinance Runner

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "VENV_DIR=%BACKEND_DIR%\venv"
set "DATA_DIR=%ROOT_DIR%data"

echo ==================================================
echo 🏦 Launching ClairFinance Operating System (Windows)
echo Root directory: %ROOT_DIR%
echo ==================================================

REM 1. Detect Python
set "PY_CMD="
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=python"
) else (
    py -3 --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=py -3"
    )
)

if "%PY_CMD%"=="" (
    echo ❌ Error: Python 3 was not found in your PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo ✅ Found Python: %PY_CMD%

REM 2. Create virtual environment if missing
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo 📦 Creating virtual environment at backend\venv...
    %PY_CMD% -m venv "%VENV_DIR%"
    if !errorlevel! neq 0 (
        echo ❌ Error creating virtual environment.
        pause
        exit /b 1
    )
    echo 📦 Upgrading pip and installing required dependencies...
    "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
    if exist "%BACKEND_DIR%\requirements.txt" (
        "%VENV_DIR%\Scripts\pip.exe" install -r "%BACKEND_DIR%\requirements.txt"
    ) else (
        echo requirements.txt not found. Installing core packages...
        "%VENV_DIR%\Scripts\pip.exe" install fastapi "uvicorn[standard]" sqlalchemy aiosqlite python-multipart pydantic python-dotenv pandas numpy scipy scikit-learn httpx "python-jose[cryptography]" passlib greenlet google-genai
    )
)

REM 3. Generate test statement datasets if missing
if not exist "%DATA_DIR%\salaried_transactions.csv" (
    echo 📊 Generating synthetic 12-month test statement datasets...
    "%VENV_DIR%\Scripts\python.exe" "%ROOT_DIR%scripts\generate_test_data.py" --persona all --output-dir "%DATA_DIR%"
)

REM 4. Environment config
if not exist "%BACKEND_DIR%\.env" (
    if exist "%BACKEND_DIR%\.env.example" (
        echo ⚙️ Creating backend\.env from .env.example...
        copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
    )
)

REM 5. Pre-seed DB
echo 🌱 Ensuring database and test personas are seeded...
set "PYTHONPATH=%BACKEND_DIR%"
"%VENV_DIR%\Scripts\python.exe" -c "import asyncio; from app.database import AsyncSessionLocal, engine, Base; from app.routers.personas import seed_all_personas; async def init(): async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all); async with AsyncSessionLocal() as session: await seed_all_personas(session); asyncio.run(init())" 2>nul

REM 6. Start FastAPI Backend (Port 8000)
echo 🚀 Starting FastAPI Backend on http://localhost:8000...
start "ClairFinance Backend (Port 8000)" /D "%BACKEND_DIR%" "%VENV_DIR%\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

REM 7. Start Frontend Web Server (Port 3000)
echo 🎨 Starting Frontend Server on http://localhost:3000...
start "ClairFinance Frontend (Port 3000)" /D "%ROOT_DIR%" "%VENV_DIR%\Scripts\python.exe" -m http.server 3000 --directory "%FRONTEND_DIR%"

REM 8. Wait for services and open browser
echo ⏳ Initializing services...
timeout /t 3 /nobreak >nul

set "TARGET_URL=http://localhost:3000"
echo 🌐 Opening web browser at %TARGET_URL%...
start %TARGET_URL%

echo ==================================================
echo ✨ ClairFinance is LIVE!
echo ==================================================
echo 💻 Frontend App:     http://localhost:3000
echo ⚙️ Backend API:      http://localhost:8000
echo 📖 Swagger API Docs: http://localhost:8000/docs
echo 🔍 Health Check:     http://localhost:8000/api/health
echo ==================================================
echo 👥 Available Personas for Demo Testing:
echo    1. Salaried Employee: Rahul Sharma (Fixed monthly salary, car loan EMI, rent)
echo    2. Freelancer:        Priya Patel  (Irregular client invoices, subscriptions)
echo    3. Student:           Amit Verma   (Allowance, mess fees, semester fee spikes)
echo ==================================================
echo NOTE: Both servers are running in background windows.
echo Press any key in this window to stop both servers and exit.
echo ==================================================

pause >nul

echo 🛑 Stopping ClairFinance services...
taskkill /FI "WINDOWTITLE eq ClairFinance Backend (Port 8000)*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ClairFinance Frontend (Port 3000)*" /F >nul 2>&1
echo ✅ ClairFinance stopped cleanly. Goodbye!
exit /b 0
