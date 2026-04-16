# Delivery System Standalone

A complete, production-ready delivery management system with driver management, real-time location tracking, route optimization, and earnings management.

**Version:** 1.0.0  
**Created:** March 2026  
**Based on:** PanaQet Marketplace Delivery System

## Overview

This is a standalone delivery system that includes:
- **Driver Management**: Registration, approval, status tracking
- **Order & Delivery Management**: Order creation, delivery assignment, status tracking
- **Real-time Location Tracking**: WebSocket-based live driver location with GPS accuracy
- **Route Calculation**: FastAPI microservice for route optimization
- **Earnings Management**: Bolt-like commission model with wallet system
- **Admin Dashboard**: System monitoring and reporting
- **Customer Tracking**: Real-time delivery tracking for customers

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Layers                               │
├──────────────────┬──────────────────┬──────────────────┐
│  Driver Frontend │ Customer Frontend │ Admin Dashboard  │
│     (SocketIO)   │  (SocketIO)      │                  │
└──────────────────┴──────────────────┴──────────────────┘
          ↓                 ↓                    ↓
┌─────────────────────────────────────────────────────────────┐
│              Flask Application (Port 5000)                   │
│  ├─ /driver    - Driver routes & APIs                        │
│  ├─ /customer  - Customer order & tracking                   │
│  ├─ /admin     - Admin management                            │
│  └─ /api       - Public API endpoints                        │
└─────────────────────────────────────────────────────────────┘
      ↓                    ↓                        ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ SQLite Database  │  │ FastAPI Routing  │  │ Live Location    │
│ (Port 5000)      │  │ Service (Port    │  │ Service (Port    │
│                  │  │ 8010)            │  │ 5001)            │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Technology Stack

- **Backend**: Flask 2.3, SQLAlchemy 2.0
- **Routing Service**: FastAPI 0.103, Uvicorn
- **Real-time**: Flask-SocketIO, WebSocket
- **Database**: SQLite (production: PostgreSQL)
- **Live Location**: Go + Gorilla WebSocket (optional)
- **Task Queue**: Python threading
- **Deployment**: Gunicorn + Nginx

## Installation

### Prerequisites
- Python 3.8+
- Go 1.19+ (for live location service)
- Git
- Virtual environment manager (venv, conda)

### Step 1: Clone/Download

```bash
cd C:\Users\lampt\Desktop\PROGRAMMING
git clone <repo-url> DELIVERY_SYSTEM_STANDALONE
cd DELIVERY_SYSTEM_STANDALONE
```

### Step 2: Create Virtual Environment

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Initialize Database

```bash
python
>>> from app import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

Or use Flask CLI:
```bash
flask init-database
flask create-admin  # Create first admin user
```

### Step 5: Environment Configuration

Create `.env` file in root directory:

```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your_secret_key_here_change_in_production
DEBUG=True

# Database
SQLALCHEMY_DATABASE_URI=sqlite:///delivery_system.db

# Services
ROUTING_SERVICE_URL=http://localhost:8010
LIVE_LOCATION_SERVICE_URL=http://localhost:5001

# Security
GOOGLE_MAPS_API_KEY=your_api_key_here

# Email (Optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
```

## Running the System

### Option 1: Run All Services Together (Development)

**Terminal 1 - Flask App:**
```bash
python app.py
```
Flask app runs on http://localhost:5000

**Terminal 2 - Routing Service:**
```bash
python routing_service.py
```
Routing service runs on http://localhost:8010

**Terminal 3 - Live Location Service (Go):**
```bash
# First time: install dependencies
go mod init delivery-location-service
go get github.com/gorilla/websocket

# Run service
go run live_location_service.go
```
Live location service runs on http://localhost:5001

### Option 2: Run Flask App Only

If you only want the main Flask app without separate microservices:

```bash
python app.py
```

The app will still work but will use fallback mock routing and location services.

### Option 3: Production Deployment

**Flask App with Gunicorn:**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

**Routing Service with Uvicorn:**
```bash
uvicorn routing_service:app --host 0.0.0.0 --port 8010 --workers 4
```

**Live Location Service (Go):**
```bash
go run live_location_service.go
```

## API Model: Bolt-like Commission System

### Driver Earnings Calculation

```
Base Fare: $5.00 (configurable, can vary by distance/time)
Platform Commission: 25% (configurable)
Driver Commission: 75% of base fare
Peak Multiplier: 1.5x during rush hours

