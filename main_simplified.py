#!/usr/bin/env python3
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
                message = f"Database working!\nAdmin user: {admin.username}\nRole: {admin.role}"
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
