# Routing Service Deployment on Render

This document explains how to deploy the routing service as a separate Render service to enable full routing functionality like localhost development.

## Overview

The routing service (`routing_service.py`) is a FastAPI application that provides:
- Real-road routing using GraphML files
- WebSocket connections for real-time location updates
- Route calculation and optimization

## Deployment Steps

### 1. Create a New Render Service

1. Go to your Render dashboard
2. Click "New +" → "Web Service"
3. Connect to the same GitHub repository (NiiOdartei1/fameko)
4. Configure the service:

**Build & Deploy Settings:**
- **Root Directory:** Leave empty (uses repository root)
- **Build Command:** `pip install -r requirements_routing.txt`
- **Start Command:** `uvicorn routing_service:app --host 0.0.0.0 --port $PORT`

**Environment Variables:**
- No additional environment variables needed for the routing service

### 2. Update Main App Environment Variables

After the routing service is deployed, add these environment variables to your main app:

- **ROUTING_SERVICE_URL:** `wss://your-routing-service-url.onrender.com`
- **ROUTING_SERVICE_HTTP_URL:** `https://your-routing-service-url.onrender.com`

Replace `your-routing-service-url` with the actual URL of your routing service (shown in Render dashboard after deployment).

### 3. Redeploy Main App

After updating environment variables, trigger a new deployment of the main app to apply the changes.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Main App     │         │  Routing Service │         │   GraphML Files │
│   (Flask)      │◄───────►│  (FastAPI)       │◄───────►│   (Google Drive)│
│   Port 10000   │  HTTP/  │   Port $PORT     │         │                 │
└─────────────────┘  WS     └──────────────────┘         └─────────────────┘
```

## Testing

After deployment:
1. Access the routing service health check: `https://your-routing-service-url.onrender.com/`
2. Test the main app driver map to verify routing service connectivity
3. Check browser console for successful WebSocket connections

## Notes

- The routing service will automatically download GraphML files from Google Drive on startup
- Both services will be on the free Render tier
- The routing service uses the same Google Drive credentials as the main app
