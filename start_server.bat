@echo off
echo ========================================
echo Starting Attendance System Server
echo ========================================
echo.

cd /d "%~dp0"

echo Activating Python environment...
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found!
    echo Using system Python...
)

echo Starting Flask server...
echo.
echo The server will be accessible at:
echo   - Local: http://localhost:5000
echo   - Network: http://[YOUR-IP]:5000
echo.
echo Clients can connect from other devices using the network address.
echo Press Ctrl+C to stop the server.
echo.
echo ========================================

python server.py

pause
