#!/usr/bin/env python3
"""
Database migration script to add is_suspect column to existing database
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Add is_suspect column to face_logs table if it doesn't exist"""
    db_path = Path("data/database.db")
    
    if not db_path.exists():
        print("Database doesn't exist yet - will be created with new schema")
        return True
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if is_suspect column exists
            cursor.execute("PRAGMA table_info(face_logs)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'is_suspect' not in columns:
                print("Adding is_suspect column to face_logs table...")
                cursor.execute("ALTER TABLE face_logs ADD COLUMN is_suspect BOOLEAN DEFAULT 0")
                conn.commit()
                print("Successfully added is_suspect column")
            else:
                print("is_suspect column already exists")
                
            return True
            
    except Exception as e:
        print(f"Error migrating database: {e}")
        return False

if __name__ == "__main__":
    if migrate_database():
        print("✓ Database migration completed successfully")
    else:
        print("✗ Database migration failed")
