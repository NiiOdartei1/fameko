@echo off
REM Start all services for DELIVERY_SYSTEM_STANDALONE

echo ========================================
echo Starting DELIVERY_SYSTEM_STANDALONE Services
echo ========================================

REM 1. Start Flask Backend
echo.
echo [1/3] Starting Flask Backend...
start "Flask Backend" cmd /k "cd /d C:\Users\lampt\Desktop\PROGRAMMING\DELIVERY_SYSTEM_STANDALONE && python app.py"

REM Wait a moment for Flask to start
timeout /t 3 /nobreak > nul

REM 2. Start Go Location Service
echo.
echo [2/3] Starting Go Location Service...
start "Location Service" cmd /k "cd /d C:\Users\lampt\Desktop\PROGRAMMING\DELIVERY_SYSTEM_STANDALONE && start_location_service.bat"

REM Wait a moment for Location Service to start
timeout /t 3 /nobreak > nul

REM 3. Start Go Routing Service
echo.
echo [3/3] Starting Go Routing Service...
start "Routing Service" cmd /k "cd /d C:\Users\lampt\Desktop\PROGRAMMING\DELIVERY_SYSTEM_STANDALONE && start_routing_service.bat"

echo.
echo ========================================
echo All services started successfully!
echo ========================================
echo.
echo Access Points:
echo Flask Backend:     http://localhost:5000
echo Location Service:   ws://localhost:5001/ws/monitor
echo Routing Service:    http://localhost:8012/route
echo.
echo Press any key to exit...
pause > nul
