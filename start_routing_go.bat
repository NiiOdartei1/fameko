@echo off
echo ========================================
echo Go Routing Service Launcher
echo ========================================
echo.

echo Starting Go routing service...
echo Service will run on port 8012
echo.

go run routing_service_go.go

echo.
echo Routing service stopped.
pause
