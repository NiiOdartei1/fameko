"""Add profile_picture column to drivers table"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'delivery_system.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if column already exists
    cursor.execute("PRAGMA table_info(drivers)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'profile_picture' not in columns:
        cursor.execute("ALTER TABLE drivers ADD COLUMN profile_picture VARCHAR(255)")
        print("✓ Added profile_picture column to drivers table")
    else:
        print("✓ profile_picture column already exists")
    
    conn.commit()
except Exception as e:
    print(f"✗ Error: {e}")
    conn.rollback()
finally:
    conn.close()
