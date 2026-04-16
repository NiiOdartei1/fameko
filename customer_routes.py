"""
Customer Routes
Customer order placement, tracking, and account management
"""
import logging
import requests
from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from database import db
from models import Customer, Order, OrderItem, Delivery, Driver, DriverLocation, DriverRating, Notification, Conversation, Message, CallLog

logger = logging.getLogger(__name__)
customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

# ===================== AUTHENTICATION =====================

@customer_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Customer registration"""
    if request.method == 'POST':
        data = request.form
        
        email = data.get('email', '').strip()
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        address = data.get('address', '').strip()
        
        if Customer.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('customer.register'))
        
        try:
            customer = Customer(name=name, email=email, phone=phone, default_address=address)
            customer.set_password(password)
            db.session.add(customer)
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('customer.login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed', 'danger')
            return redirect(url_for('customer.register'))
    
    return render_template('customer/register.html')


@customer_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Customer login"""
    if request.method == 'POST':
        data = request.form
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        logger.info(f"Customer login attempt with email: {email}")
        
        customer = Customer.query.filter_by(email=email).first()
        
        if not customer:
            logger.warning(f"Customer not found: {email}")
            flash('Email not registered', 'danger')
            return redirect(url_for('customer.login'))
        
        if not customer.check_password(password):
            logger.warning(f"Invalid password for customer: {email}")
            flash('Invalid password', 'danger')
            return redirect(url_for('customer.login'))
        
        if not customer.is_active:
            logger.warning(f"Inactive customer login attempt: {email}")
            flash('Account is inactive. Contact support.', 'danger')
            return redirect(url_for('customer.login'))
        
        # Set session user type BEFORE login to ensure it's available in load_user
        session['user_type'] = 'customer'
        session.modified = True
        
        login_user(customer, remember=True)
        logger.info(f"Customer logged in successfully: {email} (ID: {customer.id})")
        flash('Login successful!', 'success')
        return redirect(url_for('customer.dashboard'))
    
    return render_template('customer/login.html')


@customer_bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    """Customer logout"""
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('customer.login'))


# ===================== DASHBOARD =====================

@customer_bp.route('/dashboard')
@login_required
def dashboard():
    """Customer dashboard"""
    if not isinstance(current_user, Customer):
        return redirect(url_for('customer.login'))
    
    orders = Order.query.filter_by(customer_id=current_user.id).filter(Order.status != 'Cancelled').order_by(Order.created_at.desc()).limit(10).all()
    return render_template('customer/dashboard.html', orders=orders)


# ===================== ORDERS =====================

@customer_bp.route('/orders/new', methods=['GET'])
@login_required
def create_order_page():
    """Display order creation form"""
    if not isinstance(current_user, Customer):
        flash('Unauthorized', 'danger')
        return redirect(url_for('customer.login'))
    return render_template('customer/create_order.html')


@customer_bp.route('/orders', methods=['GET'])
@login_required
def get_orders():
    """Get all customer orders"""
    if not isinstance(current_user, Customer):
        flash('Unauthorized', 'danger')
        return redirect(url_for('customer.login'))
    
    orders = Order.query.filter_by(customer_id=current_user.id).filter(Order.status != 'Cancelled').order_by(Order.created_at.desc()).all()
    return render_template('customer/orders.html', orders=orders)


@customer_bp.route('/orders/<int:order_id>', methods=['GET'])
@login_required
def get_order(order_id):
    """Get specific order details"""
    if not isinstance(current_user, Customer):
        flash('Unauthorized', 'danger')
        return redirect(url_for('customer.login'))
    
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('customer.dashboard'))
    return render_template('customer/order_details.html', order=order)


