#!/usr/bin/env python
"""
Script to add service_type column to drivers table
Run this if you have an existing database and want to add the service_type field
without deleting all data.
"""
import os
from app import app, db
from models import Driver

def add_service_type_column():
    """Add service_type column to drivers table if it doesn't exist"""
    with app.app_context():
        try:
            # Try to access the service_type attribute to see if column exists
            test_driver = Driver.query.first()
            if test_driver:
                _ = test_driver.service_type
                print('✓ service_type column already exists')
                return True
        except:
            pass
        
        # Column doesn't exist, add it using SQLAlchemy
        try:
            from sqlalchemy import String
            
            # Get the database connection
            inspector = db.inspect(db.engine)
            
            # Check if column exists
            columns = [col['name'] for col in inspector.get_columns('drivers')]
            
            if 'service_type' not in columns:
                print('Adding service_type column to drivers table...')
                
                # Use raw SQL to add the column
                with db.engine.connect() as conn:
                    # SQLite compatible SQL
                    conn.execute(db.text(
                        "ALTER TABLE drivers ADD COLUMN service_type VARCHAR(50) DEFAULT 'Package'"
                    ))
                    conn.commit()
                
                print('✓ service_type column added successfully')
                return True
            else:
                print('✓ service_type column already exists')
                return True
                
        except Exception as e:
            print(f'✗ Error adding column: {e}')
            print('Alternative: Run reset_database.py to recreate all tables with the new schema')
            return False

if __name__ == '__main__':
    success = add_service_type_column()
    if success:
        print('\n✓ Database migration complete!')
    else:
        print('\n✗ Migration failed - consider resetting the database')
