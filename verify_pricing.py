#!/usr/bin/env python
"""Verify pricing configuration routes."""

import sys
sys.path.insert(0, '.')

from app import app

# Get all registered routes
routes = {}
for rule in app.url_map.iter_rules():
    if 'admin' in rule.rule and 'pricing' in rule.rule:
        routes[rule.rule] = rule.methods

print("✓ Flask route configuration:")
print("-" * 60)
for route, methods in sorted(routes.items()):
    methods_str = ','.join(m for m in methods if m not in ['HEAD', 'OPTIONS'])
    print(f"  {route:<40} [{methods_str}]")

if not routes:
    print("  ✗ No pricing routes found!")
else:
    print(f"\n✓ Found {len(routes)} pricing-related route(s)")
    
    # Test the routes by checking if they exist
    from app import db
    from models import PricingConfig
    
    with app.app_context():
        try:
            config = PricingConfig.get_config()
            print("\n✓ Pricing configuration loaded from database:")
            print(f"  - Driver Commission: {config.driver_commission_percent}%")
            print(f"  - Peak Multiplier: {config.peak_multiplier}x")
            print(f"  - Cancellation Fee: ₵{config.cancellation_fee:.2f}")
            print(f"  - Wait Time Fee: ₵{config.wait_time_fee:.2f}")
            print(f"  - Bonus per Delivery: ₵{config.bonus_per_delivery:.2f}")
            print(f"  - Referral Bonus: ₵{config.referral_bonus:.2f}")
        except Exception as e:
            print(f"  ✗ Error loading configuration: {e}")
