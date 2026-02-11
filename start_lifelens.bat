@echo off
echo ========================================
echo    LifeLens - Complete System Startup
echo ========================================
echo.
echo Starting API Server and Streamlit App...
echo.
echo API Server: http://localhost:8000
echo Streamlit App: http://localhost:8501
echo.
echo Both services will run in parallel.
echo Close this window to stop both services.
echo.
pause

cd /d "%~dp0\lifelens"

REM Start API server in background
start "LifeLens API" cmd /k "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

REM Wait 3 seconds for API to start
timeout /t 3 /nobreak > nul

REM Start Streamlit app
start "LifeLens Streamlit" cmd /k "streamlit run app.py"

echo.
echo Both services are now running!
echo.
echo To use the browser extension:
echo 1. Load extension in Chrome/Edge (chrome://extensions)
echo 2. Enable Developer Mode
echo 3. Click "Load unpacked" and select the extension folder
echo 4. Login with your patient credentials
echo.
pause
