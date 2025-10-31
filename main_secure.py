#!/usr/bin/env python3
"""
NetraSena Multi-Camera Face Tracker with Role-Based Access Control
Main application entry point with authentication system
"""

import sys
import os
from pathlib import Path
import yaml
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from loguru import logger

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.face_detection import FaceDetector
from core.user_management import UserDatabase
from ui.login_system import LoginDialog
from ui.role_based_main_window import RoleBasedMainWindow

def load_config():
    """Load configuration from YAML file"""
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def setup_logging():
    """Setup logging configuration"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure loguru
    logger.add(
        log_dir / "app.log",
        rotation="10 MB",
        retention="1 week",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )
    
    logger.add(
        log_dir / "error.log",
        rotation="10 MB",
        retention="1 week",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )

def main():
    """Main application entry point"""
    # Setup logging
    setup_logging()
    logger.info("Starting NetraSena Multi-Camera Face Tracker")
    
    # Load configuration
    config = load_config()
    if not config:
        print("Error: Could not load configuration file")
        return 1
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("NetraSena")
    app.setApplicationVersion("2.0.0")
    
    # Set application style
    app.setStyle('Fusion')
    
    try:
        # Initialize face detector
        logger.info("Initializing face detection system")
        face_detector = FaceDetector(config)
        
        # Load known faces and suspects
        face_detector.load_known_faces(config['app']['known_faces_dir'])
        face_detector.load_suspects(config['app']['suspects_dir'])
        
        # Initialize user database
        logger.info("Initializing user database")
        user_db = UserDatabase()
        
        # Show login dialog
        logger.info("Showing login dialog")
        login_dialog = LoginDialog(face_detector)
        
        current_user = None
        
        def on_login_success(user):
            nonlocal current_user
            current_user = user
            logger.info(f"User {user.username} logged in successfully")
            
        login_dialog.login_successful.connect(on_login_success)
        
        # Show login dialog
        if login_dialog.exec_() == login_dialog.Accepted and current_user:
            logger.info(f"Login successful for user: {current_user.username} (Role: {current_user.role})")
            
            # Create and show main window based on user role
            main_window = RoleBasedMainWindow(config, current_user)
            main_window.show()
            
            # Start the application event loop
            logger.info("Starting main application")
            return app.exec_()
            
        else:
            logger.info("Login cancelled or failed")
            return 0
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        QMessageBox.critical(None, "Error", f"Application error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
