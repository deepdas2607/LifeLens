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

python lifelens\scripts\medication_scheduler_service.py

pause
