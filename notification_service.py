"""
Notification Service
Handles: push notifications, SMS, email, in-app notifications, webhooks
Integration points: Firebase Cloud Messaging (FCM), Twilio SMS, Flask-Mail
"""
import logging
from datetime import datetime
from decimal import Decimal
import json

from database import db
from models import Notification, DeviceToken, Driver, Customer

logger = logging.getLogger(__name__)


def create_notification(recipient_id, recipient_type, title, body, notification_type,
                       channels='in-app', delivery_id=None, order_id=None, data=None):
    """
    Create a new notification and store it
    
    Args:
        recipient_id: User ID (driver or customer)
        recipient_type: 'driver' or 'customer'
        title: Notification title
        body: Notification body
        notification_type: Type code (e.g., 'delivery_offer', 'order_update')
        channels: Comma-separated list of channels (in-app, push, sms, email)
        delivery_id: Associated delivery ID (optional)
        order_id: Associated order ID (optional)
        data: Dict of extra data to include (will be JSON-encoded)
    
    Returns:
        Notification object or None
    """
    try:
        notification = Notification(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            title=title,
            body=body,
            notification_type=notification_type,
            channels=channels,
            status='pending',
            delivery_id=delivery_id,
            order_id=order_id,
            data=data or {}
        )
        
        db.session.add(notification)
        db.session.commit()
        
        logger.info(f"Created notification {notification.id} for {recipient_type} {recipient_id}")
        
        # Queue for sending
        queue_notification_send(notification.id)
        
        return notification
    
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        db.session.rollback()
        return None


def queue_notification_send(notification_id):
    """
    Queue a notification for sending (via SMS, push, email)
    In production, this would be sent to a task queue (Celery, RQ)
    For now, just mark it as pending
    """
    try:
        notification = db.session.get(Notification, notification_id)
        if not notification:
            return False
        
        # In production, send to task queue
        # For MVP, just mark as sent (implement actual sending in phase 2)
        notification.status = 'sent'
        notification.sent_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Queued notification {notification_id} for sending")
        return True
    
    except Exception as e:
        logger.error(f"Error queuing notification: {e}")
        return False


def send_push_notification(user_id, user_type, title, body, data=None):
    """
    Send push notification to mobile device
    Requires Firebase Cloud Messaging (FCM) setup
    
    Args:
        user_id: Driver or customer ID
        user_type: 'driver' or 'customer'
        title: Notification title
        body: Notification body
        data: Dict of extra data
    
    Returns:
        True if queued, False otherwise
    
    TODO: Implement FCM integration
    - Get device tokens from DeviceToken table
    - Build FCM payload
    - Send via FCM API (use firebase-admin library)
    - Handle errors and retries
    """
    try:
        # Get device tokens for user
        tokens = DeviceToken.query.filter(
            DeviceToken.user_id == user_id,
            DeviceToken.user_type == user_type,
            DeviceToken.is_active == True
        ).all()
        
        if not tokens:
            logger.warning(f"No device tokens found for {user_type} {user_id}")
            return False
        
        logger.info(f"Would send push to {len(tokens)} devices for {user_type} {user_id}")
        # TODO: Actually send via FCM
        return True
    
    except Exception as e:
        logger.error(f"Error in send_push_notification: {e}")
        return False


def send_sms_notification(phone_number, message):
    """
    Send SMS notification via Twilio
    
    Args:
        phone_number: Phone number (international format)
        message: SMS message text
    
    Returns:
        True if sent, False otherwise
    
    TODO: Implement Twilio integration
    - Set up Twilio account and credentials
    - Use twilio-python library
    - Handle responses and errors
    - Log attempts in database
    """
    try:
        logger.info(f"Would send SMS to {phone_number}: {message}")
        # TODO: Actually send via Twilio
        return True
    
    except Exception as e:
        logger.error(f"Error in send_sms_notification: {e}")
        return False


