"""Set profile picture for driver"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'delivery_system.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Update driver 1's profile picture to the latest profile pic
    # Using the latest timestamp from the file listing
    cursor.execute(
        "UPDATE drivers SET profile_picture = ? WHERE id = ?",
        ('driver_1_profile_pic_1775834153.637355.jpg', 1)
    )
    
    # Check if update was successful
    cursor.execute("SELECT id, full_name, profile_picture FROM drivers WHERE id = 1")
    result = cursor.fetchone()
    
    if result:
        print(f"✓ Updated driver {result[0]} ({result[1]}) profile picture: {result[2]}")
    else:
        print("✗ Driver not found")
    
    conn.commit()
except Exception as e:
    print(f"✗ Error: {e}")
    conn.rollback()
finally:
    conn.close()
