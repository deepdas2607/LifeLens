@echo off
echo ========================================
echo   Mood Intelligence Monitoring Service
echo ========================================
echo.
echo Starting scheduled mood analysis...
echo.
echo This service will:
echo - Analyze mood patterns for all patients
echo - Detect mood risk signals
echo - Generate alerts via ntfy.sh
echo - Run the multi-agent mood intelligence system
echo.
echo Notifications will be sent to:
echo https://ntfy.sh/lifelens-mood-test_patient_mood_demo
echo.
echo Press Ctrl+C to stop the service
echo.

cd /d "%~dp0"

python lifelens\scripts\scheduled_mood_analysis.py

pause