@customer_bp.route('/orders', methods=['POST'])
@login_required
def create_order():
    """Create new order with auto-assignment"""
    if not isinstance(current_user, Customer):
        flash('Unauthorized', 'danger')
        return redirect(url_for('customer.login'))
    data = request.form
    def parse_float(value, default=None):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def parse_int(value, default=None):
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return default

    try:
        logger.info(f"[ORDER_CREATION] Starting order creation for customer {current_user.id}")
        logger.debug(f"[ORDER_CREATION] Form data: service_type={data.get('service_type_selected')}, name={data.get('shipping_name')}, phone={data.get('shipping_phone')}")
        
        # Step 1: Create Order
        logger.info("[ORDER_CREATION] Step 1: Creating Order record...")
        order = Order(
            customer_id=current_user.id,
            total_amount=parse_float(data.get('total_amount', 0), 0.0),
            shipping_name=data.get('shipping_name', current_user.name),
            shipping_address=data.get('shipping_address', ''),
            shipping_phone=data.get('shipping_phone', current_user.phone),
            latitude=parse_float(data.get('latitude')) if data.get('latitude') else None,
            longitude=parse_float(data.get('longitude')) if data.get('longitude') else None,
            payment_method=data.get('payment_method', 'Cash on Delivery'),
            status='Pending'
        )
        db.session.add(order)
        db.session.flush()
        logger.info(f"[ORDER_CREATION] ✓ Order {order.id} created successfully")
        
        # Step 2: Get service type
        service_type = data.get('service_type_selected', 'package_delivery')
        logger.info(f"[ORDER_CREATION] Step 2: Service type = {service_type}")
        
        # Step 3: Create Delivery
        logger.info("[ORDER_CREATION] Step 3: Creating Delivery record...")
        estimated_duration = data.get('estimated_duration_minutes', 30)
        try:
            estimated_duration = int(round(float(estimated_duration)))
        except (TypeError, ValueError):
            estimated_duration = 30

        delivery = Delivery(
            order_id=order.id,
            pickup_location=data.get('pickup_location', order.shipping_address),
            dropoff_location=data.get('dropoff_location', order.shipping_address),
            pickup_lat=parse_float(data.get('pickup_lat')) if data.get('pickup_lat') else None,
            pickup_lng=parse_float(data.get('pickup_lng')) if data.get('pickup_lng') else None,
            dropoff_lat=parse_float(data.get('dropoff_lat')) if data.get('dropoff_lat') else None,
            dropoff_lng=parse_float(data.get('dropoff_lng')) if data.get('dropoff_lng') else None,
            base_fare=Decimal(str(parse_float(data.get('base_fare'), 5.00))),
            per_km_rate=Decimal(str(parse_float(data.get('per_km_rate'), 1.50))),
            distance_km=parse_float(data.get('distance_km'), 0.0),
            estimated_duration_minutes=estimated_duration,
            status='Pending',
            service_type=service_type
        )
        db.session.add(delivery)
        db.session.commit()
        logger.info(f"[ORDER_CREATION] ✓ Delivery {delivery.id} created successfully (distance: {delivery.distance_km}km, duration: {delivery.estimated_duration_minutes}min)")
        
        # Step 4: Broadcast notification
        logger.info("[ORDER_CREATION] Step 4: Broadcasting order notification to drivers...")
        try:
            from sqlalchemy import or_
            eligible_drivers = Driver.query.filter(
                or_(
                    Driver.service_types == 'both',
                    Driver.service_types == service_type
                ),
                Driver.status == 'Approved'
            ).all()
            
            logger.info(f"[ORDER_CREATION] Found {len(eligible_drivers)} eligible drivers for service type: {service_type}")
            
            notification_data = {
                'order_id': order.id,
                'delivery_id': delivery.id,
                'pickup_address': delivery.pickup_location,
                'dropoff_address': delivery.dropoff_location,
                'distance_km': delivery.distance_km,
                'estimated_duration': delivery.estimated_duration_minutes,
                'total_amount': float(order.total_amount),
                'payment_method': order.payment_method,
                'service_type': service_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            from flask import current_app
            
            # Emit to all eligible drivers
            current_app.socketio.emit(
                'new_order_available',
                notification_data,
                namespace='/driver'
            )
            logger.info(f"[ORDER_CREATION] ✓ Notification broadcasted to {len(eligible_drivers)} drivers")
        except Exception as e:
            logger.error(f"[ORDER_CREATION] ✗ Failed to broadcast notification: {e}", exc_info=True)
        
        # Step 5: Auto-assign delivery
        logger.info("[ORDER_CREATION] Step 5: Initiating auto-assignment...")
        try:
            from delivery_assignment_engine import auto_assign_delivery
            auto_assign_delivery(delivery.id)
            logger.info(f"[ORDER_CREATION] ✓ Auto-assignment initiated for delivery {delivery.id}")
        except Exception as e:
            logger.error(f"[ORDER_CREATION] ✗ Auto-assignment failed: {e}", exc_info=True)
        
        logger.info(f"[ORDER_CREATION] ✓✓✓ Order creation completed successfully! Order={order.id}, Delivery={delivery.id}")
        flash('Order created successfully - finding a driver', 'success')
        return redirect(url_for('customer.dashboard'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"[ORDER_CREATION] ✗✗✗ FAILED TO CREATE ORDER: {e}", exc_info=True)
        flash('Error creating order', 'danger')
        return redirect(url_for('customer.dashboard'))


@customer_bp.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Cancel an order with reason"""
    if not isinstance(current_user, Customer):
        flash('Unauthorized', 'danger')
        return redirect(url_for('customer.login'))
    
    try:
        order = Order.query.get_or_404(order_id)
        
        # Verify ownership
        if order.customer_id != current_user.id:
            flash('Unauthorized', 'danger')
            return redirect(url_for('customer.dashboard'))
        
        # Prevent cancellation of already completed or cancelled orders
        if order.status in ['Completed', 'Cancelled']:
            flash('This order cannot be cancelled', 'danger')
            return redirect(url_for('customer.get_order', order_id=order_id))
        
        # Get cancellation details
        cancel_reason = request.form.get('cancel_reason', 'No reason provided')
        cancel_notes = request.form.get('cancel_notes', '')
        
        # Update order status
        order.status = 'Cancelled'
        order.cancelled_at = datetime.utcnow()
        order.cancellation_reason = cancel_reason
        order.cancellation_notes = cancel_notes
        
        # Cancel associated delivery
        delivery = Delivery.query.filter_by(order_id=order_id).first()
        if delivery and delivery.status not in ['Completed', 'Cancelled']:
            delivery.status = 'Cancelled'
            delivery.cancelled_at = datetime.utcnow()
        
        db.session.commit()
        logger.info(f"Order {order_id} cancelled by customer {current_user.id}. Reason: {cancel_reason}")
        flash('Order cancelled successfully', 'success')
        return redirect(url_for('customer.dashboard'))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cancelling order: {e}")
        flash('Error cancelling order', 'danger')
        return redirect(url_for('customer.get_order', order_id=order_id))


# ===================== TRACKING =====================

@customer_bp.route('/track', methods=['GET'])
@login_required
def track_deliveries():
    """Track active deliveries list"""
    if not isinstance(current_user, Customer):
        flash('Unauthorized', 'danger')
        return redirect(url_for('customer.login'))
    # Get all deliveries for orders belonging to this customer
    deliveries = db.session.query(Delivery).join(Order).filter(
        Order.customer_id == current_user.id,
        Delivery.status.in_(['Pending', 'Assigned', 'In Transit', 'Arrived'])
    ).order_by(Delivery.created_at.desc()).all()
    return render_template('customer/track_deliveries.html', deliveries=deliveries)


@customer_bp.route('/track/<int:delivery_id>', methods=['GET'])
@login_required
def track_delivery(delivery_id):
    """Track specific delivery"""
    if not isinstance(current_user, Customer):
        flash('Unauthorized', 'danger')
        return redirect(url_for('customer.login'))
    delivery = Delivery.query.get_or_404(delivery_id)
    # Verify ownership through order
    order = Order.query.get(delivery.order_id)
    if not order or order.customer_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('customer.dashboard'))
    return render_template('customer/track_delivery.html', delivery=delivery)


@customer_bp.route('/support', methods=['GET'])
@login_required
def support():
    """Support page"""
    return render_template('customer/support.html')


# ===================== DELIVERY STATUS & TRACKING API =====================

@customer_bp.route('/delivery/<int:delivery_id>/status', methods=['GET'])
@login_required
def delivery_status(delivery_id):
    """Get real-time delivery status with driver location"""
    if not isinstance(current_user, Customer):
        return {'error': 'Unauthorized'}, 403
    
    try:
        delivery = db.session.get(Delivery, delivery_id)
        if not delivery:
            return {'error': 'Delivery not found'}, 404
        
        # Verify customer owns this delivery
        order = db.session.get(Order, delivery.order_id)
        if not order or order.customer_id != current_user.id:
            return {'error': 'Unauthorized'}, 403
        
        response = {
            'delivery_id': delivery.id,
            'status': delivery.status,
            'pickup_location': delivery.pickup_location,
            'dropoff_location': delivery.dropoff_location,
            'distance_km': delivery.distance_km,
            'estimated_duration_minutes': delivery.estimated_duration_minutes,
            'total_fare': float(delivery.total_fare) if delivery.total_fare else 0,
            'created_at': delivery.created_at.isoformat(),
            'assigned_at': delivery.assigned_at.isoformat() if delivery.assigned_at else None,
            'started_at': delivery.started_at.isoformat() if delivery.started_at else None,
            'completed_at': delivery.completed_at.isoformat() if delivery.completed_at else None
        }
        
        # Add driver info if assigned
        if delivery.driver_id:
            driver = db.session.get(Driver, delivery.driver_id)
            if driver:
                response['driver'] = {
                    'id': driver.id,
                    'name': driver.full_name,
                    'phone': driver.phone,
                    'vehicle_type': driver.vehicle_type,
                    'vehicle_number': driver.vehicle_number,
                    'rating': driver.rating,
                    'profile_picture': driver.profile_picture
                }
                
                # Add current location if in transit
                if delivery.status == 'In Transit':
                    loc = db.session.query(DriverLocation).filter_by(driver_id=driver.id).first()
                    if loc and loc.latitude and loc.longitude:
                        response['driver']['current_location'] = {
                            'latitude': float(loc.latitude),
                            'longitude': float(loc.longitude),
                            'updated_at': loc.updated_at.isoformat() if loc.updated_at else None
                        }
        
        return response, 200
    
    except Exception as e:
        logger.error(f"Error getting delivery status: {e}")
        return {'error': str(e)}, 500



@customer_bp.route('/conversation/<int:delivery_id>', methods=['GET'])
@login_required
def get_or_create_conversation(delivery_id):
    """Get or create a conversation for a delivery (customer side)"""
    if not isinstance(current_user, Customer):
        return jsonify({'error': 'Unauthorized'}), 403

    delivery = Delivery.query.get_or_404(delivery_id)
    # Verify ownership through order
    order = Order.query.get(delivery.order_id)
    if not order or order.customer_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    conv = Conversation.query.filter_by(delivery_id=delivery_id).first()
    if not conv:
        conv = Conversation(delivery_id=delivery_id, customer_id=current_user.id, driver_id=delivery.driver_id)
        db.session.add(conv)
        db.session.commit()

    messages = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at.asc()).all()
    msgs = [
        {
            'id': m.id,
            'sender_type': m.sender_type,
            'sender_id': m.sender_id,
            'body': m.body,
            'created_at': m.created_at.isoformat()
        }
        for m in messages
    ]

    return jsonify({
        'success': True,
        'conversation_id': conv.id,
        'driver_id': conv.driver_id,
        'messages': msgs
    }), 200


@customer_bp.route('/conversation/<int:delivery_id>/chat', methods=['GET'])
@login_required
def conversation_chat(delivery_id):
    """Redirect to unified conversation page for a delivery."""
    if not isinstance(current_user, Customer):
        return redirect(url_for('customer.login'))

    delivery = Delivery.query.get_or_404(delivery_id)
    order = Order.query.get(delivery.order_id)
    if not order or order.customer_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('customer.dashboard'))

    conv = Conversation.query.filter_by(delivery_id=delivery_id).first()
    if not conv:
        conv = Conversation(delivery_id=delivery_id, customer_id=current_user.id, driver_id=delivery.driver_id)
        db.session.add(conv)
        db.session.commit()

    # Redirect to unified conversation page
    return redirect(url_for('unified_conversation', conv_id=conv.id))


@customer_bp.route('/conversations', methods=['GET'])
@login_required
def conversations_page():
    """Render customer conversations UI"""
    if not isinstance(current_user, Customer):
        return redirect(url_for('customer.login'))
    return render_template('customer/conversations.html')


@customer_bp.route('/conversations/list', methods=['GET'])
@login_required
def customer_list_conversations():
    """Return JSON list of conversations for the customer"""
    if not isinstance(current_user, Customer):
        return jsonify({'error': 'Unauthorized'}), 403

    convs = Conversation.query.filter_by(customer_id=current_user.id).order_by(Conversation.last_message_at.desc().nullslast()).all() if hasattr(Conversation, 'last_message_at') else Conversation.query.filter_by(customer_id=current_user.id).all()
    data = []
    for c in convs:
        last_msg = Message.query.filter_by(conversation_id=c.id).order_by(Message.created_at.desc()).first()
        data.append({
            'id': c.id,
            'delivery_id': c.delivery_id,
            'driver_id': c.driver_id,
            'last_message': last_msg.body if last_msg else None,
            'last_message_at': last_msg.created_at.isoformat() if last_msg else (c.last_message_at.isoformat() if c.last_message_at else None)
        })

    return jsonify({'success': True, 'conversations': data}), 200


@customer_bp.route('/conversation/<int:conv_id>/messages', methods=['GET'])
@login_required
def get_conversation_messages(conv_id):
    if not isinstance(current_user, Customer):
        return jsonify({'error': 'Unauthorized'}), 403

    conv = Conversation.query.get_or_404(conv_id)
    if conv.customer_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    messages = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at.asc()).all()
    msgs = [
        {
            'id': m.id,
            'sender_type': m.sender_type,
            'sender_id': m.sender_id,
            'body': m.body,
            'created_at': m.created_at.isoformat()
        }
        for m in messages
    ]
    return jsonify({'success': True, 'messages': msgs}), 200


@customer_bp.route('/conversation/<int:conv_id>/send', methods=['POST'])
@login_required
def customer_send_message(conv_id):
    if not isinstance(current_user, Customer):
        return jsonify({'error': 'Unauthorized'}), 403

    conv = Conversation.query.get_or_404(conv_id)
    if conv.customer_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    body = data.get('body') or data.get('message')
    if not body:
        return jsonify({'error': 'Empty message'}), 400

    msg = Message(conversation_id=conv.id, sender_type='customer', sender_id=current_user.id, body=body)
    db.session.add(msg)
    conv.last_message_at = datetime.utcnow()
    db.session.commit()

    payload = {
        'conversation_id': conv.id,
        'sender_type': 'customer',
        'sender_id': current_user.id,
        'body': msg.body,
        'created_at': msg.created_at.isoformat(),
        'delivery_id': conv.delivery_id,
        'customer_id': conv.customer_id
    }

    # Notify driver in real-time if connected
    try:
        if conv.driver_id and current_app and getattr(current_app, 'socketio', None):
            current_app.socketio.emit('new_message', payload, namespace='/driver', room=f'driver_{conv.driver_id}')
    except Exception:
        logger.exception('Failed to emit new_message to driver')

    return jsonify({'success': True, 'message': payload}), 200


@customer_bp.route('/call/driver/<int:driver_id>', methods=['POST'])
@login_required
def call_driver(driver_id):
    """Customer requests a call to the driver (logs and notifies driver)"""
    if not isinstance(current_user, Customer):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    delivery_id = data.get('delivery_id')

    # Try to find conversation if available
    conv = None
    if delivery_id:
        conv = Conversation.query.filter_by(delivery_id=delivery_id).first()

    call = CallLog(conversation_id=(conv.id if conv else None), caller_type='customer', caller_id=current_user.id, callee_id=driver_id)
    db.session.add(call)
    db.session.commit()

    payload = {
        'call_id': call.id,
        'caller_id': current_user.id,
        'caller_name': getattr(current_user, 'name', getattr(current_user, 'full_name', 'Customer')),
        'delivery_id': delivery_id
    }

    try:
        if getattr(current_app, 'socketio', None):
            current_app.socketio.emit('incoming_call', payload, namespace='/driver', room=f'driver_{driver_id}')
    except Exception:
        logger.exception('Failed to emit incoming_call to driver')

    return jsonify({'success': True, 'call_id': call.id}), 200


@customer_bp.route('/delivery/<int:delivery_id>/rate_driver', methods=['POST'])
@login_required
def rate_driver(delivery_id):
    """Rate driver after delivery completion"""
    if not isinstance(current_user, Customer):
        return {'error': 'Unauthorized'}, 403
    
    try:
        data = request.get_json() or {}
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        # Validate rating
        if not rating or not (1 <= rating <= 5):
            return {'error': 'Rating must be between 1 and 5'}, 400
        
        delivery = db.session.get(Delivery, delivery_id)
        if not delivery:
            return {'error': 'Delivery not found'}, 404
        
        # Verify customer owns this delivery
        order = db.session.get(Order, delivery.order_id)
        if not order or order.customer_id != current_user.id:
            return {'error': 'Unauthorized'}, 403
        
        # Verify delivery is completed
        if delivery.status != 'Delivered':
            return {'error': 'Can only rate completed deliveries'}, 400
        
        if not delivery.driver_id:
            return {'error': 'No driver assigned to this delivery'}, 400
        
        # Check if already rated
        existing_rating = db.session.query(DriverRating).filter(
            DriverRating.delivery_id == delivery_id
        ).first()
        
        if existing_rating:
            return {'error': 'You have already rated this delivery'}, 400
        
        # Create rating
        driver_rating = DriverRating(
            driver_id=delivery.driver_id,
            delivery_id=delivery_id,
            rating=rating,
            comment=comment
        )

        db.session.add(driver_rating)

        # Update driver's average rating
        driver = db.session.get(Driver, delivery.driver_id)
        if driver:
            all_ratings = DriverRating.query.filter_by(driver_id=driver.id).all()
            avg_rating = sum(r.rating for r in all_ratings) / len(all_ratings)
            driver.rating = round(avg_rating, 1)
            driver.completed_deliveries = len(all_ratings)

        db.session.commit()

        return {'message': 'Rating submitted successfully'}, 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting rating: {e}")
        return {'error': 'Error submitting rating'}, 500


@customer_bp.route('/delivery/<int:delivery_id>/route', methods=['GET', 'POST'])
@login_required
def get_delivery_route(delivery_id):
    """Get route for a delivery (internal endpoint, replaces external 8012 service)"""
    if not isinstance(current_user, Customer):
        return {'error': 'Unauthorized'}, 403
    
    try:
        delivery = db.session.get(Delivery, delivery_id)
        if not delivery:
            return {'error': 'Delivery not found'}, 404
        
        # Verify customer owns this delivery
        order = db.session.get(Order, delivery.order_id)
        if not order or order.customer_id != current_user.id:
            return {'error': 'Unauthorized'}, 403
        
        # Get coordinates from request or delivery
        if request.method == 'POST':
            data = request.get_json() or {}
            pickup_lat = data.get('pickup_lat', delivery.pickup_lat)
            pickup_lng = data.get('pickup_lng', delivery.pickup_lng)
            dropoff_lat = data.get('dropoff_lat', delivery.dropoff_lat)
            dropoff_lng = data.get('dropoff_lng', delivery.dropoff_lng)
        else:
            pickup_lat = delivery.pickup_lat
            pickup_lng = delivery.pickup_lng
            dropoff_lat = delivery.dropoff_lat
            dropoff_lng = delivery.dropoff_lng
        
        # Validate coordinates
        if not all([pickup_lat, pickup_lng, dropoff_lat, dropoff_lng]):
            logger.warning(f"[ROUTE] Missing coordinates for delivery {delivery_id}")
            return {
                'error': 'Missing delivery coordinates',
                'primary': {
                    'coordinates': [[pickup_lng, pickup_lat], [dropoff_lng, dropoff_lat]]
                }
            }, 200
        
        logger.info(f"[ROUTE] Calculating route for delivery {delivery_id}: ({pickup_lat}, {pickup_lng}) -> ({dropoff_lat}, {dropoff_lng})")
        
        # Try to get full route from internal service
        try:
            from graphml import get_route_on_roads
            
            logger.debug(f"[ROUTE] graphml import successful")
            
            # Call get_route_on_roads with dict format - SAME FORMAT as create order uses
            pickup_dict = {'lat': float(pickup_lat), 'lng': float(pickup_lng)}
            dropoff_dict = {'lat': float(dropoff_lat), 'lng': float(dropoff_lng)}
            
            logger.debug(f"[ROUTE] Calling get_route_on_roads with pickup={pickup_dict}, dropoff={dropoff_dict}")
            
            # Call with same parameters as create_order would use
            route_result = get_route_on_roads(
                pickup=pickup_dict,
                dropoff=dropoff_dict,
                num_alternatives=1,
                detail_level="medium",
                region=None
            )
            
            logger.debug(f"[ROUTE] get_route_on_roads returned: {type(route_result)} with keys: {route_result.keys() if isinstance(route_result, dict) else 'N/A'}")
            
            # Extract route coordinates from result
            if route_result and isinstance(route_result, dict):
                route_coords = route_result.get('route_coords')
                
                if route_coords and isinstance(route_coords, list) and len(route_coords) >= 2:
                    logger.info(f"[ROUTE] ✓ Road-following route calculated with {len(route_coords)} waypoints")
                    
                    # Validate coordinates are in [lng, lat] format
                    validated_coords = []
                    for coord in route_coords:
                        if isinstance(coord, (list, tuple)) and len(coord) == 2:
                            try:
                                lng, lat = float(coord[0]), float(coord[1])
                                validated_coords.append([lng, lat])
                            except (ValueError, TypeError):
                                logger.warning(f"[ROUTE] Invalid coordinate: {coord}")
                                continue
                    
                    if len(validated_coords) >= 2:
                        return {
                            'primary': {
                                'coordinates': validated_coords
                            },
                            'alternatives': route_result.get('alt_routes', [])
                        }, 200
                    else:
                        logger.warning(f"[ROUTE] After validation, only {len(validated_coords)} coordinates remain")
                        raise ValueError('Route has insufficient valid waypoints')
                else:
                    logger.warning(f"[ROUTE] route_coords is empty or invalid: {route_coords}")
                    raise ValueError('Route calculation returned insufficient waypoints')
            else:
                logger.warning(f"[ROUTE] route_result is not a dict or is None: {route_result}")
                raise ValueError('Route calculation returned invalid result')
                
        except ImportError as e:
            logger.error(f"[ROUTE] Failed to import graphml: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"[ROUTE] Route calculation failed: {type(e).__name__}: {e}", exc_info=True)
            
            # If route calculation fails, create interpolated waypoints as fallback
            # Use more waypoints for better visual quality
            logger.info(f"[ROUTE] Falling back to interpolated waypoints for delivery {delivery_id}")
            
            num_waypoints = 5
            route_coords = []
            for i in range(num_waypoints + 1):
                t = i / num_waypoints
                lat = float(pickup_lat) + (float(dropoff_lat) - float(pickup_lat)) * t
                lng = float(pickup_lng) + (float(dropoff_lng) - float(pickup_lng)) * t
                route_coords.append([lng, lat])
            
            return {
                'primary': {
                    'coordinates': route_coords
                },
                'alternatives': []
            }, 200
    
    except Exception as e:
        logger.error(f"Error calculating delivery route: {type(e).__name__}: {e}", exc_info=True)
        return {
            'error': str(e),
            'primary': {
                'coordinates': []
            }
        }, 500
    
    except Exception as e:
        logger.error(f"Error calculating delivery route: {e}", exc_info=True)
        return {
            'error': str(e),
            'primary': {
                'coordinates': []
            }
        }, 500


@customer_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    """Get customer's notifications"""
    if not isinstance(current_user, Customer):
        return {'error': 'Unauthorized'}, 403
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        notifications_query = Notification.query.filter(
            Notification.recipient_id == current_user.id,
            Notification.recipient_type == 'customer'
        ).order_by(Notification.created_at.desc())
        
        paginated = notifications_query.paginate(page=page, per_page=per_page)
        
        notifications = [
            {
                'id': n.id,
                'title': n.title,
                'body': n.body,
                'type': n.notification_type,
                'created_at': n.created_at.isoformat(),
                'read_at': n.read_at.isoformat() if n.read_at else None,
                'data': n.data
            }
            for n in paginated.items
        ]
        
        return {
            'success': True,
            'notifications': notifications,
            'total': paginated.total,
            'pages': paginated.pages,
            'page': page
        }, 200
    
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return {'error': str(e)}, 500


# ===================== GEOCODING =====================

@customer_bp.route('/geocode', methods=['GET', 'POST'])
def geocode():
    """OpenStreetMap geocoding proxy - No auth required since used in location selection"""
    try:
        if request.method == 'GET':
            q = request.args.get('q', '').strip()
            limit = request.args.get('limit', '5')
            countrycodes = request.args.get('countrycodes', '')
        else:
            data = request.get_json(silent=True) or {}
            q = (data.get('q') or data.get('address') or '').strip()
            limit = data.get('limit', 5)
            countrycodes = data.get('countrycodes', '')

        # Validate parameters
        try:
            limit = int(limit)
            if limit < 1:
                limit = 5
            if limit > 10:
                limit = 10
        except (ValueError, TypeError):
            limit = 5

        if not q or len(q) < 2:
            logger.debug(f"Geocode query too short or empty: '{q}'")
            return jsonify([]), 200

        logger.debug(f"Geocoding request: q={q}, limit={limit}, countrycodes={countrycodes}")
        
        try:
            params = {
                'format': 'json',
                'q': q,
                'limit': limit,
                'addressdetails': 1
            }
            if countrycodes:
                params['countrycodes'] = countrycodes

            headers = {
                'User-Agent': 'DeliverySystem/1.0 (delivery@localhost)',
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate'
            }
            
            resp = requests.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers, timeout=8)
            
            if resp.status_code == 200:
                results = resp.json()
                logger.debug(f"Geocoding found {len(results)} results for '{q}'")
                return jsonify(results), 200
            else:
                logger.warning(f"Nominatim returned status {resp.status_code} for query: {q}")
                return jsonify([]), 200
        except requests.Timeout:
            logger.warning(f'Geocoding request timed out for query: {q}')
            return jsonify([]), 200
        except requests.ConnectionError as e:
            logger.warning(f'Geocoding connection error: {type(e).__name__}: {e}')
            return jsonify([]), 200
        except Exception as e:
            logger.warning(f'Geocoding error: {type(e).__name__}: {e}')
            return jsonify([]), 200
        
    except Exception as e:
        logger.exception(f'Unexpected error in geocode route: {type(e).__name__}: {e}')
        return jsonify([]), 500
