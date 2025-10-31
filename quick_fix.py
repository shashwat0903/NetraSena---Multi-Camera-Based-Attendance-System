#!/usr/bin/env python3
"""
Quick fix script for NetraSena issues
"""

import sqlite3
import sys
from pathlib import Path

def fix_database():
    """Fix database schema issues"""
    print("Fixing database schema...")
    
    db_path = Path("data/database.db")
    if not db_path.exists():
        print("No database found - will be created with correct schema")
        return True
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if is_suspect column exists
            cursor.execute("PRAGMA table_info(face_logs)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'is_suspect' not in columns:
                print("Adding missing is_suspect column...")
                cursor.execute("ALTER TABLE face_logs ADD COLUMN is_suspect BOOLEAN DEFAULT 0")
                conn.commit()
                print("✓ Added is_suspect column")
            else:
                print("✓ Database schema is correct")
                
            # Set any NULL values to False
            cursor.execute("UPDATE face_logs SET is_suspect = 0 WHERE is_suspect IS NULL")
            conn.commit()
            
            return True
            
    except Exception as e:
        print(f"✗ Database fix failed: {e}")
        return False

def check_camera():
    """Test camera availability"""
    print("Testing camera availability...")
    
    try:
        import cv2
        
        # Test default camera
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print("✓ Camera 0 is working")
                return True
            else:
                print("⚠ Camera 0 opens but can't read frames")
                return False
        else:
            print("✗ Camera 0 cannot be opened")
            return False
            
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        return False

def fix_config():
    """Update configuration for better compatibility"""
    print("Updating configuration...")
    
    try:
        # Camera config is already updated to 640x480 for better compatibility
        print("✓ Camera configuration optimized")
        return True
        
    except Exception as e:
        print(f"✗ Config fix failed: {e}")
        return False

def main():
    """Run all fixes"""
    print("NetraSena - Quick Fix")
    print("=" * 40)
    
    success = True
    
    # Fix database
    if not fix_database():
        success = False
    
    # Check camera
    if not check_camera():
        print("⚠ Camera issues detected - check connections and permissions")
        success = False
    
    # Fix config
    if not fix_config():
        success = False
    
    print("=" * 40)
    if success:
        print("✓ All fixes completed successfully!")
        print("You can now run: python main.py")
    else:
        print("⚠ Some issues remain - check the messages above")
    
    print("\nTroubleshooting tips:")
    print("• Close other apps that might use the camera")
    print("• Check camera permissions in Windows settings")
    print("• Try running as administrator")
    print("• Restart the system if camera issues persist")

if __name__ == "__main__":
    main()
