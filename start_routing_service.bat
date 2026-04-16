@echo off
REM Start Go routing service

echo Building Go routing service...
cd /d "C:\Users\lampt\Desktop\PROGRAMMING\DELIVERY_SYSTEM_STANDALONE"

REM Compile Go service
go build -o routing_service_go.exe routing_service_go.go

if errorlevel 1 (
    echo Failed to build Go routing service
    exit /b 1
)

echo Go routing service built successfully
echo Starting Go routing service on port 8012...

REM Run Go service
routing_service_go.exe

pause
