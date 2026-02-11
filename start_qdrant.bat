@echo off
echo ========================================
echo   Starting Qdrant Vector Database
echo ========================================
echo.

REM Check if Docker is installed
docker --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed or not in PATH
    echo.
    echo Please install Docker Desktop:
    echo https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)

echo ✅ Docker is installed
echo.
echo Starting Qdrant container...
echo Container name: qdrant_lifelens
echo Port: 6333
echo Data volume: qdrant_storage
echo.

REM Start Qdrant container
docker run -d ^
  --name qdrant_lifelens ^
  -p 6333:6333 ^
  -p 6334:6334 ^
  -v qdrant_storage:/qdrant/storage ^
  qdrant/qdrant:latest

if %errorlevel% equ 0 (
    echo.
    echo ✅ Qdrant started successfully!
    echo.
    echo Qdrant Dashboard: http://localhost:6333/dashboard
    echo API Endpoint: http://localhost:6333
    echo.
    echo To stop Qdrant: docker stop qdrant_lifelens
    echo To restart: docker start qdrant_lifelens
    echo To remove: docker rm -f qdrant_lifelens
) else (
    echo.
    echo ⚠️ Container might already exist. Trying to start existing container...
    docker start qdrant_lifelens
    
    if %errorlevel% equ 0 (
        echo ✅ Existing Qdrant container started!
    ) else (
        echo ❌ Failed to start Qdrant
        echo.
        echo Try removing the old container:
        echo   docker rm -f qdrant_lifelens
        echo Then run this script again
    )
)

echo.
pause
