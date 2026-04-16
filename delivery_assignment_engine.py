"""
Delivery Assignment Engine
Automatic driver matching and offer system (Bolt/Uber style)
- Finds nearby available drivers
- Sends simultaneous offers to 3-5 drivers
- Handles timeouts and retries
- Escalates to surge pricing if needed
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from math import radians, cos, sin, asin, sqrt

from database import db
from models import (
    Delivery, DriverLocation, DeliveryRequest, Driver, 
    Notification, Wallet, WalletTransaction, Order
)

logger = logging.getLogger(__name__)


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance in kilometers between two GPS coordinates
    Formula: Haversine distance
    """
    try:
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        
        # Earth's radius in km
        r = 6371
        return c * r
    except Exception as e:
        logger.error(f"Distance calculation error: {e}")
        return float('inf')


def find_nearby_drivers(pickup_lat, pickup_lng, radius_km=5.0, exclude_driver_ids=None, limit=10, driver_region=None):
    """
    Find drivers within radius of pickup location
    
    Args:
        pickup_lat: Pickup latitude
        pickup_lng: Pickup longitude
        radius_km: Search radius (default 5km)
        exclude_driver_ids: List of driver IDs to exclude (already rejected)
        limit: Max drivers to return
        driver_region: Filter to only drivers in this region (strict single-region routing)
    
    Returns:
        List of Driver objects sorted by distance
    """
    try:
        if exclude_driver_ids is None:
            exclude_driver_ids = []
        
        # Get all online drivers with current location
        query = Driver.query.filter(
            Driver.is_online == True,
            Driver.status == 'Approved',
            ~Driver.id.in_(exclude_driver_ids) if exclude_driver_ids else True
        )
        
        # If region is specified, only get drivers in that region
        if driver_region:
            query = query.filter_by(region=driver_region)
            logger.info(f"Filtering drivers for region: {driver_region}")
        
        online_drivers = query.all()
        
        # Calculate distance for each driver
        nearby = []
        for driver in online_drivers:
            loc = DriverLocation.query.filter_by(driver_id=driver.id).first()
            
            if not loc or loc.latitude is None or loc.longitude is None:
                continue
            
            distance = haversine_distance(
                pickup_lat, pickup_lng,
                loc.latitude, loc.longitude
            )
            
            if distance <= radius_km:
                nearby.append({
                    'driver': driver,
                    'distance': distance,
                    'location': loc
                })
        
        # Sort by distance (closest first)
        nearby.sort(key=lambda x: x['distance'])
        
        return [item['driver'] for item in nearby[:limit]]
    
    except Exception as e:
        logger.error(f"Error finding nearby drivers: {e}")
        return []


def send_delivery_offers(delivery_id, num_offers=3):
    """
    Send delivery offers to nearby drivers simultaneously
    - Creates DeliveryRequest records with 60s timeout
    - Sends notifications to drivers
    - Returns list of driver IDs offered
    
    Args:
        delivery_id: Delivery ID to assign
        num_offers: Number of drivers to offer to
    
    Returns:
        List of driver IDs offered, or empty list on failure
    """
    try:
        delivery = db.session.get(Delivery, delivery_id)
        if not delivery:
            logger.warning(f"Delivery {delivery_id} not found")
            return []
        
        # Get pickup coordinates from delivery
        pickup_lat = delivery.pickup_lat
        pickup_lng = delivery.pickup_lng
        
        if not pickup_lat or not pickup_lng:
            logger.warning(f"Delivery {delivery_id} missing pickup coordinates")
            return []
        
        # Find nearby drivers
        exclude_rejected = [
            req.driver_id for req in DeliveryRequest.query.filter_by(
                delivery_id=delivery_id,
                status='Declined'
            ).all()
        ]
        
        nearby_drivers = find_nearby_drivers(
            pickup_lat, pickup_lng,
            radius_km=5.0,
            exclude_driver_ids=exclude_rejected,
            limit=num_offers
        )
        
        if not nearby_drivers:
            logger.warning(f"No nearby drivers found for delivery {delivery_id}")
            return []
        
        # Calculate estimated fare for driver
        base_fare = float(delivery.base_fare) if delivery.base_fare else 5.0
        per_km_rate = float(delivery.per_km_rate) if delivery.per_km_rate else 1.5
        distance = float(delivery.distance_km) if delivery.distance_km else 2.0
        
        driver_commission_percent = delivery.driver_commission_percent or 75.0
        estimated_driver_earnings = (base_fare + (distance * per_km_rate)) * (driver_commission_percent / 100.0)
        
        offered_driver_ids = []
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=60)  # 60-second timeout
        
        # Send offers to each driver
        for driver in nearby_drivers:
            try:
                # Create delivery request record
                delivery_request = DeliveryRequest(
                    delivery_id=delivery_id,
                    driver_id=driver.id,
                    status='Pending',
                    sent_at=now,
                    expires_at=expires_at
                )
                
                db.session.add(delivery_request)
                offered_driver_ids.append(driver.id)
                
                # Log notification for driver (in-app)
                notification = Notification(
                    recipient_id=driver.id,
                    recipient_type='driver',
                    title=f"New Delivery Offer: ₵{estimated_driver_earnings:.2f}",
                    body=f"Pickup: {delivery.pickup_location} → Dropoff: {delivery.dropoff_location}",
                    notification_type='delivery_offer',
                    channels='in-app,push',
                    status='pending',
                    delivery_id=delivery_id,
                    data={
                        'delivery_id': delivery_id,
                        'pickup_location': delivery.pickup_location,
                        'dropoff_location': delivery.dropoff_location,
                        'distance_km': delivery.distance_km,
                        'estimated_fare': float(delivery.base_fare or 5.0),
                        'driver_earnings': estimated_driver_earnings,
                        'expires_in_seconds': 60
                    }
                )
                db.session.add(notification)
                
            except Exception as e:
                logger.error(f"Error sending offer to driver {driver.id}: {e}")
                continue
        
        db.session.commit()
        logger.info(f"Sent delivery {delivery_id} offers to {len(offered_driver_ids)} drivers: {offered_driver_ids}")
        
        return offered_driver_ids
    
    except Exception as e:
        logger.error(f"Error sending delivery offers: {e}")
        db.session.rollback()
        return []


