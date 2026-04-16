# Routing Service Setup

This project now includes a dedicated routing service for real-time driver tracking, similar to the marketplace implementation.

## Files Added:
- `routing_service_optimized.py` - FastAPI-based routing service
- `start_routing.py` - Launcher script for the routing service
- `routing_config.py` - Configuration for the routing service

## How to Start:

### Option 1: Start Routing Service Separately
```bash
# Terminal 1: Start the routing service
python start_routing.py

# Terminal 2: Start the main Flask application
python app.py
```

### Option 2: Start Routing Service First
1. Run `python start_routing.py` in one terminal
2. Wait for routing service to start (you'll see "Routing service started successfully on port 8011")
3. Run `python app.py` in another terminal

## Routing Service Features:
- **WebSocket Endpoints:**
  - `ws://127.0.0.1:8011/ws/driver/{driver_id}` - Driver connections
  - `ws://127.0.0.1:8011/ws/monitor` - Monitor connections
- **HTTP API:** `http://127.0.0.1:8011` - Route calculations
- **Port:** 8011 (changed from 8010 to avoid conflicts)
- **Cache:** 3600s TTL, 5000 max entries

## Driver Map Integration:
- The driver map now connects to the routing service WebSocket instead of SocketIO
- Real-time location updates via WebSocket
- Fallback to HTTP polling if WebSocket fails
- Error messages guide users if routing service isn't running

## Troubleshooting:
- If WebSocket connection fails, ensure routing service is running on port 8011
- Check for "Routing service started successfully on port 8011" message
- Both services must run simultaneously for full functionality
- If port 8011 is in use, you can change the port by setting the ROUTING_PORT environment variable:
  ```bash
  set ROUTING_PORT=8012
  python start_routing.py
  ```
