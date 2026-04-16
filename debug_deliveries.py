#!/usr/bin/env python
"""Debug script to check delivery data"""
from database import db
from app import create_app
from models import Delivery, DeliveryRequest, Order, Driver

app = create_app()
with app.app_context():
    print("=== Database Status ===")
    
    orders = Order.query.all()
    print(f"\nTotal orders: {len(orders)}")
    for order in orders[-5:]:  # Last 5
        print(f"  Order #{order.id}: status={order.status}, customer_id={order.customer_id}, created_at={order.created_at}")
    
    deliveries = Delivery.query.all()
    print(f"\nTotal deliveries: {len(deliveries)}")
    for delivery in deliveries[-5:]:  # Last 5
        print(f"  Delivery #{delivery.id}: order_id={delivery.order_id}, status={delivery.status}, driver_id={delivery.driver_id}")
    
    requests = DeliveryRequest.query.all()
    print(f"\nTotal delivery requests: {len(requests)}")
    for req in requests[-5:]:  # Last 5
        print(f"  Request #{req.id}: driver_id={req.driver_id}, delivery_id={req.delivery_id}, status={req.status}, expires_at={req.expires_at}")
    
    drivers = Driver.query.all()
    print(f"\nTotal drivers: {len(drivers)}")
    for driver in drivers[:3]:
        print(f"  Driver #{driver.id}: {driver.email}, is_online={driver.is_online}")
    
    # Check for pending deliveries with no driver
    pending_unassigned = Delivery.query.filter_by(status='Pending', driver_id=None).all()
    print(f"\nPending unassigned deliveries: {len(pending_unassigned)}")
    for d in pending_unassigned[:3]:
        print(f"  Delivery #{d.id}: {d.pickup_location} -> {d.dropoff_location}")
