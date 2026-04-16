#!/usr/bin/env python
import os
from app import app, db

# Remove old database
db_file = 'instance/delivery_system.db'
if os.path.exists(db_file):
    os.remove(db_file)
    print(f'✓ Deleted old database: {db_file}')
else:
    print(f'  No existing database to delete')

# Create new database with all tables
with app.app_context():
    db.create_all()
    print('✓ Created new database with all tables')
    print('\n✓ All tables created:')
    for table_name in sorted(db.metadata.tables.keys()):
        print(f'  - {table_name}')
    print('\n✓ Database initialization complete!')
