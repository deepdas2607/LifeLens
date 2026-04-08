@echo off
echo Starting LifeLens API Server...
echo.
echo API will be available at http://localhost:8000
echo This server handles browser extension requests
echo.

cd /d "%~dp0"
call "%~dp0bootstrap_env.bat"
if %errorlevel% neq 0 (
	echo.
	echo [ERROR] Bootstrap failed.
	pause
	exit /b 1
)

"%~dp0.venv\Scripts\python.exe" -m uvicorn lifelens.api.main:app --host 0.0.0.0 --port 8000 --reload
pause
