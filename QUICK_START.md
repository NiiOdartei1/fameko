# Quick Start Guide

## 5-Minute Setup

### 1. Create Virtual Environment
```bash
python -m venv venv
.\venv\Scripts\Activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
python
>>> from app import create_app, db
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### 4. Create Admin User
```bash
flask create-admin
# Enter: username, email, password
```

### 5. Run Services (3 terminals)

**Terminal 1 - Flask App (Port 5000):**
```bash
python app.py
```
Visit: http://localhost:5000

**Terminal 2 - Routing Service (Port 8010):**
```bash
python routing_service.py
```

**Terminal 3 - Live Location (Port 5001):**
```bash
go run live_location_service.go
```

## First Time Usage

### Create Driver Account
1. Go to http://localhost:5000/driver/register
2. Fill in form and submit
3. Login to admin dashboard
4. Approve the driver
5. Driver can now login and accept deliveries

### Create Customer Account
1. Go to http://localhost:5000/customer/register
2. Login and create an order
3. Order will be available for drivers to accept

### Admin Dashboard
1. Go to http://localhost:5000/admin/dashboard
2. Default login: admin/admin (set during creation)
3. View all drivers, orders, deliveries
4. Approve/suspend drivers
5. View analytics

## Testing Endpoints

### Create Order
```bash
curl -X POST http://localhost:5000/customer/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "total_amount": 50,
    "shipping_name": "Test",
    "shipping_address": "123 Main St",
    "latitude": 5.6037,
    "longitude": -0.1869
  }'
```

### Get Available Deliveries
```bash
curl http://localhost:5000/driver/deliveries/available \
  -H "Authorization: Bearer <token>"
```

### Update Driver Location
```bash
curl -X POST http://localhost:5000/driver/location/update \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 5.6037,
    "lng": -0.1869,
    "delivery_id": 1
  }'
```

## Common Issues

**Port 5000 in use:**
```bash
# Kill process
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**Database error:**
```bash
# Reset database
rm delivery_system.db
python -c "from app import *; init_db(app)"
```

**Routing service unreachable:**
```bash
# Check if running
curl http://localhost:8010/health
```

## File Structure Overview

```
DELIVERY_SYSTEM_STANDALONE/
├── app.py                 # Main Flask app
├── models.py              # Database models
├── driver_routes.py       # Driver API
├── customer_routes.py     # Customer API
├── admin_routes.py        # Admin API
├── routing_service.py     # FastAPI service
├── live_location_service.go  # Go service
├── config.py              # Configuration
├── database.py            # DB setup
├── requirements.txt       # Dependencies
└── README.md             # Full documentation
```

## Next Steps

1. Read full README.md for detailed documentation
2. Explore templates/ for UI customization
3. Configure .env file for your environment
4. Setup database backup strategy
5. Configure email notifications (optional)
6. Deploy to production (see Deployment section in README)

## Documentation Links

- API Documentation: See API section in README.md
- Database Models: See models.py file
- Configuration: See config.py and Configuration section in README.md
- Development: See Development Workflow in README.md
