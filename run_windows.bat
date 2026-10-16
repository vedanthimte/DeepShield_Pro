@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo DeepShield Pro - native Windows setup
echo No Docker required
echo ============================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.11+ from python.org and retry.
  pause
  exit /b 1
)
if not exist .venv py -3.11 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
start "DeepShield API" cmd /k "call .venv\Scripts\activate && uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"
cd frontend
call npm install
call npm run dev