def driver_accept_delivery_offer(driver_id, delivery_request_id):
    """
    Driver accepts a delivery offer
    - Updates DeliveryRequest status to 'Accepted'
    - Assigns Delivery to driver
    - Cancels other pending offers for this delivery
    - Returns True on success
    """
    try:
        delivery_request = db.session.get(DeliveryRequest, delivery_request_id)
        if not delivery_request:
            logger.warning(f"DeliveryRequest {delivery_request_id} not found")
            return False
        
        if delivery_request.driver_id != driver_id:
            logger.warning(f"Driver {driver_id} cannot accept delivery request {delivery_request_id}")
            return False
        
        if delivery_request.status != 'Pending':
            logger.warning(f"DeliveryRequest {delivery_request_id} already {delivery_request.status}")
            return False
        
        delivery_id = delivery_request.delivery_id
        delivery = db.session.get(Delivery, delivery_id)
        
        if not delivery:
            logger.warning(f"Delivery {delivery_id} not found")
            return False
        
        now = datetime.utcnow()
        
        # Update the accepted request
        delivery_request.status = 'Accepted'
        delivery_request.accepted_at = now
        
        # Assign delivery to driver
        delivery.driver_id = driver_id
        delivery.status = 'Assigned'
        delivery.assigned_at = now
        
        # Cancel all other pending offers for this delivery
        other_requests = DeliveryRequest.query.filter(
            DeliveryRequest.delivery_id == delivery_id,
            DeliveryRequest.id != delivery_request_id,
            DeliveryRequest.status == 'Pending'
        ).all()
        
        for req in other_requests:
            req.status = 'Cancelled'
        
        # Notify customer that driver accepted
        order = Order.query.get(delivery.order_id)
        if order:
            customer_notification = Notification(
                recipient_id=order.customer_id,
                recipient_type='customer',
                title='Driver Assigned!',
                body=f"Driver {delivery.driver.full_name} accepted your delivery",
                notification_type='driver_assigned',
                channels='in-app,push',
                status='pending',
                order_id=order.id,
                delivery_id=delivery_id,
                data={
                    'delivery_id': delivery_id,
                    'driver_name': delivery.driver.full_name,
                    'driver_phone': delivery.driver.phone,
                    'vehicle_type': delivery.driver.vehicle_type,
                    'vehicle_number': delivery.driver.vehicle_number,
                    'driver_rating': delivery.driver.rating
                }
            )
            db.session.add(customer_notification)
        
        db.session.commit()
        logger.info(f"Driver {driver_id} accepted delivery {delivery_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error accepting delivery offer: {e}")
        db.session.rollback()
        return False


def driver_decline_delivery_offer(driver_id, delivery_request_id, reason=None):
    """
    Driver declines a delivery offer
    - Updates DeliveryRequest status to 'Declined'
    - Triggers retry: auto-offer to next batch of drivers
    - Returns True on success
    """
    try:
        delivery_request = db.session.get(DeliveryRequest, delivery_request_id)
        if not delivery_request:
            logger.warning(f"DeliveryRequest {delivery_request_id} not found")
            return False
        
        if delivery_request.driver_id != driver_id:
            logger.warning(f"Driver {driver_id} cannot decline delivery request {delivery_request_id}")
            return False
        
        now = datetime.utcnow()
        
        # Update request
        delivery_request.status = 'Declined'
        delivery_request.declined_at = now
        delivery_request.decline_reason = reason or 'Unknown'
        
        delivery_id = delivery_request.delivery_id
        
        db.session.commit()
        logger.info(f"Driver {driver_id} declined delivery {delivery_id}: {reason}")
        
        # Check if all pending offers expired/declined
        pending_requests = DeliveryRequest.query.filter(
            DeliveryRequest.delivery_id == delivery_id,
            DeliveryRequest.status == 'Pending'
        ).all()
        
        if not pending_requests:
            # All offers exhausted - trigger retry (send to next batch)
            retry_delivery_assignment(delivery_id)
        
        return True
    
    except Exception as e:
        logger.error(f"Error declining delivery offer: {e}")
        db.session.rollback()
        return False


