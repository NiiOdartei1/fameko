@echo off
REM Start Go location service

echo Building Go location service...
cd /d "C:\Users\lampt\Desktop\PROGRAMMING\DELIVERY_SYSTEM_STANDALONE"

REM Compile Go service
go build -o location_service.exe location_service\live_location_service.go

if errorlevel 1 (
    echo Failed to build Go location service
    exit /b 1
)

echo Go location service built successfully
echo Starting Go location service on port 5001...

REM Run Go service
location_service.exe

pause
