@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo   LifeLens Environment Bootstrap
echo ========================================
echo.

REM Detect Python launcher or python executable
set "PYTHON_CMD="
where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python 3.8+ is not installed or not available in PATH.
        echo Install Python from https://www.python.org/downloads/
        exit /b 1
    )
    set "PYTHON_CMD=python"
)

REM Create virtual environment if needed
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
)

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

REM Install dependencies on first run
if not exist ".venv\.lifelens_bootstrap_done" (
    echo Installing dependencies. This may take a few minutes...
    "%VENV_PYTHON%" -m pip install --upgrade pip
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to upgrade pip.
        exit /b 1
    )

    "%VENV_PYTHON%" -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install requirements.
        exit /b 1
    )

    type nul > ".venv\.lifelens_bootstrap_done"
)

REM Seed env files if missing
if not exist ".env" (
    if exist ".env.example" (
        copy /Y ".env.example" ".env" > nul
        echo Created .env from .env.example
    ) else (
        echo [WARN] .env is missing and no .env.example was found.
    )
)

if not exist "lifelens\.env" (
    if exist ".env" (
        copy /Y ".env" "lifelens\.env" > nul
        echo Created lifelens\.env from root .env
    ) else if exist "lifelens\.env.example" (
        copy /Y "lifelens\.env.example" "lifelens\.env" > nul
        echo Created lifelens\.env from lifelens\.env.example
    ) else (
        echo [WARN] lifelens\.env is missing.
    )
)

echo Bootstrap complete.
exit /b 0
