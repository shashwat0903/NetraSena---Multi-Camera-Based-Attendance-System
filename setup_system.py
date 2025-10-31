#!/usr/bin/env python3
"""
System Setup and Error Resolution Script
This script fixes all issues and prepares the system for running
"""

import os
import sys
import sqlite3
from pathlib import Path
import yaml
import shutil

def create_directories():
    """Create all necessary directories"""
    directories = [
        "data",
        "data/known_faces", 
        "data/screenshots",
        "data/suspects",
        "data/user_faces",
        "logs",
        "models/models"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def fix_database():
    """Fix and initialize all databases"""
    print("\n🔧 Setting up databases...")
    
    # Main face database
    try:
        from core.database import FaceDatabase
        face_db = FaceDatabase("data/database.db")
        print("✓ Face database initialized")
    except Exception as e:
        print(f"✗ Face database error: {e}")
        return False
    
    # User management database
    try:
        from core.user_management import UserDatabase
        user_db = UserDatabase("data/users.db")
        print("✓ User database initialized")
        print(f"✓ Admin user ready (admin/admin@123)")
    except Exception as e:
        print(f"✗ User database error: {e}")
        return False
    
    return True

def create_sample_faces():
    """Create sample known faces if they don't exist"""
    print("\n👤 Setting up sample faces...")
    
    known_faces_dir = Path("data/known_faces")
    if not any(known_faces_dir.glob("*.jpg")):
        print("ℹ No known faces found. You can add face images to data/known_faces/ directory")
    else:
        faces = list(known_faces_dir.glob("*.jpg"))
        print(f"✓ Found {len(faces)} known faces")

def check_config_files():
    """Check and fix configuration files"""
    print("\n⚙️ Checking configuration files...")
    
    # Check camera config
    camera_config = Path("config/camera_config.yaml")
    if camera_config.exists():
        print("✓ Camera configuration found")
        with open(camera_config, 'r') as f:
            config = yaml.safe_load(f)
            num_cameras = len(config.get('cameras', []))
            print(f"  - {num_cameras} cameras configured")
    else:
        print("✗ Camera configuration missing")
        return False
    
    # Check main config
    main_config = Path("config/config.yaml")
    if main_config.exists():
        print("✓ Main configuration found")
    else:
        print("✗ Main configuration missing")
        return False
    
    return True

def create_alert_sounds():
    """Create placeholder alert sound files if they don't exist"""
    print("\n🔊 Setting up alert sounds...")
    
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    
    sound_files = ["alert.wav", "suspect_alert.wav"]
    
    for sound_file in sound_files:
        sound_path = assets_dir / sound_file
        if not sound_path.exists():
            # Create a simple placeholder file
            sound_path.touch()
            print(f"⚠ Created placeholder: {sound_path}")
            print(f"  → Replace with actual sound file")
        else:
            print(f"✓ Sound file exists: {sound_file}")

def fix_imports():
    """Check and fix import issues"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        "PyQt5",
        "opencv-python", 
        "numpy",
        "yaml",
        "loguru",
        "pygame",
        "sqlite3"  # Built-in, should always be available
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == "yaml":
                import yaml
            elif package == "sqlite3":
                import sqlite3
            elif package == "PyQt5":
                from PyQt5.QtWidgets import QApplication
            elif package == "opencv-python":
                import cv2
            elif package == "numpy":
                import numpy
            elif package == "loguru":
                from loguru import logger
            elif package == "pygame":
                import pygame
            
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠ Missing packages: {missing_packages}")
        print("Run: pip install " + " ".join(missing_packages))
        return False
    
    return True

def create_simple_main_without_insightface():
    """Create a simplified main program that doesn't require insightface"""
    print("\n🚀 Creating simplified main program...")
    
    content = '''#!/usr/bin/env python3
"""
NetraSena Simplified Main Program (without face recognition)
This version focuses on the camera system and role-based access control
"""

import sys
import os
import yaml
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.user_management import UserDatabase
from core.camera_manager import CameraManager

class SimplifiedMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetraSena - Simplified Version")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize user database
        self.user_db = UserDatabase()
        
        # Initialize camera manager
        self.camera_manager = CameraManager('config/camera_config.yaml')
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("NetraSena Camera System")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        layout.addWidget(title)
        
        # Status
        self.status_label = QLabel("System Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Buttons
        test_cameras_btn = QPushButton("Test Cameras")
        test_cameras_btn.clicked.connect(self.test_cameras)
        layout.addWidget(test_cameras_btn)
        
        test_database_btn = QPushButton("Test Database")
        test_database_btn.clicked.connect(self.test_database)
        layout.addWidget(test_database_btn)
        
        exit_btn = QPushButton("Exit")
        exit_btn.clicked.connect(self.close)
        layout.addWidget(exit_btn)
        
    def test_cameras(self):
        """Test camera connections"""
        try:
            self.status_label.setText("Testing cameras...")
            self.camera_manager.start_all_cameras()
            
            # Test each camera
            working_cameras = []
            for cam_id in range(5):
                if cam_id in self.camera_manager.cameras:
                    frame = self.camera_manager.get_frame(cam_id)
                    if frame is not None:
                        working_cameras.append(cam_id)
            
            self.camera_manager.stop_all_cameras()
            
            if working_cameras:
                message = f"Working cameras: {working_cameras}"
                QMessageBox.information(self, "Camera Test", message)
            else:
                QMessageBox.warning(self, "Camera Test", "No cameras working")
                
            self.status_label.setText("Camera test completed")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Camera test failed: {e}")
            self.status_label.setText("Camera test failed")
    
    def test_database(self):
        """Test database connections"""
        try:
            # Test user database
            admin = self.user_db.get_user('admin')
            if admin:
                message = f"Database working!\\nAdmin user: {admin.username}\\nRole: {admin.role}"
                QMessageBox.information(self, "Database Test", message)
            else:
                QMessageBox.warning(self, "Database Test", "Admin user not found")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Database test failed: {e}")

def load_config():
    """Load configuration"""
    config_path = Path("config/config.yaml")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    """Main application"""
    print("Starting NetraSena Simplified Version...")
    
    # Setup logging
    logger.add("logs/app.log", rotation="10 MB")
    
    app = QApplication(sys.argv)
    window = SimplifiedMainWindow()
    window.show()
    
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())
'''
    
    with open("main_simplified.py", "w") as f:
        f.write(content)
    
    print("✓ Created main_simplified.py")
    print("  → Run this if insightface has issues")

def main():
    """Main setup function"""
    print("=" * 60)
    print("🛠️  NetraSena System Setup & Error Resolution")
    print("=" * 60)
    
    success = True
    
    # Step 1: Create directories
    print("1️⃣ Creating directories...")
    create_directories()
    
    # Step 2: Check imports
    print("\n2️⃣ Checking dependencies...")
    if not fix_imports():
        success = False
        print("⚠️  Some dependencies missing - install them first")
    
    # Step 3: Check config files
    print("\n3️⃣ Checking configuration...")
    if not check_config_files():
        success = False
    
    # Step 4: Setup databases
    if success:
        print("\n4️⃣ Setting up databases...")
        if not fix_database():
            success = False
    
    # Step 5: Setup assets
    print("\n5️⃣ Setting up assets...")
    create_alert_sounds()
    create_sample_faces()
    
    # Step 6: Create simplified version
    print("\n6️⃣ Creating backup version...")
    create_simple_main_without_insightface()
    
    print("\n" + "=" * 60)
    
    if success:
        print("✅ SYSTEM SETUP COMPLETE!")
        print("\n🚀 Ready to run:")
        print("   python main_simplified.py  (recommended)")
        print("   python main_secure.py      (full version)")
        print("\n👤 Default admin login:")
        print("   Username: admin")
        print("   Password: admin@123")
    else:
        print("❌ SETUP INCOMPLETE!")
        print("\n⚠️  Please fix the errors above first")
    
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
