"""

Admin Routes

Admin dashboard, driver management, order management

"""

import logging
import traceback
import os

from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify

from flask_login import login_required, current_user, login_user, logout_user

from forms import AdminLoginForm



from database import db

from models import Admin, Driver, Order, Delivery, Customer, DriverLocation

from models import DriverRating  # Import separately to ensure it's loaded



logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')





def admin_only(f):

    """Decorator to check if user is admin"""

    from functools import wraps

    @wraps(f)

    def decorated_function(*args, **kwargs):

        logger.info(f"Current user: {current_user}, type: {type(current_user)}, is_authenticated: {current_user.is_authenticated if current_user else 'None'}")

        if not current_user or not current_user.is_authenticated:

            flash('Please log in to access the admin area', 'info')

            return redirect(url_for('admin.login'))



        # Check if user is admin by class type only

        is_admin = isinstance(current_user, Admin)

        logger.info(f"Is admin check: {is_admin}")



        if not is_admin:

            flash('Unauthorized - Admin access required', 'danger')

            return redirect(url_for('main.index'))

        return f(*args, **kwargs)

    return decorated_function





# ===================== AUTH =====================



@admin_bp.route('/test-form')

def test_form():

    """Test form creation"""

    try:

        form = AdminLoginForm()

        return f"Form created successfully. Fields: {list(form._fields.keys())}"

    except Exception as e:

        return f"Error creating form: {e}"





@admin_bp.route('/login', methods=['GET', 'POST'])

def login():

    """Admin login"""

    form = AdminLoginForm()

    

    if form.validate_on_submit():

        admin = Admin.query.filter_by(email=form.email.data).first()

        

        if admin and admin.check_password(form.password.data) and admin.is_active:

            # Set session user type BEFORE login to ensure it's available in load_user
            session['user_type'] = 'admin'
            session.modified = True
            
            login_user(admin, remember=form.remember.data)

            

            flash('Login successful', 'success')

            return redirect(url_for('admin.dashboard'))

        

        flash('Invalid email or password', 'danger')

    

    return render_template('admin/login.html', form=form)





@admin_bp.route('/logout', methods=['POST', 'GET'])

@login_required

def logout():

    """Admin logout"""

    logout_user()

    session.pop('user_type', None)

    flash('Logged out successfully', 'info')

    return redirect(url_for('admin.login'))





# ===================== DASHBOARD =====================



@admin_bp.route('/dashboard')

@login_required

@admin_only

def dashboard():

    """Admin dashboard"""

    stats = {

        'total_drivers': Driver.query.count(),

        'active_drivers': Driver.query.filter_by(is_online=True).count(),

        'total_orders': Order.query.count(),

        'total_deliveries': Delivery.query.count(),

        'completed_deliveries': Delivery.query.filter_by(status='Delivered').count(),

        'active_deliveries': Delivery.query.filter_by(status='In Transit').count(),

        'pending_deliveries': Delivery.query.filter_by(status='Pending').count(),

        'total_customers': Customer.query.count(),

    }

    

    return render_template('admin/dashboard.html', stats=stats)





@admin_bp.route('/drivers/<int:driver_id>/approve', methods=['POST'])

@login_required

@admin_only

def approve_driver(driver_id):

    """Approve a driver"""

    try:

        driver = Driver.query.get_or_404(driver_id)

        driver.status = 'Active'

        db.session.commit()

        

        logger.info(f"Driver {driver_id} approved by admin {current_user.email}")

        flash(f'Driver {driver.full_name} approved successfully', 'success')

        return redirect(url_for('admin.drivers_page'))

    except Exception as e:

        db.session.rollback()

        logger.error(f"Error approving driver {driver_id}: {str(e)}")

        flash('Failed to approve driver', 'danger')

        return redirect(url_for('admin.drivers_page'))





@admin_bp.route('/drivers/<int:driver_id>/reject', methods=['POST'])

@login_required

@admin_only

def reject_driver(driver_id):

    """Reject a driver"""

    try:

        data = request.get_json() or {}

        reason = data.get('reason', 'No reason provided')

        

        driver = Driver.query.get_or_404(driver_id)

        driver.status = 'Suspended'

        db.session.commit()

        

        logger.info(f"Admin {current_user.username} rejected driver {driver.full_name}. Reason: {reason}")

        flash(f'Driver {driver.full_name} rejected', 'warning')

        return redirect(url_for('admin.dashboard'))

    except Exception as e:

        db.session.rollback()

        logger.error(f"Error rejecting driver {driver_id}: {e}")

        flash('Failed to reject driver', 'danger')

        return redirect(url_for('admin.dashboard'))





