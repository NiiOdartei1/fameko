"""
Delivery Retry Queue Service
Handles delivery queue management, retries, escalation, and dead-letter handling
Used for unassigned deliveries that need retry or manual intervention
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from database import db
from models import Delivery, DeliveryRequest, Notification
from delivery_assignment_engine import retry_delivery_assignment, send_delivery_offers

logger = logging.getLogger(__name__)


class DeliveryQueue:
    """Main queue manager for delivery assignment"""
    
    @staticmethod
    def process_unassigned_deliveries():
        """
        Background task: Process unassigned deliveries
        - Find deliveries pending for >5 mins
        - Retry assignment with escalation
        Called periodically (e.g., every 5 minutes)
        """
        try:
            now = datetime.utcnow()
            cutoff_time = now - timedelta(minutes=5)
            
            # Find deliveries that are still pending and created >5 mins ago
            unassigned = Delivery.query.filter(
                Delivery.status == 'Pending',
                Delivery.created_at < cutoff_time,
                ~Delivery.id.in_(
                    db.session.query(DeliveryRequest.delivery_id).filter(
                        DeliveryRequest.status == 'Accepted'
                    )
                )
            ).all()
            
            logger.info(f"Found {len(unassigned)} unassigned deliveries to retry")
            
            for delivery in unassigned:
                # Check how many attempts already made
                attempt_count = DeliveryRequest.query.filter(
                    DeliveryRequest.delivery_id == delivery.id,
                    DeliveryRequest.status.in_(['Declined', 'Expired'])
                ).count()
                
                attempt_num = attempt_count + 1
                
                if attempt_num <= 3:
                    # Retry with escalation
                    retry_delivery_assignment(delivery.id, attempt_num)
                    logger.info(f"Retry {attempt_num} for delivery {delivery.id}")
                else:
                    # Mark for manual intervention
                    logger.warning(f"Delivery {delivery.id} exceeded max retries - needs manual assignment")
                    DeliveryQueue._mark_dead_letter(delivery.id)
            
            return len(unassigned)
        
        except Exception as e:
            logger.error(f"Error processing unassigned deliveries: {e}")
            return 0
    
    @staticmethod
    def _mark_dead_letter(delivery_id):
        """Mark delivery as dead-letter (needs manual intervention)"""
        try:
            delivery = db.session.get(Delivery, delivery_id)
            if delivery:
                # Create notification for admin
                notification = Notification(
                    recipient_id=1,  # TODO: Get admin ID from config
                    recipient_type='admin',
                    title='Dead Letter: Unassigned Delivery',
                    body=f'Delivery {delivery_id} could not be auto-assigned after max retries',
                    notification_type='dead_letter',
                    channels='in-app,email',
                    status='pending',
                    delivery_id=delivery_id,
                    data={
                        'delivery_id': delivery_id,
                        'order_id': delivery.order_id,
                        'pickup_location': delivery.pickup_location,
                        'reason': 'No drivers available after 3 attempts'
                    }
                )
                db.session.add(notification)
                db.session.commit()
                logger.warning(f"Marked delivery {delivery_id} as dead-letter")
        
        except Exception as e:
            logger.error(f"Error marking dead-letter: {e}")
    
    @staticmethod
    def get_queue_stats():
        """Get queue statistics"""
        try:
            pending = Delivery.query.filter_by(status='Pending').count()
            assigned = Delivery.query.filter_by(status='Assigned').count()
            in_transit = Delivery.query.filter_by(status='In Transit').count()
            delivered = Delivery.query.filter_by(status='Delivered').count()
            cancelled = Delivery.query.filter_by(status='Cancelled').count()
            
            # Get pending offers
            pending_offers = DeliveryRequest.query.filter_by(status='Pending').count()
            
            # Get avg time in queue
            oldest_pending = Delivery.query.filter_by(status='Pending').order_by(
                Delivery.created_at.asc()
            ).first()
            
            oldest_age_minutes = 0
            if oldest_pending:
                age = datetime.utcnow() - oldest_pending.created_at
                oldest_age_minutes = int(age.total_seconds() / 60)
            
            return {
                'pending': pending,
                'assigned': assigned,
                'in_transit': in_transit,
                'delivered': delivered,
                'cancelled': cancelled,
                'pending_offers': pending_offers,
                'oldest_pending_age_minutes': oldest_age_minutes
            }
        
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {}


class RetryScheduler:
    """Manages retry scheduling for failed deliveries"""
    
    @staticmethod
    def schedule_retry(delivery_id, delay_seconds=300):
        """
        Schedule a retry for a delivery
        delay_seconds: Time to wait before retry (default 5 mins)
        
        TODO: Use APScheduler or Celery for production
        For MVP, this just returns the scheduled time
        """
        retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        logger.info(f"Scheduled retry for delivery {delivery_id} at {retry_at}")
        return retry_at
    
    @staticmethod
    def escalate_delivery(delivery_id):
        """
        Escalate delivery with surge pricing and premium incentives
        - Increase peak_multiplier (1.0 → 1.5x)
        - Add bonus incentive for first acceptance
        - Send to all available drivers (not just nearby)
        """
        try:
            delivery = db.session.get(Delivery, delivery_id)
            if not delivery:
                return False
            
            # Increase multiplier
            current_multiplier = delivery.peak_multiplier or 1.0
            new_multiplier = min(current_multiplier + 0.25, 1.5)
            delivery.peak_multiplier = new_multiplier
            
            # Add bonus
            delivery.bonuses = (delivery.bonuses or 0) + Decimal('2.00')
            
            db.session.commit()
            
            logger.info(f"Escalated delivery {delivery_id}: multiplier={new_multiplier}, bonus={delivery.bonuses}")
            
            # Send offers to expanded pool
            send_delivery_offers(delivery_id, num_offers=10)
            
            return True
        
        except Exception as e:
            logger.error(f"Error escalating delivery: {e}")
            return False


class DeliveryMetrics:
    """Track queue metrics and SLAs"""
    
    @staticmethod
    def get_sla_metrics(hours=24):
        """
        Get delivery SLA metrics
        - Avg time to assignment
        - Avg time to pickup
        - Avg time to delivery
        - % delivered within SLA
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            deliveries = Delivery.query.filter(
                Delivery.created_at >= cutoff
            ).all()
            
            times_to_assignment = []
            times_to_delivery = []
            
            for d in deliveries:
                if d.assigned_at:
                    time_to_assign = (d.assigned_at - d.created_at).total_seconds() / 60
                    times_to_assignment.append(time_to_assign)
                
                if d.completed_at:
                    time_to_deliver = (d.completed_at - d.created_at).total_seconds() / 60
                    times_to_delivery.append(time_to_deliver)
            
            avg_assign_time = sum(times_to_assignment) / len(times_to_assignment) if times_to_assignment else 0
            avg_deliver_time = sum(times_to_delivery) / len(times_to_delivery) if times_to_delivery else 0
            
            # SLA: 30 mins to assignment, 60 mins to delivery
            sla_met = sum(1 for t in times_to_assignment if t <= 30) if times_to_assignment else 0
            sla_compliance = (sla_met / len(times_to_assignment) * 100) if times_to_assignment else 0
            
            return {
                'sample_size': len(deliveries),
                'avg_time_to_assignment_minutes': round(avg_assign_time, 2),
                'avg_time_to_delivery_minutes': round(avg_deliver_time, 2),
                'sla_compliance_percent': round(sla_compliance, 2),
                'sla_target': '30 min to assignment, 60 min to delivery'
            }
        
        except Exception as e:
            logger.error(f"Error calculating SLA metrics: {e}")
            return {}


def start_background_tasks():
    """
    Initialize background tasks for queue management
    TODO: In production, use APScheduler or Celery
    For MVP, this could be called periodically by a cron job
    """
    logger.info("Starting delivery queue background tasks")
    
    # Check for expired offers every minute
    # DeliveryQueue.check_expired_offers()
    
    # Process unassigned deliveries every 5 minutes
    # DeliveryQueue.process_unassigned_deliveries()
    
    # TODO: Set up actual scheduler (APScheduler)
    # from apscheduler.schedulers.background import BackgroundScheduler
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(DeliveryQueue.process_unassigned_deliveries, 'interval', minutes=5)
    # scheduler.add_job(check_expired_delivery_offers, 'interval', minutes=1)
    # scheduler.start()
