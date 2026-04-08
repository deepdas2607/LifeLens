@echo off
echo ========================================
echo    LifeLens Complete Demo Launcher
echo ========================================
echo.
echo Preparing environment and starting all services...
echo.
echo Services to launch:
echo 1. API Server        (port 8000)
echo 2. Streamlit App     (port 8501)
echo 3. Med Scheduler     (background)
echo.
echo Press any key to continue or Ctrl+C to cancel
pause > nul

cd /d "%~dp0"

call "%~dp0bootstrap_env.bat"
if %errorlevel% neq 0 (
	echo.
	echo [ERROR] Bootstrap failed. Fix the error above and try again.
	pause
	exit /b 1
)

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

REM Start API Server in background
echo.
echo [1/3] Starting API Server...
start "LifeLens API Server" cmd /k cd /d "%~dp0" ^&^& "%VENV_PYTHON%" -m uvicorn lifelens.api.main:app --host 0.0.0.0 --port 8000
timeout /t 3 /nobreak > nul

REM Start Streamlit App in background
echo [2/3] Starting Streamlit App...
start "LifeLens Streamlit" cmd /k cd /d "%~dp0" ^&^& "%VENV_PYTHON%" -m streamlit run lifelens\app.py --server.port 8501
timeout /t 3 /nobreak > nul

REM Start Medication Scheduler in background
echo [3/3] Starting Medication Scheduler...
start "LifeLens Med Scheduler" cmd /k cd /d "%~dp0" ^&^& "%VENV_PYTHON%" lifelens\scripts\medication_scheduler_service.py
timeout /t 2 /nobreak > nul

echo.
echo ========================================
echo    All Services Started!
echo ========================================
echo.
echo ✅ API Server:      http://localhost:8000
echo ✅ Streamlit App:   http://localhost:8501
echo ✅ Med Scheduler:   Running in background
echo.
echo Browser Extension Setup:
echo 1. Open Chrome/Edge
echo 2. Go to chrome://extensions
echo 3. Enable Developer Mode
echo 4. Click 'Load unpacked'
echo 5. Select folder: lifelens/extension
echo 6. Login with: patient1 / patient123
echo.
echo Demo Accounts:
echo   Patient:    patient1  / patient123
echo   Caretaker:  caretaker1 / care123
echo   Family:     family1   / family123
echo.
echo Notifications:
echo   View at: https://ntfy.sh/lifelens-caregiver-alerts
echo.
echo To stop all services: Close all terminal windows
echo.
echo Press any key to open Streamlit in browser...
pause > nul

REM Open Streamlit in default browser
start http://localhost:8501

echo.
echo ========================================
echo    Demo is Ready!
echo ========================================
echo.
echo Quick Demo Flow:
echo 1. Login to Streamlit (patient1/patient123)
echo 2. Upload image, audio, or text memory
echo 3. Use semantic search to find memories
echo 4. Check Medication tracking
echo 5. View Mood analysis
echo 6. Test Browser Extension
echo 7. Login as family to show read-only access
echo.
pause