# ===================== DRIVER MANAGEMENT =====================



@admin_bp.route('/drivers-page')

@login_required

@admin_only

def drivers_page():

    """Driver management page with real customer ratings"""

    # Try using full path reference

    import models

    DriverRating = getattr(models, 'DriverRating', None)

    

    drivers = Driver.query.all()

    

    # Check if DriverRating is available

    if DriverRating is None:

        print("ERROR: DriverRating not found in models module!")

        # Fallback: use a simple rating calculation

        for driver in drivers:

            driver.calculated_rating = 4.5  # Placeholder rating

    else:

        # Calculate real average ratings from customer feedback

        for driver in drivers:

            # Get all customer ratings for this driver

            ratings = db.session.query(db.func.avg(DriverRating.rating)).filter(DriverRating.driver_id == driver.id).scalar()

            driver.calculated_rating = round(ratings, 2) if ratings else None

    

    return render_template('admin/drivers.html', drivers=drivers)


@admin_bp.route('/drivers', methods=['GET'])
@login_required
@admin_only
def get_drivers():
    """API endpoint to get drivers by status"""
    try:
        status = request.args.get('status', 'Pending')
        
        # Query drivers by status
        drivers = Driver.query.filter_by(status=status).all()
        
        # Convert to JSON-serializable format
        drivers_data = []
        for driver in drivers:
            drivers_data.append({
                'id': driver.id,
                'full_name': driver.full_name,
                'email': driver.email,
                'phone': driver.phone,
                'vehicle_type': driver.vehicle_type,
                'license_number': driver.license_number,
                'status': driver.status,
                'date_joined': driver.date_joined.strftime('%Y-%m-%d') if driver.date_joined else None
            })
        
        return jsonify({'drivers': drivers_data})
    except Exception as e:
        logger.error(f"Error fetching drivers: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/drivers/<int:driver_id>/suspend', methods=['POST'])

@login_required

@admin_only

def suspend_driver(driver_id):

    """Suspend driver"""

    try:

        driver = Driver.query.get_or_404(driver_id)

        driver.status = 'Suspended'

        db.session.commit()

        

        logger.info(f"Driver {driver_id} suspended by admin")

        flash(f'Driver {driver.full_name} suspended', 'warning')

        return redirect(url_for('admin.drivers_page'))

    except Exception as e:

        db.session.rollback()

        logger.error(f"Error suspending driver: {e}")

        flash('Error suspending driver', 'danger')

        return redirect(url_for('admin.drivers_page'))





@admin_bp.route('/drivers/<int:driver_id>/activate', methods=['POST'])

@login_required

@admin_only

def activate_driver(driver_id):

    """Activate driver"""

    try:

        driver = Driver.query.get_or_404(driver_id)

        driver.status = 'Active'

        db.session.commit()

        

        logger.info(f"Driver {driver_id} activated by admin")

        flash(f'Driver {driver.full_name} activated', 'success')

        return redirect(url_for('admin.drivers_page'))

    except Exception as e:

        db.session.rollback()

        logger.error(f"Error activating driver: {e}")

        flash('Error activating driver', 'danger')

        return redirect(url_for('admin.drivers_page'))





@admin_bp.route('/orders-page')

@login_required

@admin_only

def orders_page():

    """Orders management page"""

    orders = Order.query.all()

    return render_template('admin/orders.html', orders=orders)





@admin_bp.route('/orders/<int:order_id>')

@login_required

@admin_only

def order_details(order_id):

    """View order details"""

    order = Order.query.get_or_404(order_id)

    return render_template('admin/order_details.html', order=order)













# ===================== SETTINGS =====================



@admin_bp.route('/settings-page')

@login_required

@admin_only

def settings_page():

    """Settings page"""

    return render_template('admin/settings.html')



@admin_bp.route('/maps-page')

@login_required

@admin_only

def maps_page():

    """Maps page for driver tracking"""

    return render_template('admin/driver_map.html')



@admin_bp.route('/test-simple', methods=['GET'])
@login_required
@admin_only
def test_simple():
    """Simple test without database"""
    return jsonify({'message': 'Simple test works', 'status': 'success'})

@admin_bp.route('/locations', methods=['GET'])
@login_required
@admin_only
def get_driver_locations():
    """Get all driver locations for admin map"""
    try:
        logger.info("Getting driver locations for admin map")
        
        # Direct implementation instead of import to avoid circular imports
        drivers = DriverLocation.query.all()
        logger.info(f"Found {len(drivers)} driver location records")
        
        locations = []
        for d in drivers:
            if d.latitude is None or d.longitude is None:
                continue
            
            # Get driver's region information
            driver = Driver.query.get(d.driver_id)
            driver_region = driver.region if driver and hasattr(driver, 'region') else None

            locations.append({
                "driver_id": d.driver_id,
                "lat": float(d.latitude),
                "lng": float(d.longitude),
                "delivery_id": d.delivery_id,
                "timestamp": int(d.updated_at.timestamp()) if d.updated_at else None,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
                "region": driver_region
            })
        
        logger.info(f"Returning {len(locations)} valid driver locations")
        
        return jsonify({
            'count': len(locations),
            'locations': locations
        })
    except ImportError as e:
        logger.error(f"Import error in get_driver_locations: {e}")
        return jsonify({'error': 'Driver location module not available', 'count': 0, 'locations': []}), 500
    except Exception as e:
        logger.error(f"Error getting driver locations: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to get locations', 'count': 0, 'locations': []}), 500





# ===================== CUSTOMER MANAGEMENT =====================

@admin_bp.route('/customers')
@login_required
@admin_only
def customers_page():
    """Customers management page"""
    return render_template('admin/customers.html')

@admin_bp.route('/api/customers', methods=['GET'])
@login_required
@admin_only
def get_customers():
    """Get all customers for admin"""
    try:
        page = int(request.args.get('page', 1))
        per_page = 20
        search = request.args.get('search', '')
        status = request.args.get('status', '')
        
        # Query customers with filters
        query = Customer.query
        
        if search:
            query = query.filter(
                Customer.name.ilike(f'%{search}%') |
                Customer.email.ilike(f'%{search}%') |
                Customer.phone.ilike(f'%{search}%')
            )

        if status:
            query = query.filter(Customer.is_active == (status == 'active'))

        # Paginate results
        customers = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        customers_data = []
        for customer in customers.items:
            customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'address': customer.default_address,
                'status': 'active' if customer.is_active else 'inactive',
                'created_at': customer.date_joined.isoformat() if customer.date_joined else None,
                'order_count': len(customer.orders) if customer.orders else 0
            })
        
        return jsonify({
            'success': True,
            'customers': customers_data,
            'total': customers.total,
            'pages': customers.pages,
            'current_page': customers.page
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@admin_bp.route('/api/customers', methods=['POST'])
@login_required
@admin_only
def create_customer():
    """Create new customer"""
    try:
        data = request.form
        
        # Validate required fields
        if not data.get('first_name') or not data.get('last_name') or not data.get('email') or not data.get('phone'):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        # Check if email already exists
        existing_customer = Customer.query.filter_by(email=data.get('email')).first()
        if existing_customer:
            return jsonify({
                'success': False,
                'message': 'Email already exists'
            }), 400
        
        # Create new customer
        customer = Customer(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            city=data.get('city'),
            postal_code=data.get('postal_code'),
            status=data.get('status', 'active')
        )
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer created successfully',
            'customer_id': customer.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@admin_bp.route('/api/customers/<int:customer_id>', methods=['PUT'])
@login_required
@admin_only
def update_customer(customer_id):
    """Update customer"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        data = request.form
        
        # Update customer fields
        customer.first_name = data.get('first_name', customer.first_name)
        customer.last_name = data.get('last_name', customer.last_name)
        customer.email = data.get('email', customer.email)
        customer.phone = data.get('phone', customer.phone)
        customer.address = data.get('address', customer.address)
        customer.city = data.get('city', customer.city)
        customer.postal_code = data.get('postal_code', customer.postal_code)
        customer.status = data.get('status', customer.status)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@admin_bp.route('/api/customers/<int:customer_id>', methods=['DELETE'])
@login_required
@admin_only
def delete_customer(customer_id):
    """Delete customer"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        db.session.delete(customer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ===================== ORDER MANAGEMENT =====================



@admin_bp.route('/orders', methods=['GET'])

@login_required

@admin_only

def get_orders():

    """Orders management page"""

    return redirect(url_for('admin.orders_page'))





# ===================== DELIVERY MANAGEMENT =====================



@admin_bp.route('/deliveries', methods=['GET'])

@login_required

@admin_only

def get_deliveries():

    """Deliveries page redirect"""

    return redirect(url_for('admin.orders_page'))





# ===================== ANALYTICS =====================



@admin_bp.route('/analytics')

@login_required

@admin_only

def analytics():

    # ...existing code...

    """Analytics page with real metrics"""

    # Timeframe selection (default: last 30 days)

    timeframe = request.args.get('timeframe', '30days')

    if timeframe == '7days':

        start_date = datetime.now() - timedelta(days=7)

    elif timeframe == '90days':

        start_date = datetime.now() - timedelta(days=90)

    elif timeframe == 'all':

        start_date = None

    else:

        start_date = datetime.now() - timedelta(days=30)



    # Orders and revenue

    orders_query = Order.query

    if start_date:

        orders_query = orders_query.filter(Order.order_date >= start_date)

    total_orders = orders_query.count()

    
    # Only count COMPLETED deliveries as verified revenue (not pending orders)
    revenue_query = db.session.query(db.func.sum(Delivery.total_fare)).filter(
        Delivery.status == 'Delivered'
    )
    if start_date:
        revenue_query = revenue_query.filter(Delivery.completed_at >= start_date)
    total_revenue = revenue_query.scalar() or 0
    
    # Count completed orders
    completed_orders = orders_query.filter(Order.status == 'Delivered').count()



    # Drivers

    total_drivers = Driver.query.count()

    active_drivers = Driver.query.filter_by(is_online=True).count()



    # Customers

    total_customers = Customer.query.count()



    # Orders trend (last 30 days, grouped by day)

    trend_days = 30 if timeframe == '30days' else 7 if timeframe == '7days' else 90 if timeframe == '90days' else 30

    trend_start = datetime.now() - timedelta(days=trend_days)

    trend_data = db.session.query(

        db.func.date(Order.order_date).label('date'),

        db.func.count(Order.id).label('orders')

    ).filter(Order.order_date >= trend_start).group_by(db.func.date(Order.order_date)).order_by(db.func.date(Order.order_date)).all()

    orders_trend = [{'date': str(row.date), 'orders': row.orders} for row in trend_data]



    # Order status breakdown

    status_counts = db.session.query(Order.status, db.func.count(Order.id)).group_by(Order.status).all()

    status_breakdown = {row[0]: row[1] for row in status_counts}



    # Top drivers (by deliveries and revenue)

    top_drivers = (

        db.session.query(

            Driver.full_name,

            Driver.id,

            db.func.count(Delivery.id).label('deliveries'),

            db.func.avg(Driver.rating).label('rating'),

            db.func.sum(Delivery.actual_driver_earnings).label('revenue')

        )

        .join(Delivery, Delivery.driver_id == Driver.id)

        .group_by(Driver.id)

        .order_by(db.func.count(Delivery.id).desc())

        .limit(3)

        .all()

    )

    drivers_table = [

        {

            'name': row.full_name,

            'id': row.id,

            'deliveries': row.deliveries,

            'rating': round(row.rating, 2) if row.rating else '-',

            'revenue': float(row.revenue) if row.revenue else 0

        } for row in top_drivers

    ]



    # Top customers (by orders and actual spent - only completed deliveries)

    top_customers = (
        db.session.query(
            Customer.id,
            Customer.name,
            Customer.email,
            db.func.count(Order.id).label('orders'),
            db.func.sum(Delivery.total_fare).label('spent'),
            Customer.is_active
        )
        .join(Order, Order.customer_id == Customer.id)
        .join(Delivery, Delivery.order_id == Order.id)
        .filter(Delivery.status == 'Delivered')  # Only completed deliveries
        .group_by(Customer.id)
        .order_by(db.func.count(Order.id).desc())
        .limit(3)
        .all()
    )

    customers_table = [
        {
            'name': row.name,
            'email': row.email,
            'orders': row.orders,
            'spent': float(row.spent) if row.spent else 0,
            'status': 'Active' if row.is_active else 'Inactive'
        } for row in top_customers
    ]


    # Payment method breakdown

    payment_methods = db.session.query(

        Order.payment_method,

        db.func.count(Order.id).label('transactions'),

        db.func.sum(Order.total_amount).label('volume')

    ).group_by(Order.payment_method).all()

    total_transactions = sum([row.transactions for row in payment_methods]) or 1

    payment_table = [

        {

            'method': row.payment_method,

            'transactions': row.transactions,

            'volume': float(row.volume) if row.volume else 0,

            'percentage': round((row.transactions / total_transactions) * 100, 1),

            'status': 'Active'  # Placeholder, adjust as needed

        } for row in payment_methods

    ]



    return render_template(

        'admin/analytics.html',

        total_orders=total_orders,

        completed_orders=completed_orders,

        total_revenue=total_revenue,

        total_drivers=total_drivers,

        active_drivers=active_drivers,

        total_customers=total_customers,

        orders_trend=orders_trend,

        status_breakdown=status_breakdown,

        drivers_table=drivers_table,

        customers_table=customers_table,

        payment_table=payment_table,

        timeframe=timeframe

    )


@admin_bp.route('/financial-breakdown')
@login_required
@admin_only
def financial_breakdown():
    """Detailed financial breakdown page with tips, bonuses, and surge analytics"""
    from models import PricingConfig
    
    timeframe = request.args.get('timeframe', '30days')
    
    if timeframe == '7days':
        start_date = datetime.now() - timedelta(days=7)
    elif timeframe == '90days':
        start_date = datetime.now() - timedelta(days=90)
    elif timeframe == 'all':
        start_date = None
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    # Get all completed deliveries
    completed_deliveries = db.session.query(Delivery).filter(Delivery.status == 'Delivered')
    if start_date:
        completed_deliveries = completed_deliveries.filter(Delivery.completed_at >= start_date)
    completed_deliveries = completed_deliveries.all()
    
    # Calculate detailed financial metrics
    total_customer_revenue = sum(float(d.total_fare or 0) for d in completed_deliveries)
    total_driver_earnings = sum(float(d.actual_driver_earnings or 0) for d in completed_deliveries)
    total_platform_fees = sum(float(d.total_platform_fees or 0) for d in completed_deliveries)
    total_tips = sum(float(d.tips or 0) for d in completed_deliveries)
    total_bonuses = sum(float(d.bonuses or 0) for d in completed_deliveries)
    
    # Calculate surge revenue (peak_multiplier > 1.0 means surge pricing was applied)
    total_surge_revenue = 0
    total_wait_time_fees = 0
    total_cancellation_fees = 0
    
    for d in completed_deliveries:
        # Surge revenue = (base_fare * peak_multiplier - base_fare) if peak_multiplier > 1
        if d.peak_multiplier > 1.0:
            base = float(d.base_fare or 0)
            surge_amount = base * (float(d.peak_multiplier) - 1.0)
            total_surge_revenue += surge_amount
        
        total_wait_time_fees += float(d.wait_time_fee or 0)
    
    # Pending revenue (not yet completed)
    pending_deliveries = db.session.query(Delivery).filter(
        Delivery.status.in_(['Pending', 'Assigned', 'In Transit'])
    )
    if start_date:
        pending_deliveries = pending_deliveries.filter(Delivery.created_at >= start_date)
    pending_deliveries = pending_deliveries.all()
    pending_revenue = sum(float(d.total_fare or 0) for d in pending_deliveries)
    
    # Payment method breakdown for completed deliveries
    payment_breakdown_query = db.session.query(
        Order.payment_method,
        db.func.count(Delivery.id).label('count'),
        db.func.sum(Delivery.total_fare).label('revenue')
    ).join(Order, Order.id == Delivery.order_id).filter(
        Delivery.status == 'Delivered'
    )
    if start_date:
        payment_breakdown_query = payment_breakdown_query.filter(Delivery.completed_at >= start_date)
    
    payment_breakdown = payment_breakdown_query.group_by(Order.payment_method).all()
    
    payment_data = [
        {
            'method': row.payment_method or 'Unknown',
            'count': row.count,
            'revenue': float(row.revenue or 0)
        }
        for row in payment_breakdown
    ]
    
    # Top earning drivers
    top_drivers_query = db.session.query(
        Driver.full_name,
        Driver.id,
        db.func.count(Delivery.id).label('deliveries'),
        db.func.sum(Delivery.actual_driver_earnings).label('earnings'),
        db.func.avg(Delivery.actual_driver_earnings).label('avg_earning')
    ).join(Delivery, Delivery.driver_id == Driver.id).filter(
        Delivery.status == 'Delivered'
    )
    if start_date:
        top_drivers_query = top_drivers_query.filter(Delivery.completed_at >= start_date)
    
    top_drivers = top_drivers_query.group_by(Driver.id).order_by(
        db.func.sum(Delivery.actual_driver_earnings).desc()
    ).limit(10).all()
    
    top_drivers_data = [
        {
            'name': row.full_name,
            'deliveries': row.deliveries,
            'total_earnings': float(row.earnings or 0),
            'avg_earning': float(row.avg_earning or 0)
        }
        for row in top_drivers
    ]
    
    # Daily revenue trend with detailed breakdown
    trend_days = 30 if timeframe == '30days' else 7 if timeframe == '7days' else 90 if timeframe == '90days' else 30
    trend_start = datetime.now() - timedelta(days=trend_days)
    
    daily_breakdown = db.session.query(
        db.func.date(Delivery.completed_at).label('date'),
        db.func.count(Delivery.id).label('deliveries'),
        db.func.sum(Delivery.total_fare).label('revenue'),
        db.func.sum(Delivery.actual_driver_earnings).label('driver_payout'),
        db.func.sum(Delivery.total_platform_fees).label('platform_fees'),
        db.func.sum(Delivery.tips).label('tips'),
        db.func.sum(Delivery.bonuses).label('bonuses')
    ).filter(
        Delivery.status == 'Delivered',
        Delivery.completed_at >= trend_start
    ).group_by(db.func.date(Delivery.completed_at)).order_by(
        db.func.date(Delivery.completed_at)
    ).all()
    
    daily_data = [
        {
            'date': str(row.date),
            'deliveries': row.deliveries,
            'revenue': float(row.revenue or 0),
            'driver_payout': float(row.driver_payout or 0),
            'platform_fees': float(row.platform_fees or 0),
            'tips': float(row.tips or 0),
            'bonuses': float(row.bonuses or 0)
        }
        for row in daily_breakdown
    ]
    
    # Get pricing config for reference
    from models import PricingConfig
    pricing_config = PricingConfig.get_config()
    
    return render_template(
        'admin/financial_breakdown.html',
        timeframe=timeframe,
        total_customer_revenue=total_customer_revenue,
        total_driver_earnings=total_driver_earnings,
        total_platform_fees=total_platform_fees,
        total_tips=total_tips,
        total_bonuses=total_bonuses,
        total_surge_revenue=total_surge_revenue,
        total_wait_time_fees=total_wait_time_fees,
        pending_revenue=pending_revenue,
        payment_data=payment_data,
        top_drivers=top_drivers_data,
        daily_data=daily_data,
        total_completed_deliveries=len(completed_deliveries),
        total_pending_deliveries=len(pending_deliveries),
        driver_commission=pricing_config.driver_commission_percent,
        platform_commission=100 - pricing_config.driver_commission_percent
    )



@admin_bp.route('/support', methods=['GET'])

@login_required

@admin_only

def support():

    """Support page"""

    return render_template('admin/support.html')


# ===================== PRICING CONFIGURATION =====================

@admin_bp.route('/pricing', methods=['GET'])
@login_required
@admin_only
def pricing_configuration():
    """Display pricing configuration page"""
    from models import PricingConfig
    
    config = PricingConfig.get_config()
    
    return render_template(
        'admin/pricing_configuration.html',
        driver_commission=config.driver_commission_percent,
        peak_multiplier=config.peak_multiplier,
        cancellation_fee=float(config.cancellation_fee),
        wait_time_fee=float(config.wait_time_fee),
        bonus_per_delivery=float(config.bonus_per_delivery),
        referral_bonus=float(config.referral_bonus)
    )


@admin_bp.route('/pricing/save', methods=['POST'])
@login_required
@admin_only
def save_pricing_configuration():
    """Save pricing configuration"""
    from models import PricingConfig
    from decimal import Decimal
    
    try:
        data = request.get_json()
        
        # Validate percentages
        driver_commission = float(data.get('driver_commission', 75))
        if driver_commission < 0 or driver_commission > 100:
            return jsonify({'success': False, 'message': 'Driver commission must be between 0 and 100%'}), 400
        
        peak_multiplier = float(data.get('peak_multiplier', 1.5))
        if peak_multiplier < 1.0 or peak_multiplier > 5.0:
            return jsonify({'success': False, 'message': 'Peak multiplier must be between 1.0 and 5.0'}), 400
        
        # Get or create config
        config = PricingConfig.get_config()
        
        # Update values
        config.driver_commission_percent = driver_commission
        config.peak_multiplier = peak_multiplier
        config.cancellation_fee = Decimal(str(data.get('cancellation_fee', 1.50)))
        config.wait_time_fee = Decimal(str(data.get('wait_time_fee', 0.15)))
        config.bonus_per_delivery = Decimal(str(data.get('bonus_per_delivery', 0.50)))
        config.referral_bonus = Decimal(str(data.get('referral_bonus', 5.00)))
        config.updated_by_admin_id = current_user.id
        config.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Pricing configuration updated by {current_user.email}: Driver={driver_commission}%, Platform={100-driver_commission}%")
        
        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
    
    except Exception as e:
        logger.error(f"Error saving pricing configuration: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


# ===================== DRIVER DOCUMENT VERIFICATION =====================

@admin_bp.route('/driver-documents', methods=['GET'])
@login_required
@admin_only
def driver_documents():
    """View all driver documents pending verification"""
    from models import Document, DriverOnboarding
    
    # Get filter parameters
    status_filter = request.args.get('status', 'Pending')
    page = request.args.get('page', 1, type=int)
    
    query = Document.query
    
    if status_filter and status_filter != 'All':
        query = query.filter_by(verification_status=status_filter)
    
    # Paginate
    documents = query.order_by(Document.uploaded_at.desc()).paginate(page=page, per_page=15)
    
    # Get stats
    total_docs = Document.query.count()
    pending_docs = Document.query.filter_by(verification_status='Pending').count()
    verified_docs = Document.query.filter_by(verification_status='Verified').count()
    rejected_docs = Document.query.filter_by(verification_status='Rejected').count()
    
    return render_template(
        'admin/driver_documents.html',
        documents=documents,
        status_filter=status_filter,
        total_docs=total_docs,
        pending_docs=pending_docs,
        verified_docs=verified_docs,
        rejected_docs=rejected_docs
    )


@admin_bp.route('/documents/<int:doc_id>/view', methods=['GET'])
@login_required
@admin_only
def view_document(doc_id):
    """Get document details and file URL for viewing"""
    from models import Document, DriverOnboarding, Driver
    
    try:
        doc = Document.query.get_or_404(doc_id)
        onboarding = DriverOnboarding.query.get_or_404(doc.onboarding_id)
        driver = Driver.query.get_or_404(onboarding.driver_id)
        
        # Determine file type from file path
        file_ext = os.path.splitext(doc.file_path)[1].lower()
        file_type = 'pdf' if file_ext == '.pdf' else 'image'
        
        # Generate URL to serve the file
        file_url = f'/admin/documents/file/{doc.id}'
        
        return jsonify({
            'success': True,
            'document': {
                'id': doc.id,
                'driver_name': driver.full_name,
                'document_type': doc.document_type,
                'document_number': doc.document_number,
                'uploaded_at': doc.uploaded_at.strftime('%B %d, %Y %I:%M %p'),
                'verification_status': doc.verification_status,
                'verification_notes': doc.verification_notes,
                'file_url': file_url,
                'file_type': file_type
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/documents/file/<int:doc_id>', methods=['GET'])
@login_required
@admin_only
def serve_document(doc_id):
    """Serve the actual document file"""
    from models import Document
    from flask import send_file
    
    try:
        doc = Document.query.get_or_404(doc_id)
        file_path = doc.file_path
        
        # Security check: ensure file path is within uploads directory
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        full_path = os.path.join(uploads_dir, file_path)
        
        if not os.path.abspath(full_path).startswith(os.path.abspath(uploads_dir)):
            logger.warning(f"Attempted path traversal: {full_path}")
            return jsonify({'error': 'Invalid file path'}), 403
        
        if not os.path.exists(full_path):
            logger.warning(f"File not found: {full_path}")
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(full_path, mimetype=doc.mime_type or 'application/octet-stream')
        
    except Exception as e:
        logger.error(f"Error serving document: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/documents/<int:doc_id>/verify', methods=['POST'])
@login_required
@admin_only
def verify_document(doc_id):
    """Verify or reject a driver document"""
    from models import Document
    
    try:
        doc = Document.query.get_or_404(doc_id)
        data = request.get_json() or {}
        
        action = data.get('action')  # 'approve' or 'reject'
        notes = data.get('notes', '')
        
        if action == 'approve':
            doc.verification_status = 'Verified'
            doc.verified_by = current_user.id
            doc.verified_at = datetime.utcnow()
            doc.verification_notes = notes
            message = 'Document verified successfully'
        elif action == 'reject':
            reason = data.get('reason', 'Does not meet requirements')
            doc.verification_status = 'Rejected'
            doc.rejection_reason = reason
            doc.verification_notes = notes
            message = 'Document rejected'
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        
        db.session.commit()
        
        logger.info(f"Admin {current_user.id} {action}ed document {doc_id}")
        
        return jsonify({'success': True, 'message': message}), 200
    
    except Exception as e:
        logger.error(f"Error verifying document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/driver-onboarding/<int:driver_id>', methods=['GET'])
@login_required
@admin_only
def review_driver_onboarding(driver_id):
    """Review a driver's complete onboarding status"""
    from models import DriverOnboarding, Document, Driver
    
    driver = Driver.query.get_or_404(driver_id)
    onboarding = DriverOnboarding.query.filter_by(driver_id=driver_id).first()
    
    if not onboarding:
        flash('No onboarding record found for this driver', 'warning')
        return redirect(url_for('admin.drivers_page'))
    
    documents = Document.query.filter_by(onboarding_id=onboarding.id).all()
    
    # Calculate document completion
    doc_types = {doc.document_type: doc for doc in documents}
    required_docs = ['national_id', 'driver_license', 'vehicle_insurance']
    
    return render_template(
        'admin/review_driver_onboarding.html',
        driver=driver,
        onboarding=onboarding,
        documents=documents,
        doc_types=doc_types,
        required_docs=required_docs
    )


@admin_bp.route('/driver-onboarding/<int:driver_id>/approve', methods=['POST'])
@login_required
@admin_only  
def approve_driver_onboarding(driver_id):
    """Approve a driver's onboarding"""
    from models import DriverOnboarding
    
    try:
        onboarding = DriverOnboarding.query.filter_by(driver_id=driver_id).first_or_404()
        
        onboarding.status = 'Approved'
        onboarding.approval_stage = 3
        onboarding.approved_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Admin {current_user.id} approved driver {driver_id} onboarding")
        
        return jsonify({'success': True, 'message': 'Driver approved successfully'}), 200
    
    except Exception as e:
        logger.error(f"Error approving driver: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/driver-onboarding/<int:driver_id>/reject', methods=['POST'])
@login_required
@admin_only
def reject_driver_onboarding(driver_id):
    """Reject a driver's onboarding"""
    from models import DriverOnboarding
    
    try:
        onboarding = DriverOnboarding.query.filter_by(driver_id=driver_id).first_or_404()
        data = request.get_json() or {}
        
        reason = data.get('reason', 'Documents do not meet requirements')
        details = data.get('details', {})
        
        onboarding.status = 'Rejected'
        onboarding.rejected_at = datetime.utcnow()
        onboarding.rejection_reason = reason
        onboarding.rejection_details = details
        
        db.session.commit()
        
        logger.info(f"Admin {current_user.id} rejected driver {driver_id} onboarding")
        
        return jsonify({'success': True, 'message': 'Driver onboarding rejected'}), 200
    
    except Exception as e:
        logger.error(f"Error rejecting driver: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500





# ===================== STATISTICS ENDPOINTS =====================

@admin_bp.route('/stats/avg-delivery-time', methods=['GET'])
@login_required
@admin_only
def get_avg_delivery_time():
    """Get average delivery time for completed deliveries"""
    try:
        # Get all completed deliveries with both start and end times
        completed_deliveries = Delivery.query.filter(
            Delivery.status == 'Delivered',
            Delivery.started_at.isnot(None),
            Delivery.completed_at.isnot(None)
        ).all()
        
        if not completed_deliveries:
            return jsonify({'avg_time': 0}), 200
        
        # Calculate average delivery time in minutes
        total_time = timedelta(0)
        for delivery in completed_deliveries:
            elapsed = delivery.completed_at - delivery.started_at
            total_time += elapsed
        
        avg_minutes = total_time.total_seconds() / len(completed_deliveries) / 60
        
        return jsonify({'avg_time': round(avg_minutes, 1)}), 200
    
    except Exception as e:
        logger.error(f"Error calculating average delivery time: {e}")
        return jsonify({'error': str(e), 'avg_time': 0}), 500

