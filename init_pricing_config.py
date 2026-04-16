#!/usr/bin/env python
"""Initialize pricing configuration in database."""

import sys
sys.path.insert(0, '.')

from app import app, db
from models import PricingConfig

def init_pricing_config():
    """Create pricing_config table and insert default values."""
    with app.app_context():
        try:
            # Check if config already exists
            existing = PricingConfig.query.filter_by(id=1).first()
            if existing:
                print("✓ Pricing config already exists in database")
                print(f"  Driver Commission: {existing.driver_commission_percent}%")
                print(f"  Peak Multiplier: {existing.peak_multiplier}x")
                return True
        except Exception as e:
            print(f"Note: {str(e)}")
        
        try:
            # Create all tables (will only create missing ones)
            db.create_all()
            print("✓ Tables created/verified")
            
            # Check again if config exists
            existing = PricingConfig.query.filter_by(id=1).first()
            if not existing:
                # Create default config
                config = PricingConfig(
                    id=1,
                    driver_commission_percent=75.0,
                    peak_multiplier=1.5,
                    cancellation_fee=1.50,
                    wait_time_fee=0.15,
                    bonus_per_delivery=0.50,
                    referral_bonus=5.00
                )
                db.session.add(config)
                db.session.commit()
                print("✓ Default pricing config created:")
                print("  - Driver Commission: 75%")
                print("  - Platform Commission: 25%")
                print("  - Peak Multiplier: 1.5x")
                print("  - Cancellation Fee: ₵1.50")
                print("  - Wait Time Fee: ₵0.15/min")
                print("  - Bonus per Delivery: ₵0.50")
                print("  - Referral Bonus: ₵5.00")
            else:
                print("✓ Configuration already initialized")
                
            return True
            
        except Exception as e:
            print(f"✗ Error during initialization: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = init_pricing_config()
    sys.exit(0 if success else 1)
