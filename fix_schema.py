#!/usr/bin/env python
"""Fix database schema by adding missing columns"""

from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # Fix 1: Add service_type to deliveries table
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('deliveries')]
        
        if 'service_type' not in columns:
            print('Adding service_type column to deliveries table...')
            db.session.execute(text("ALTER TABLE deliveries ADD COLUMN service_type VARCHAR(50) DEFAULT 'package_delivery'"))
            db.session.commit()
            print('✓ Column added successfully!')
        else:
            print('✓ deliveries.service_type already exists')
        
        # Fix 2: Add service_types to drivers table
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('drivers')]
        
        if 'service_types' not in columns:
            print('Adding service_types column to drivers table...')
            db.session.execute(text("ALTER TABLE drivers ADD COLUMN service_types VARCHAR(100) DEFAULT 'both'"))
            db.session.commit()
            print('✓ Column added successfully!')
        else:
            print('✓ drivers.service_types already exists')
        
        # Fix 3: Add responded_at to delivery_requests table
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('delivery_requests')]
        
        if 'responded_at' not in columns:
            print('Adding responded_at column to delivery_requests table...')
            db.session.execute(text("ALTER TABLE delivery_requests ADD COLUMN responded_at DATETIME"))
            db.session.commit()
            print('✓ Column added successfully!')
        else:
            print('✓ delivery_requests.responded_at already exists')
            
        # Verify all columns
        print('\n✓ All schema fixes completed!')
        print('\nVerifying columns...')
        
        for table in ['deliveries', 'drivers', 'delivery_requests']:
            inspector = db.inspect(db.engine)
            if table == 'deliveries':
                expected = 'service_type'
            elif table == 'drivers':
                expected = 'service_types'
            else:
                expected = 'responded_at'
            
            columns = [col['name'] for col in inspector.get_columns(table)]
            if expected in columns:
                print(f'  ✓ {table}.{expected}')
            else:
                print(f'  ✗ {table}.{expected} - MISSING!')
            
    except Exception as e:
        print(f'Error: {e}')
        db.session.rollback()

print('\nDone!')