def check_expired_delivery_offers():
    """
    Background task: Check for expired delivery offers
    - Marks Pending offers older than 60s as 'Expired'
    - Auto-retries delivery to next batch of drivers
    - Called periodically (e.g., every minute)
    """
    try:
        now = datetime.utcnow()
        
        # Find expired pending requests
        expired = DeliveryRequest.query.filter(
            DeliveryRequest.status == 'Pending',
            DeliveryRequest.expires_at < now
        ).all()
        
        delivery_ids_to_retry = set()
        
        for req in expired:
            req.status = 'Expired'
            delivery_ids_to_retry.add(req.delivery_id)
        
        db.session.commit()
        
        # Retry each delivery with new batch of drivers
        for delivery_id in delivery_ids_to_retry:
            retry_delivery_assignment(delivery_id)
        
        logger.info(f"Checked {len(expired)} expired delivery offers")
        return len(expired)
    
    except Exception as e:
        logger.error(f"Error checking expired offers: {e}")
        return 0


def retry_delivery_assignment(delivery_id, attempt_num=1):
    """
    Retry delivery assignment to new batch of drivers
    - Gets all drivers who already declined/expired
    - Excludes them from next search
    - Escalates offer parameters (higher pay) on 2nd+ attempt
    
    Args:
        delivery_id: Delivery ID to retry
        attempt_num: Which attempt this is (1st, 2nd, etc.)
    """
    try:
        delivery = db.session.get(Delivery, delivery_id)
        if not delivery:
            logger.warning(f"Delivery {delivery_id} not found for retry")
            return False
        
        # Don't retry if already assigned
        if delivery.status != 'Pending':
            return False
        
        # Get all rejected driver IDs so far
        rejected = [
            req.driver_id for req in DeliveryRequest.query.filter(
                DeliveryRequest.delivery_id == delivery_id,
                DeliveryRequest.status.in_(['Declined', 'Expired'])
            ).all()
        ]
        
        # Escalation: increase radius on each retry
        search_radius = 5.0 + (attempt_num - 1) * 3.0  # 5km, 8km, 11km, ...
        
        # Escalation: apply surge multiplier on second+ attempt
        if attempt_num > 1:
            delivery.peak_multiplier = min(1.5, 1.0 + (attempt_num - 1) * 0.15)  # Max 1.5x
        
        # Find and offer to next batch
        nearby_drivers = find_nearby_drivers(
            delivery.pickup_lat, delivery.pickup_lng,
            radius_km=search_radius,
            exclude_driver_ids=rejected,
            limit=5
        )
        
        if nearby_drivers:
            offered_ids = send_delivery_offers(delivery_id, num_offers=len(nearby_drivers))
            logger.info(f"Retried delivery {delivery_id} (attempt {attempt_num}): offered to {len(offered_ids)} drivers")
            return True
        else:
            logger.warning(f"No drivers available for retry on delivery {delivery_id}")
            # Escalate further or mark as dead-letter
            if attempt_num < 3:
                # Schedule another retry after delay
                logger.info(f"Scheduling retry {attempt_num + 1} for delivery {delivery_id}")
            else:
                # Max retries reached - mark for manual intervention
                logger.warning(f"Max retries reached for delivery {delivery_id} - requires manual assignment")
            return False
    
    except Exception as e:
        logger.error(f"Error retrying delivery assignment: {e}")
        return False


def auto_assign_delivery(delivery_id):
    """
    Main entry point: Auto-assign a delivery
    Called when order is created and needs immediate assignment
    
    Returns:
        True if offers sent, False otherwise
    """
    try:
        logger.info(f"Starting auto-assignment for delivery {delivery_id}")
        
        delivery = db.session.get(Delivery, delivery_id)
        if not delivery:
            logger.warning(f"Delivery {delivery_id} not found")
            return False
        
        # Send offers to first batch of drivers
        offered_ids = send_delivery_offers(delivery_id, num_offers=3)
        
        if offered_ids:
            logger.info(f"Auto-assigned delivery {delivery_id} to {len(offered_ids)} drivers")
            return True
        else:
            logger.warning(f"Failed to auto-assign delivery {delivery_id} - no drivers available")
            return False
    
    except Exception as e:
        logger.error(f"Error in auto_assign_delivery: {e}")
        return False