Driver Earnings = (Base Fare × Driver Commission %) + Tips + Bonuses - Wait Time Fee
Platform Revenue = (Base Fare × Platform Commission %) + Cancellation Fees
```

**Example:**
```
Base Fare:             $10.00
Peak Multiplier:       1.5x → $15.00
Platform Commission:   25% → $3.75
Driver Commission:     75% × $15.00 = $11.25
Customer Tips:         $2.00 → Driver gets
───────────────────────
Driver Earnings:       $13.25
Platform Revenue:      $3.75 + fees
```

## Database Models

### Core Models

1. **Driver** - Driver accounts with earnings tracking
   - Authentication (email/password)
   - Vehicle information
   - Earnings & statistics
   - Rating system
   - Commission rate

2. **Delivery** - Individual delivery records
   - Order reference
   - Pickup/dropoff locations
   - Route coordinates
   - Pricing & commission breakdown
   - Status tracking

3. **Order** - Customer orders
   - Multiple items
   - Shipping address
   - Payment method
   - Multiple deliveries

4. **Customer** - Buyer/customer accounts
   - Profile information
   - Orders history
   - Default addresses

5. **Admin** - Admin accounts
   - Permissions (drivers, orders, analytics)

6. **Wallet** - Driver earnings wallet
   - Balance tracking
   - Transaction history
   - Commission storage

## API Documentation

### Driver Endpoints

**Authentication:**
- `POST /driver/register` - Register driver
- `POST /driver/login` - Login driver
- `POST /driver/logout` - Logout

**Location:**
- `POST /driver/location/update` - Update driver location (real-time)
- `GET /driver/location` - Get current location
- `GET /driver/locations/all` - Get all online drivers

**Deliveries:**
- `GET /driver/deliveries` - Get driver's deliveries
- `GET /driver/deliveries/available` - Get unassigned deliveries
- `POST /driver/deliveries/<id>/accept` - Accept delivery
- `POST /driver/deliveries/<id>/start` - Start delivery
- `POST /driver/deliveries/<id>/complete` - Complete delivery

**Earnings:**
- `GET /driver/earnings` - Get earnings summary
- `GET /driver/wallet` - Get wallet details

### Customer Endpoints

**Authentication:**
- `POST /customer/register` - Register customer
- `POST /customer/login` - Login customer
- `POST /customer/logout` - Logout

**Orders:**
- `POST /customer/orders` - Create new order
- `GET /customer/orders` - Get customer's orders
- `GET /customer/orders/<id>` - Get order details

**Tracking:**
- `GET /customer/track/<delivery_id>` - Real-time delivery tracking

### Admin Endpoints

**Drivers:**
- `GET /admin/drivers` - List all drivers
- `POST /admin/drivers/<id>/approve` - Approve driver
- `POST /admin/drivers/<id>/suspend` - Suspend driver

**Orders:**
- `GET /admin/orders` - List all orders
- `GET /admin/deliveries` - List all deliveries

**Analytics:**
- `GET /admin/analytics` - System analytics

### Routing Service Endpoints

**Route Calculation:**
- `POST /route` - Calculate route between two points
  ```json
  {
    "pickup_lat": 5.6037,
    "pickup_lng": -0.1869,
    "dropoff_lat": 5.5580,
    "dropoff_lng": -0.2077,
    "alternatives": 3
  }
  ```

**Geocoding:**
- `POST /geocode` - Address to coordinates

**Cache:**
- `GET /cache/stats` - Cache statistics
- `DELETE /cache` - Clear cache

**Health:**
- `GET /health` - Health check

### Live Location Service (WebSocket)

**Driver Connection:**
```javascript
ws = new WebSocket("ws://localhost:5001/ws/driver?driver_id=123");
ws.send(JSON.stringify({
  "driver_id": 123,
  "lat": 5.6037,
  "lng": -0.1869,
  "delivery_id": 1
}));
```

**Monitor Connection:**
```javascript
monitor = new WebSocket("ws://localhost:5001/ws/monitor");
monitor.onmessage = (event) => {
  const location = JSON.parse(event.data);
  console.log("Driver", location.driver_id, "at", location.lat, location.lng);
};
```

## File Structure

```
DELIVERY_SYSTEM_STANDALONE/
├── app.py                      # Flask application factory & initialization
├── config.py                   # Configuration management
├── database.py                 # SQLAlchemy database setup
├── extensions.py               # Flask extensions
├── models.py                   # SQLAlchemy models (Order, Delivery, Driver, etc.)
│
├── driver_routes.py            # Driver authentication & delivery APIs
├── customer_routes.py          # Customer order & tracking APIs
├── admin_routes.py             # Admin management & analytics
├── api_routes.py               # Public API endpoints
│
├── routing_service.py          # FastAPI routing microservice
├── live_location_service.go    # Go WebSocket live location service
│
├── templates/                  # HTML templates
│   ├── base.html
│   ├── driver/
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   └── delivery_tracking.html
│   ├── customer/
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   └── track_delivery.html
│   └── admin/
│       ├── dashboard.html
│       ├── drivers.html
│       └── analytics.html
│
├── static/                     # Static files
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── map.js
│   │   └── tracking.js
│   └── images/
│
├── uploads/                    # User uploaded files
├── cache/                      # Routing cache
│
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (create locally)
├── .gitignore                  # Git ignore file
└── README.md                   # This file
```

## Configuration

### Environment Variables

See `.env` file. Key variables:

```env
FLASK_ENV              # development, production, testing
DEBUG                  # True/False
SECRET_KEY            # Random secret for sessions
ROUTING_SERVICE_URL   # FastAPI routing service URL
LIVE_LOCATION_SERVICE_URL  # Go location service URL
GOOGLE_MAPS_API_KEY   # For geocoding (optional)
```

### Config Classes

- **DevelopmentConfig**: Debug enabled, SQLite
- **ProductionConfig**: Debug disabled, environment variables required
- **TestingConfig**: In-memory SQLite

## Development Workflow

### 1. Start Services (3 terminals)

**Terminal 1:**
```bash
python app.py
```

**Terminal 2:**
```bash
python routing_service.py
```

**Terminal 3:**
```bash
go run live_location_service.go
```

### 2. Test Driver Flow

1. Register driver: `POST http://localhost:5000/driver/register`
   ```json
   {
     "full_name": "John Doe",
     "email": "john@example.com",
     "phone": "+1234567890",
     "license_number": "DL123456",
     "vehicle_type": "Car",
     "vehicle_number": "ABC-123",
     "password": "securepass"
   }
   ```

