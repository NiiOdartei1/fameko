"""
Data Models for Delivery System
Includes Order, Delivery, Driver, DriverLocation, OrderItem, Wallet
"""
from datetime import datetime, timedelta
from decimal import Decimal
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text, JSON, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship

from database import db


# ==================== ORDER MODELS ====================

class Order(db.Model):
    """
    Order model representing a delivery order
    Contains shipping information and order status
    """
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Order details
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(32), default='Pending')  # Pending, Approved, Cancelled, Delivered
    
    # Shipping information
    shipping_name = db.Column(db.String(120), nullable=False)
    shipping_address = db.Column(db.String(255), nullable=False)
    shipping_phone = db.Column(db.String(20), nullable=False)
    
    # Shipping coordinates (GPS)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Payment
    payment_method = db.Column(db.String(50), default='Cash on Delivery')
    payment_status = db.Column(db.String(20), default='Pending')  # Pending, Paid, Refunded
    
    # Tracking
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('Customer', back_populates='orders')
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')
    deliveries = db.relationship('Delivery', backref='order', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.id}>'


class OrderItem(db.Model):
    """Line items for an order"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    
    # Item details
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.Text, nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    total_price = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Item tracking
    status = db.Column(db.String(32), default='Pending')
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'


# ==================== DRIVER MODELS ====================

class Driver(UserMixin, db.Model):
    """
    Driver model with authentication and earnings tracking
    Bolt-like commission model
    """
    __tablename__ = 'drivers'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Personal Information
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    region = db.Column(db.String(100), nullable=False)  # Operating region (e.g., Ashanti, Greater Accra)
    
    # Authentication
    password_hash = db.Column(db.String(255), nullable=False)
    
    # License & Vehicle Information
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    license_expiry = db.Column(db.DateTime, nullable=True)
    vehicle_type = db.Column(db.String(50))  # Car, Motorcycle, Bicycle
    vehicle_number = db.Column(db.String(50))
    vehicle_model = db.Column(db.String(100), nullable=True)
    
    # Insurance
    insurance_policy_number = db.Column(db.String(100), nullable=True)
    insurance_expiry = db.Column(db.DateTime, nullable=True)
    
    # Status
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Suspended, Inactive
    is_online = db.Column(db.Boolean, default=False)
    
    # Service Types (JSON: package_delivery, personal_transportation, or both)
    service_types = db.Column(db.String(100), default='both')  # Values: 'package_delivery', 'personal_transportation', 'both'
    
    # Documents
    id_front_image = db.Column(db.String(255), nullable=True)
    id_back_image = db.Column(db.String(255), nullable=True)
    license_image = db.Column(db.String(255), nullable=True)
    vehicle_image = db.Column(db.String(255), nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    
    # Earnings & Statistics (Bolt-like)
    total_earnings = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    total_tips_earned = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    total_bonuses_earned = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    total_commissions_paid = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    
    # Statistics
    completed_deliveries = db.Column(db.Integer, default=0)
    cancelled_deliveries = db.Column(db.Integer, default=0)
    commission_rate = db.Column(db.Float, default=25.0)  # Platform commission percentage
    rating = db.Column(db.Float, default=5.0)
    
    # Timestamps
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    deliveries = db.relationship('Delivery', backref='driver', lazy=True)
    location = db.relationship('DriverLocation', backref='driver', uselist=False, cascade='all, delete-orphan')
    wallet = db.relationship('Wallet', primaryjoin='Driver.id == Wallet.driver_id', foreign_keys='Wallet.driver_id', backref='driver', uselist=False)
    ratings = db.relationship('DriverRating', backref='driver', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Driver {self.full_name}>'


class DriverLocation(db.Model):
    """Real-time driver location tracking"""
    __tablename__ = 'driver_locations'
    
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), primary_key=True)
    
    # Current GPS coordinates
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Current delivery
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=True)
    
    # Metadata
    accuracy = db.Column(db.Float, nullable=True)  # GPS accuracy in meters
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DriverLocation driver={self.driver_id}>'


class DriverRating(db.Model):
    """Customer ratings for drivers"""
    __tablename__ = 'driver_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=False)
    
    rating = db.Column(db.Float, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    delivery = db.relationship('Delivery', backref='customer_rating', uselist=False)


# ==================== DELIVERY MODELS ====================

class Delivery(db.Model):
    """
    Core delivery record with Bolt-like pricing model
    Tracks route, pricing, and delivery status
    """
    __tablename__ = 'deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # References
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    
    # Pickup & Dropoff
    pickup_location = db.Column(db.String(255), nullable=False)
    pickup_address = db.Column(db.String(255), nullable=True)
    pickup_lat = db.Column(db.Float, nullable=True)
    pickup_lng = db.Column(db.Float, nullable=True)
    
    dropoff_location = db.Column(db.String(255), nullable=False)
    dropoff_address = db.Column(db.String(255), nullable=True)
    dropoff_lat = db.Column(db.Float, nullable=True)
    dropoff_lng = db.Column(db.Float, nullable=True)
    
    # Route Information
    route_coords = db.Column(db.Text, nullable=True)  # JSON: [[lng, lat], [lng, lat], ...]
    distance_km = db.Column(db.Float, nullable=True)
    estimated_duration_minutes = db.Column(db.Integer, nullable=True)
    
    # Pricing Breakdown (Bolt-like Commission Model)
    base_fare = db.Column(db.Numeric(12, 2), default=0)  # Core delivery fare
    per_km_rate = db.Column(db.Numeric(12, 2), nullable=True)  # Variable cost per kilometer
    
    # Earnings Split
    platform_commission = db.Column(db.Numeric(12, 2), default=0)  # What platform keeps
    driver_commission_percent = db.Column(db.Float, default=75.0)  # Driver gets % of base_fare
    
    # Additional Fees
    tips = db.Column(db.Numeric(12, 2), default=0)  # Direct to driver
    bonuses = db.Column(db.Numeric(12, 2), default=0)  # Platform bonus to driver
    cancellation_fee = db.Column(db.Numeric(12, 2), default=0)
    wait_time_fee = db.Column(db.Numeric(12, 2), default=0)
    
    # Multipliers
    peak_multiplier = db.Column(db.Float, default=1.0)  # Peak hour pricing
    
    # Final Calculations
    total_fare = db.Column(db.Numeric(12, 2), nullable=True)  # Total for customer
    actual_driver_earnings = db.Column(db.Numeric(12, 2), nullable=True)  # What driver gets
    total_platform_fees = db.Column(db.Numeric(12, 2), default=0)  # What platform keeps
    
    # Status
    status = db.Column(db.String(30), default='Pending')  # Pending, Assigned, In Transit, Delivered, Cancelled
    
    # Service Type
    service_type = db.Column(db.String(50), default='package_delivery')  # package_delivery or personal_transportation
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)  # Driver left pickup
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Wallet
    wallet_transaction_id = db.Column(db.Integer, db.ForeignKey('wallet_transactions.id'), nullable=True)
    
    # Metadata
    notes = db.Column(db.Text, nullable=True)
    
    wallet_transaction = db.relationship('WalletTransaction', foreign_keys='Delivery.wallet_transaction_id', uselist=False)
    
    def calculate_driver_earnings(self):
        """Calculate final driver earnings"""
        # Driver gets commission_percent of base fare + tips + bonuses - wait time penalties
        base_commission = float(self.base_fare) * (self.driver_commission_percent / 100.0)
        additional = float(self.tips) + float(self.bonuses) - float(self.wait_time_fee)
        return Decimal(str(base_commission + additional))
    
    def __repr__(self):
        return f'<Delivery {self.id}>'


# ==================== CUSTOMER MODELS ====================

class Customer(UserMixin, db.Model):
    """Customer/Buyer model"""
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Address
    default_address = db.Column(db.String(255), nullable=True)
    default_latitude = db.Column(db.Float, nullable=True)
    default_longitude = db.Column(db.Float, nullable=True)
    
    # Account
    is_active = db.Column(db.Boolean, default=True)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('Order', back_populates='customer', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Customer {self.name}>'


# ==================== WALLET & FINANCE MODELS ====================

class Wallet(db.Model):
    """Driver wallet model"""
    __tablename__ = 'wallets'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), unique=True, nullable=False)
    
    # Balance
    balance = db.Column(db.Numeric(12, 2), default=0)
    
    # Totals
    total_credited = db.Column(db.Numeric(12, 2), default=0)
    total_debitted = db.Column(db.Numeric(12, 2), default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('WalletTransaction', backref='wallet', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Wallet driver_id={self.driver_id}>'


class WalletTransaction(db.Model):
    """Wallet transaction history"""
    __tablename__ = 'wallet_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.id'), nullable=False)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=True)
    
    # Transaction details
    transaction_type = db.Column(db.String(50), nullable=False)  # credit, debit, withdrawal
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Status
    status = db.Column(db.String(20), default='Completed')  # Pending, Completed, Failed
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<WalletTransaction {self.id}>'


# ==================== ADMIN MODELS ====================

class Admin(UserMixin, db.Model):
    """Admin user model"""
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Permissions
    can_manage_drivers = db.Column(db.Boolean, default=False)
    can_view_analytics = db.Column(db.Boolean, default=False)
    can_manage_orders = db.Column(db.Boolean, default=False)
    can_manage_admins = db.Column(db.Boolean, default=False)
    
    # Account
    is_active = db.Column(db.Boolean, default=True)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Admin {self.username}>'


# ==================== DELIVERY REQUEST MODELS ====================

class DeliveryRequest(db.Model):
    """Delivery offer sent to specific drivers"""
    __tablename__ = 'delivery_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=False)
    
    # Request status
    status = db.Column(db.String(20), default='Pending')  # Pending, Accepted, Declined, Expired
    
    # Timestamps
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<DeliveryRequest driver={self.driver_id} delivery={self.delivery_id}>'


# ==================== MESSAGING MODELS ====================


class Conversation(db.Model):
    """Conversation between a customer and a driver for a delivery"""
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_message_at = db.Column(db.DateTime, nullable=True)

    messages = db.relationship('Message', backref='conversation', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Conversation {self.id} delivery={self.delivery_id} customer={self.customer_id} driver={self.driver_id}>'


class Message(db.Model):
    """Individual message in a conversation"""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # 'customer' or 'driver'
    sender_id = db.Column(db.Integer, nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Message {self.id} conv={self.conversation_id} sender={self.sender_type}:{self.sender_id}>'


class CallLog(db.Model):
    """Simple call log for call attempts between parties"""
    __tablename__ = 'call_logs'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=True)
    caller_type = db.Column(db.String(20), nullable=False)
    caller_id = db.Column(db.Integer, nullable=False)
    callee_id = db.Column(db.Integer, nullable=False)
    initiated_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='initiated')  # initiated, accepted, rejected, missed
    duration_seconds = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f'<CallLog {self.id} caller={self.caller_type}:{self.caller_id} callee={self.callee_id} status={self.status}>'


# ==================== ONBOARDING & DOCUMENTS ====================

class DriverOnboarding(db.Model):
    """Driver onboarding and verification status"""
    __tablename__ = 'driver_onboarding'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    
    # Status
    status = db.Column(db.String(20), default='Pending')  # Pending, In Review, Approved, Rejected
    approval_stage = db.Column(db.Integer, default=1)  # 1=Basic Info, 2=Documents, 3=Verification
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    driver = db.relationship('Driver', backref='onboarding', uselist=False)
    documents = db.relationship('Document', backref='driver_onboarding', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<DriverOnboarding driver={self.driver_id} status={self.status}>'


class Document(db.Model):
    """Driver documents for verification"""
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    onboarding_id = db.Column(db.Integer, db.ForeignKey('driver_onboarding.id'), nullable=False)
    
    # Document info
    document_type = db.Column(db.String(50), nullable=False)  # license, insurance, etc
    file_path = db.Column(db.String(255), nullable=False)
    
    # Verification
    verification_status = db.Column(db.String(20), default='Pending')  # Pending, Verified, Rejected
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Document type={self.document_type}>'


# ==================== PAYMENT & EARNINGS ====================

class PaymentStatement(db.Model):
    """Weekly payment statements for drivers"""
    __tablename__ = 'payment_statements'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    
    # Period
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    
    # Earnings
    gross_earnings = db.Column(db.Numeric(12, 2), default=0)
    platform_fees = db.Column(db.Numeric(12, 2), default=0)
    tips_received = db.Column(db.Numeric(12, 2), default=0)
    net_payment = db.Column(db.Numeric(12, 2), default=0)
    
    # Stats
    deliveries_count = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, nullable=True)
    
    # Status
    payment_status = db.Column(db.String(20), default='Pending')  # Pending, Paid, Failed
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<PaymentStatement driver={self.driver_id} period={self.period_start.date()}>'


class RatingFeedback(db.Model):
    """Detailed rating feedback from customers"""
    __tablename__ = 'rating_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=True)
    
    # Rating details
    rating = db.Column(db.Float, nullable=False)  # 1-5
    category = db.Column(db.String(50), nullable=True)  # friendliness, professionalism, etc
    comment = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<RatingFeedback driver={self.driver_id} rating={self.rating}>'


class DriverEarningsMetric(db.Model):
    """Daily earnings metrics for drivers"""
    __tablename__ = 'driver_earnings_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    
    # Date
    date = db.Column(db.DateTime, nullable=False)
    
    # Earnings data
    total_earnings = db.Column(db.Numeric(12, 2), default=0)
    deliveries_completed = db.Column(db.Integer, default=0)
    deliveries_accepted = db.Column(db.Integer, default=0)
    acceptance_rate = db.Column(db.Float, nullable=True)
    
    # Performance
    average_rating = db.Column(db.Float, nullable=True)
    peak_hour = db.Column(db.String(10), nullable=True)  # e.g., "14:00"
    location = db.Column(db.String(255), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DriverEarningsMetric driver={self.driver_id} date={self.date.date()}>'


class Notification(db.Model):
    """Notifications for drivers and customers"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    recipient_type = db.Column(db.String(20))  # driver, customer, admin
    recipient_id = db.Column(db.Integer, nullable=False)
    
    # Notification content
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50))  # info, warning, alert, delivery_update

    # Delivery/Order links and delivery channels/status
    channels = db.Column(db.String(100), default='in-app')
    status = db.Column(db.String(50), default='pending')
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    data = db.Column(db.JSON, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Notification {self.id} to {self.recipient_type}:{self.recipient_id} status={self.status}>'

    # Backwards compatibility: some code uses `body` when creating notifications
    @property
    def body(self):
        return self.message

    @body.setter
    def body(self, value):
        self.message = value


# ==================== PRICING CONFIGURATION ====================

class PricingConfig(db.Model):
    """Platform pricing configuration - single record for system-wide settings"""
    __tablename__ = 'pricing_config'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Commission split
    driver_commission_percent = db.Column(db.Float, default=75.0)  # % of base fare driver gets
    
    # Pricing multipliers
    peak_multiplier = db.Column(db.Float, default=1.5)  # Peak hour surge pricing
    
    # Fixed fees
    cancellation_fee = db.Column(db.Numeric(12, 2), default=1.50)  # Fee for cancellations
    wait_time_fee = db.Column(db.Numeric(12, 2), default=0.15)  # Per minute wait fee
    bonus_per_delivery = db.Column(db.Numeric(12, 2), default=0.50)  # Bonus per delivery
    referral_bonus = db.Column(db.Numeric(12, 2), default=5.00)  # Referral bonus amount
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    
    @classmethod
    def get_config(cls):
        """Get or create the single pricing configuration record"""
        config = cls.query.filter_by(id=1).first()
        if not config:
            config = cls(id=1)
            db.session.add(config)
            db.session.commit()
        return config
    
    def __repr__(self):
        return f'<PricingConfig driver={self.driver_commission_percent}% peak={self.peak_multiplier}x>'
