@echo off
echo Starting LifeLens API Server...
echo.
echo API will be available at http://localhost:8000
echo This server handles browser extension requests
echo.
cd /d "%~dp0\lifelens"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
pause