def send_email_notification(recipient_email, subject, template_name, data=None):
    """
    Send email notification via Flask-Mail
    
    Args:
        recipient_email: Email address
        subject: Email subject
        template_name: Name of email template (e.g., 'order_confirmation.txt')
        data: Dict of template variables
    
    Returns:
        True if queued, False otherwise
    
    TODO: Implement Flask-Mail integration
    - Set up email templates in templates/emails/
    - Render templates with data
    - Send via SMTP
    - Log in database
    """
    try:
        logger.info(f"Would send email to {recipient_email}: {subject}")
        # TODO: Actually send via Flask-Mail
        return True
    
    except Exception as e:
        logger.error(f"Error in send_email_notification: {e}")
        return False


def mark_notification_as_read(notification_id):
    """Mark notification as read by recipient"""
    try:
        notification = db.session.get(Notification, notification_id)
        if notification:
            notification.read_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Marked notification {notification_id} as read")
            return True
        return False
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return False


def get_unread_notifications(user_id, user_type, limit=20):
    """Get unread notifications for user"""
    try:
        notifications = Notification.query.filter(
            Notification.recipient_id == user_id,
            Notification.recipient_type == user_type,
            Notification.read_at == None
        ).order_by(
            Notification.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                'id': n.id,
                'title': n.title,
                'body': n.body,
                'type': n.notification_type,
                'created_at': n.created_at.isoformat(),
                'data': n.data
            }
            for n in notifications
        ]
    
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return []


def register_device_token(user_id, user_type, token, platform, device_name=None):
    """
    Register a device token for push notifications
    
    Args:
        user_id: Driver or customer ID
        user_type: 'driver' or 'customer'
        token: FCM or APNs token
        platform: 'ios', 'android', or 'web'
        device_name: Optional device name
    
    Returns:
        DeviceToken object or None
    """
    try:
        # Check if token already exists
        existing = DeviceToken.query.filter_by(token=token).first()
        if existing:
            existing.last_used_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Updated existing device token for {user_type} {user_id}")
            return existing
        
        # Create new token
        device_token = DeviceToken(
            user_id=user_id,
            user_type=user_type,
            token=token,
            platform=platform,
            device_name=device_name
        )
        
        db.session.add(device_token)
        db.session.commit()
        
        logger.info(f"Registered device token for {user_type} {user_id} ({platform})")
        return device_token
    
    except Exception as e:
        logger.error(f"Error registering device token: {e}")
        db.session.rollback()
        return None


def send_webhook(event_type, entity_type, entity_id, data):
    """
    Send webhook notification to external systems
    
    Args:
        event_type: 'created', 'updated', 'completed', 'cancelled'
        entity_type: 'order', 'delivery', 'driver', etc.
        entity_id: ID of entity
        data: Dict with entity data
    
    TODO: Implement webhook system
    - Store webhook subscriptions in database
    - Send HTTP POST to registered URLs
    - Implement retry logic
    - Log webhook attempts
    """
    logger.info(f"Would send webhook: {event_type} {entity_type} {entity_id}")
    return True


class NotificationBatch:
    """Helper for batching notifications (for efficiency)"""
    
    def __init__(self):
        self.notifications = []
    
    def add(self, recipient_id, recipient_type, title, body, notification_type,
            channels='in-app', delivery_id=None, order_id=None, data=None):
        """Add notification to batch"""
        self.notifications.append({
            'recipient_id': recipient_id,
            'recipient_type': recipient_type,
            'title': title,
            'body': body,
            'notification_type': notification_type,
            'channels': channels,
            'delivery_id': delivery_id,
            'order_id': order_id,
            'data': data
        })
    
    def commit(self):
        """Save all notifications to database"""
        try:
            for notif_data in self.notifications:
                notification = Notification(**notif_data, status='pending')
                db.session.add(notification)
            
            db.session.commit()
            logger.info(f"Committed batch of {len(self.notifications)} notifications")
            return len(self.notifications)
        
        except Exception as e:
            logger.error(f"Error committing notification batch: {e}")
            db.session.rollback()
            return 0
