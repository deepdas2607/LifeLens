@echo off
echo Starting LifeLens Medication Scheduler Service...
echo.
echo This service will:
echo - Check for upcoming medication reminders every minute
echo - Monitor for missed doses
echo - Run nightly adherence analytics
echo.
echo Press Ctrl+C to stop the service
echo.

cd /d "%~dp0"

call "%~dp0bootstrap_env.bat"
if %errorlevel% neq 0 (
	echo.
	echo [ERROR] Bootstrap failed.
	pause
	exit /b 1
)

"%~dp0.venv\Scripts\python.exe" lifelens\scripts\medication_scheduler_service.py

pause
