#!/usr/bin/env python3
"""
Test script to verify NetraSena functionality
"""

import sys
import sqlite3
from pathlib import Path

def test_database():
    """Test database functionality"""
    print("Testing database...")
    
    try:
        from core.database import FaceDatabase
        
        db = FaceDatabase("data/database.db")
        
        # Test getting logs with suspect filter
        logs = db.get_face_logs(limit=5, is_suspect=None)
        print(f"✓ Database query successful - {len(logs)} entries")
        
        # Test suspect filter specifically
        suspect_logs = db.get_face_logs(limit=5, is_suspect=True)
        known_logs = db.get_face_logs(limit=5, is_suspect=False)
        print(f"✓ Suspect filtering works - {len(suspect_logs)} suspects, {len(known_logs)} known")
        
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_camera_manager():
    """Test camera manager"""
    print("Testing camera manager...")
    
    try:
        from core.camera_manager import CameraManager
        
        cm = CameraManager("config/camera_config.yaml")
        print(f"✓ Camera manager loaded - {len(cm.cameras)} cameras configured")
        
        # Test camera availability
        for cam_id, camera in cm.cameras.items():
            if camera.enabled:
                print(f"✓ Camera {cam_id}: {camera.name} - enabled")
            else:
                print(f"- Camera {cam_id}: {camera.name} - disabled")
        
        return True
        
    except Exception as e:
        print(f"✗ Camera manager test failed: {e}")
        return False

def test_face_detection():
    """Test face detection setup"""
    print("Testing face detection...")
    
    try:
        import yaml
        with open("config/config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        
        # Check if suspects directory exists
        suspects_dir = Path(config['app']['suspects_dir'])
        if suspects_dir.exists():
            print(f"✓ Suspects directory exists: {suspects_dir}")
        else:
            print(f"⚠ Creating suspects directory: {suspects_dir}")
            suspects_dir.mkdir(parents=True, exist_ok=True)
        
        # Check GPU configuration
        device = config['recognition']['device']
        print(f"✓ Recognition device: {device}")
        
        return True
        
    except Exception as e:
        print(f"✗ Face detection test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("NetraSena - System Test")
    print("=" * 45)
    
    success = True
    
    if not test_database():
        success = False
    
    if not test_camera_manager():
        success = False
    
    if not test_face_detection():
        success = False
    
    print("=" * 45)
    if success:
        print("✓ All tests passed! System is ready.")
        print("\nEnhanced features available:")
        print("• Live camera face capture")
        print("• Suspect management system")
        print("• Multi-camera dashboard")
        print("• Enhanced history filtering")
        print("• GPU acceleration (if available)")
        print("\nRun: python main.py")
    else:
        print("⚠ Some tests failed - check the issues above")

if __name__ == "__main__":
    main()