2. Admin approves: `POST /admin/drivers/1/approve`

3. Login driver: `POST /driver/login`
   ```json
   {
     "email": "john@example.com",
     "password": "securepass"
   }
   ```

4. Get available deliveries: `GET /driver/deliveries/available`

5. Accept delivery: `POST /driver/deliveries/1/accept`

6. Update location: `POST /driver/location/update`
   ```json
   {
     "lat": 5.6037,
     "lng": -0.1869,
     "delivery_id": 1
   }
   ```

7. Start delivery: `POST /driver/deliveries/1/start`

8. Complete delivery: `POST /driver/deliveries/1/complete`

### 3. Test Customer Flow

1. Register customer: `POST /customer/register`

2. Create order: `POST /customer/orders`
   ```json
   {
     "total_amount": 50.00,
     "shipping_name": "Jane Smith",
     "shipping_address": "123 Main St",
     "shipping_phone": "+1234567890",
     "latitude": 5.5580,
     "longitude": -0.2077,
     "payment_method": "Cash on Delivery",
     "items": [
       {
         "name": "Item 1",
         "quantity": 2,
         "price": 10.00
       }
     ]
   }
   ```

3. Track delivery: `GET /customer/track/1`

## Testing

### Unit Tests

```bash
pytest tests/ -v
```

### API Testing

Use Postman or curl:

```bash
# Health check
curl http://localhost:5000/health

# Routing service
curl -X POST http://localhost:8010/route \
  -H "Content-Type: application/json" \
  -d '{"pickup_lat": 5.6037, "pickup_lng": -0.1869, "dropoff_lat": 5.5580, "dropoff_lng": -0.2077}'

# Live location service
curl http://localhost:5001/health
```

### Load Testing

```python
# Use locust for load testing
pip install locust
locust -f tests/locustfile.py
```

## Performance Considerations

1. **Database Indexing**: Ensure indexes on frequently queried columns
   - `drivers.email`, `orders.customer_id`, `deliveries.status`

2. **Caching**: Routes cached for 1 hour (5000 entries max)

3. **WebSocket Pools**: Monitor concurrent WebSocket connections

4. **Async Operations**: Location updates non-blocking

## Security Best Practices

1. **Environment Variables**: Never commit secrets to git
2. **CORS**: Configure properly for production
3. **SQL Injection**: SQLAlchemy ORM prevents injection
4. **Password Hashing**: Uses werkzeug.security
5. **HTTPS**: Use SSL certificates in production
6. **Rate Limiting**: Implement on production APIs
7. **Input Validation**: WTForms validates all inputs

## Troubleshooting

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :5000
kill -9 <PID>
```

### Database Locked

```bash
# Delete and recreate
rm delivery_system.db
python -c "from app import *; init_db(app)"
```

### Location Service Connection Failed

Ensure all three services are running and accessible:
```bash
curl http://localhost:5000/health
curl http://localhost:8010/health
curl http://localhost:5001/health
```

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]
```

### Docker Compose

See `docker-compose.yml` for multi-container setup.

### Kubernetes

Helm charts available in `k8s/` directory.

## Monitoring

### Logs

```bash
# Tail logs
tail -f logs/delivery_system.log

# Filter errors
grep ERROR logs/delivery_system.log
```

### Metrics

Access admin dashboard:
- `/admin/dashboard` - System overview
- `/admin/analytics` - Revenue & delivery metrics

### Health Checks

```bash
curl http://localhost:5000/health
curl http://localhost:8010/health
curl http://localhost:5001/health
```

## Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push branch: `git push origin feature/name`
5. Submit pull request

## License

Proprietary - All rights reserved

## Support

- Documentation: See README files in each module
- Issues: Create issue in repository
- Email: support@delivery-system.com

## Version History

### v1.0.0 (March 2026)
- Initial release
- Driver management
- Real-time location tracking
- Route optimization
- Earnings management
- Admin dashboard

## Roadmap

- [ ] Mobile app (iOS/Android)
- [ ] Analytics improvements
- [ ] Notification system (push/SMS)
- [ ] Automated testing
- [ ] Multi-language support
- [ ] Payment integration
- [ ] Advanced clustering algorithm
- [ ] ML-based demand prediction

---

**Last Updated:** March 16, 2026  
**Created by:** Delivery System Development Team  
**Repository:** [GitHub URL]
