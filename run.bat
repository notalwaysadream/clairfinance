@echo off
setlocal enabledelayedexpansion

REM ================================================================
REM ClaireFinance Windows Startup Script
REM Boots both FastAPI backend (port 8000) and Frontend (port 3000),
REM seeds datasets, installs requirements, and opens the browser.
REM ================================================================

title ClaireFinance Runner

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "VENV_DIR=%BACKEND_DIR%\venv"
set "DATA_DIR=%ROOT_DIR%data"

echo ==================================================
echo 🏦 Launching ClaireFinance Operating System (Windows)
echo Root directory: %ROOT_DIR%
echo ==================================================

REM 1. Detect Python
set "PY_CMD="
python -c "import sys; sys.exit(0)" >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=python"
) else (
    py -3 -c "import sys; sys.exit(0)" >nul 2>&1
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

REM 2. Clean invalid Unix/Mac venv if copied across platforms
if exist "%VENV_DIR%" (
    if not exist "%VENV_DIR%\Scripts\python.exe" (
        echo ⚠️ Detected non-Windows virtual environment. Cleaning up for Windows rebuild...
        rmdir /s /q "%VENV_DIR%"
    )
)

REM 3. Create virtual environment if missing
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo 📦 Creating virtual environment at backend\venv...
    %PY_CMD% -m venv "%VENV_DIR%"
    if !errorlevel! neq 0 (
        echo ❌ Error creating virtual environment.
        pause
        exit /b 1
    )
    echo 📦 Upgrading pip...
    "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
)

REM 4. Verify / Install Dependencies
"%VENV_DIR%\Scripts\python.exe" -c "import fastapi, uvicorn, sqlalchemy, pandas, sklearn" >nul 2>&1
if !errorlevel! neq 0 (
    echo 📦 Installing backend dependencies...
    if exist "%BACKEND_DIR%\requirements.txt" (
        echo Installing from requirements.txt...
        "%VENV_DIR%\Scripts\pip.exe" install -r "%BACKEND_DIR%\requirements.txt"
        if !errorlevel! neq 0 (
            echo ⚠️ Some pinned dependencies could not be installed. Falling back to core packages...
            "%VENV_DIR%\Scripts\pip.exe" install fastapi "uvicorn[standard]" sqlalchemy aiosqlite python-multipart pydantic python-dotenv pandas numpy scipy scikit-learn httpx "python-jose[cryptography]" passlib greenlet google-genai
        )
    ) else (
        echo requirements.txt not found. Installing core packages...
        "%VENV_DIR%\Scripts\pip.exe" install fastapi "uvicorn[standard]" sqlalchemy aiosqlite python-multipart pydantic python-dotenv pandas numpy scipy scikit-learn httpx "python-jose[cryptography]" passlib greenlet google-genai
    )
)

REM 5. Generate test statement datasets if missing
if not exist "%DATA_DIR%\salaried_transactions.csv" (
    echo 📊 Generating synthetic 12-month test statement datasets...
    "%VENV_DIR%\Scripts\python.exe" "%ROOT_DIR%scripts\generate_test_data.py" --persona all --output-dir "%DATA_DIR%"
)

REM 6. Environment config
if not exist "%BACKEND_DIR%\.env" (
    if exist "%BACKEND_DIR%\.env.example" (
        echo ⚙️ Creating backend\.env from .env.example...
        copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
    )
)

REM 7. Initialize Database and Seed Personas
echo 🌱 Ensuring database and test personas are seeded...
"%VENV_DIR%\Scripts\python.exe" "%ROOT_DIR%scripts\init_db.py"

REM 7.5 Ensure ports 8000 and 3000 are free
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM 8. Start FastAPI Backend (Port 8000)
echo 🚀 Starting FastAPI Backend on http://localhost:8000...
start "ClaireFinance Backend (Port 8000)" cmd /k "cd /d "%BACKEND_DIR%" && set PYTHONPATH=%BACKEND_DIR% && "%VENV_DIR%\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

REM 9. Start Frontend Web Server (Port 3000)
echo 🎨 Starting Frontend Server on http://localhost:3000...
start "ClaireFinance Frontend (Port 3000)" cmd /k "cd /d "%ROOT_DIR%" && "%VENV_DIR%\Scripts\python.exe" "%ROOT_DIR%scripts\serve_frontend.py" 3000 "%FRONTEND_DIR%""

REM 10. Wait for Backend to become healthy before opening browser
echo ⏳ Waiting for backend health check...
"%VENV_DIR%\Scripts\python.exe" "%ROOT_DIR%scripts\wait_for_backend.py" "http://127.0.0.1:8000/api/health"

REM 11. Open Web Browser
set "TARGET_URL=http://localhost:3000"
echo 🌐 Opening web browser at %TARGET_URL%...
start %TARGET_URL%

echo ==================================================
echo ✨ ClaireFinance is LIVE!
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

echo 🛑 Stopping ClaireFinance services...
taskkill /FI "WINDOWTITLE eq ClaireFinance Backend (Port 8000)*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ClaireFinance Frontend (Port 3000)*" /F >nul 2>&1

REM Also free up ports 8000 and 3000 if still held
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :8000') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :3000') do taskkill /F /PID %%a >nul 2>&1

echo ✅ ClaireFinance stopped cleanly. Goodbye!
exit /b 0
