@echo off
echo =======================================
echo  Retail Insights Engine - Windows Setup
echo =======================================
echo.

REM Check Python version
python --version 2>NUL
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.13.0 from https://python.org
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
.venv\Scripts\pip install --upgrade pip -q
.venv\Scripts\pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    exit /b 1
)

echo.
echo ✓ Dependencies installed.
echo.
echo =======================================
echo  Next steps:
echo =======================================
echo.
echo 1. Copy .env.example to .env:
echo    copy .env.example .env
echo    Then open .env and paste the Neon password from Person A.
echo.
echo 2. Create your local test database (for running pytest):
echo    psql -U postgres -c "CREATE DATABASE retail_insights_test;"
echo.
echo 3. Start the API server:
echo    .venv\Scripts\uvicorn app.main:app --reload --port 8000
echo.
echo 4. Open http://localhost:8000/docs in your browser.
echo.
echo =======================================
echo  Common commands on Windows:
echo =======================================
echo.
echo   Run server:   .venv\Scripts\uvicorn app.main:app --reload --port 8000
echo   Run tests:    .venv\Scripts\pytest -v
echo   Run linter:   .venv\Scripts\ruff check .
echo   Migrations:   .venv\Scripts\alembic upgrade head  (Person A only)
echo.
