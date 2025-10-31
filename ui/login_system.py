import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QMessageBox, QFrame,
                            QTabWidget, QWidget, QComboBox, QCheckBox, QTableWidget,
                            QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont
from loguru import logger
import time
from pathlib import Path

from core.user_management import UserDatabase, FaceAuthenticator, User
from core.face_detection import FaceDetector
from core.utils import numpy_to_pixmap

class LoginDialog(QDialog):
    login_successful = pyqtSignal(User)
    
    def __init__(self, face_detector: FaceDetector, parent=None):
        super().__init__(parent)
        self.face_detector = face_detector
        self.user_db = UserDatabase()
        self.face_auth = FaceAuthenticator(face_detector)
        self.camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_camera_frame)
        self.face_detected_user = None
        self.selected_role = None
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("NetraSena - Login")
        self.setFixedSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("NetraSena Security System")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 24, QFont.Bold))
        layout.addWidget(title)
        
        # Role selection
        role_frame = QFrame()
        role_frame.setFrameStyle(QFrame.StyledPanel)
        role_layout = QVBoxLayout(role_frame)
        
        role_label = QLabel("Select Login Type:")
        role_label.setFont(QFont("Arial", 14, QFont.Bold))
        role_layout.addWidget(role_label)
        
        role_buttons_layout = QHBoxLayout()
        
        self.admin_button = QPushButton("Admin Login")
        self.admin_button.setMinimumHeight(50)
        self.admin_button.clicked.connect(lambda: self.select_role("admin"))
        role_buttons_layout.addWidget(self.admin_button)
        
        self.subadmin_button = QPushButton("Subadmin Login")
        self.subadmin_button.setMinimumHeight(50)
        self.subadmin_button.clicked.connect(lambda: self.select_role("subadmin"))
        role_buttons_layout.addWidget(self.subadmin_button)
        
        role_layout.addLayout(role_buttons_layout)
        layout.addWidget(role_frame)
        
        # Create tabs (initially hidden)
        self.tabs = QTabWidget()
        self.tabs.setVisible(False)
        
        # Face Authentication Tab (for subadmin)
        self.face_tab = QWidget()
        self.setup_face_tab()
        self.tabs.addTab(self.face_tab, "Face Authentication")
        
        # Manual Login Tab (for admin and backup)
        self.manual_tab = QWidget()
        self.setup_manual_tab()
        self.tabs.addTab(self.manual_tab, "Manual Login")
        
        layout.addWidget(self.tabs)
        
        self.setLayout(layout)
        
    def select_role(self, role):
        """Handle role selection"""
        self.selected_role = role
        self.tabs.setVisible(True)
        
        if role == "admin":
            # For admin, go directly to manual login
            self.tabs.setCurrentIndex(1)  # Manual tab
            self.tabs.setTabEnabled(0, False)  # Disable face tab
        else:
            # For subadmin, setup face authentication
            self.tabs.setCurrentIndex(0)  # Face tab
            self.setup_camera()
            
        # Update UI labels
        if role == "admin":
            self.manual_tab.findChild(QLabel).setText("Admin Login")
        else:
            # Update face tab instructions
            instructions = self.face_tab.findChild(QLabel)
            if instructions:
                instructions.setText("Subadmin Face Authentication - Look at the camera")
                
    def setup_face_tab(self):
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("Look at the camera for face recognition")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setFont(QFont("Arial", 14))
        layout.addWidget(instructions)
        
        # Camera feed
        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setStyleSheet("border: 2px solid black")
        self.camera_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.camera_label)
        
        # Status
        self.status_label = QLabel("Select login type first")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.status_label)
        
        # User ID and Password input (shown after face recognition)
        self.auth_frame = QFrame()
        self.auth_frame.setVisible(False)
        auth_layout = QVBoxLayout()
        
        # User ID input
        userid_layout = QHBoxLayout()
        userid_layout.addWidget(QLabel("User ID:"))
        self.userid_input = QLineEdit()
        userid_layout.addWidget(self.userid_input)
        auth_layout.addLayout(userid_layout)
        
        # Password input
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.authenticate_subadmin)
        password_layout.addWidget(self.password_input)
        auth_layout.addLayout(password_layout)
        
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.authenticate_subadmin)
        auth_layout.addWidget(self.login_button)
        
        self.auth_frame.setLayout(auth_layout)
        layout.addWidget(self.auth_frame)
        
        self.face_tab.setLayout(layout)
        
    def setup_manual_tab(self):
        layout = QVBoxLayout()
        
        # Manual login form
        form_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Manual Login")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(title_label)
        
        # Username
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        username_layout.addWidget(self.username_input)
        form_layout.addLayout(username_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.manual_password_input = QLineEdit()
        self.manual_password_input.setEchoMode(QLineEdit.Password)
        self.manual_password_input.returnPressed.connect(self.manual_login)
        password_layout.addWidget(self.manual_password_input)
        form_layout.addLayout(password_layout)
        
        # Login button
        self.manual_login_button = QPushButton("Login")
        self.manual_login_button.clicked.connect(self.manual_login)
        form_layout.addWidget(self.manual_login_button)
        
        layout.addWidget(QLabel(""))  # Spacer
        layout.addLayout(form_layout)
        layout.addStretch()
        
        self.manual_tab.setLayout(layout)
        
    def setup_camera(self):
        """Setup camera for face authentication (subadmin only)"""
        if self.selected_role != "subadmin":
            return
            
        try:
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                self.timer.start(50)  # 20 FPS
                self.status_label.setText("Camera ready - Look at the camera for face recognition")
            else:
                self.status_label.setText("Camera not available - Use manual login")
                self.tabs.setCurrentIndex(1)  # Switch to manual tab
        except Exception as e:
            logger.error(f"Camera setup failed: {e}")
            self.status_label.setText("Camera error - Use manual login")
            self.tabs.setCurrentIndex(1)
            
    def update_camera_frame(self):
        """Update camera frame and check for face authentication"""
        if not self.camera or not self.camera.isOpened() or self.selected_role != "subadmin":
            return
            
        ret, frame = self.camera.read()
        if not ret:
            return
            
        # Flip frame horizontally for mirror effect
        frame = cv2.flip(frame, 1)
        
        # Try face authentication only for subadmin
        if not self.face_detected_user and self.selected_role == "subadmin":
            authenticated_user = self.face_auth.authenticate_face(frame)
            if authenticated_user and authenticated_user.role == "subadmin":
                self.face_detected_user = authenticated_user
                self.status_label.setText(f"Face recognized: {authenticated_user.username}")
                self.auth_frame.setVisible(True)
                self.userid_input.setText(authenticated_user.user_id)
                self.password_input.setFocus()
                
                # Draw recognition indicator
                cv2.putText(frame, f"Recognized: {authenticated_user.username}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Display frame
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.camera_label.setPixmap(scaled_pixmap)
        
    def authenticate_subadmin(self):
        """Authenticate subadmin password after face recognition"""
        if not self.face_detected_user:
            QMessageBox.warning(self, "Error", "No face detected. Please try again.")
            return
            
        user_id = self.userid_input.text()
        password = self.password_input.text()
        
        # For development, allow admin password
        if user_id == "admin" and password == "admin":
            QMessageBox.information(self, "Success", "Admin login successful")
            self.accept()
            return
        
        if self.user_db.verify_password(self.face_detected_user.user_id, password):
            self.user_db.update_last_login(self.face_detected_user.user_id)
            self.login_successful.emit(self.face_detected_user)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid password!")
            self.password_input.clear()
            self.password_input.setFocus()
            
    def manual_login(self):
        """Manual login with username/password"""
        username = self.username_input.text()
        password = self.manual_password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
            
        user = self.user_db.get_user_by_username(username)
        if user and self.user_db.verify_password(user.user_id, password):
            self.user_db.update_last_login(user.user_id)
            self.login_successful.emit(user)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials!")
            self.manual_password_input.clear()
            
    def closeEvent(self, event):
        """Clean up camera on close"""
        self.timer.stop()
        if self.camera:
            self.camera.release()
        event.accept()

class UserManagementDialog(QDialog):
    def __init__(self, face_detector: FaceDetector, parent=None):
        super().__init__(parent)
        self.face_detector = face_detector
        self.user_db = UserDatabase()
        self.face_auth = FaceAuthenticator(face_detector)
        self.camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_camera_frame)
        self.registering_user = None
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("User Management")
        self.setFixedSize(1000, 700)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("User Management")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)
        
        # Create tabs
        self.tabs = QTabWidget()
        
        # User List Tab
        self.user_list_tab = QWidget()
        self.setup_user_list_tab()
        self.tabs.addTab(self.user_list_tab, "Users")
        
        # Add User Tab
        self.add_user_tab = QWidget()
        self.setup_add_user_tab()
        self.tabs.addTab(self.add_user_tab, "Add User")
        
        layout.addWidget(self.tabs)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
        self.load_users()
        
    def setup_user_list_tab(self):
        layout = QVBoxLayout()
        
        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels([
            "User ID", "Username", "Role", "Assigned Cameras", "Last Login", "Actions"
        ])
        
        # Make table fill the space
        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.users_table)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_users)
        layout.addWidget(refresh_button)
        
        self.user_list_tab.setLayout(layout)
        
    def setup_add_user_tab(self):
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QVBoxLayout()
        
        # User ID
        user_id_layout = QHBoxLayout()
        user_id_layout.addWidget(QLabel("User ID:"))
        self.user_id_input = QLineEdit()
        user_id_layout.addWidget(self.user_id_input)
        form_layout.addLayout(user_id_layout)
        
        # Username
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username:"))
        self.new_username_input = QLineEdit()
        username_layout.addWidget(self.new_username_input)
        form_layout.addLayout(username_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.new_password_input)
        form_layout.addLayout(password_layout)
        
        # Role
        role_layout = QHBoxLayout()
        role_layout.addWidget(QLabel("Role:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(["subadmin"])
        role_layout.addWidget(self.role_combo)
        form_layout.addLayout(role_layout)
        
        # Camera assignment
        camera_layout = QVBoxLayout()
        camera_layout.addWidget(QLabel("Assigned Cameras:"))
        self.camera_checkboxes = []
        for i in range(5):
            checkbox = QCheckBox(f"Camera {i} - {'Laptop' if i == 0 else f'IP Camera {i}'}")
            self.camera_checkboxes.append(checkbox)
            camera_layout.addWidget(checkbox)
        form_layout.addLayout(camera_layout)
        
        layout.addLayout(form_layout)
        
        # Face registration
        face_layout = QVBoxLayout()
        face_layout.addWidget(QLabel("Face Registration:"))
        
        # Camera feed
        self.reg_camera_label = QLabel()
        self.reg_camera_label.setMinimumSize(320, 240)
        self.reg_camera_label.setStyleSheet("border: 2px solid black")
        self.reg_camera_label.setAlignment(Qt.AlignCenter)
        face_layout.addWidget(self.reg_camera_label)
        
        # Camera controls
        camera_controls = QHBoxLayout()
        self.start_camera_button = QPushButton("Start Camera")
        self.start_camera_button.clicked.connect(self.start_registration_camera)
        camera_controls.addWidget(self.start_camera_button)
        
        self.capture_face_button = QPushButton("Capture Face")
        self.capture_face_button.clicked.connect(self.capture_face)
        self.capture_face_button.setEnabled(False)
        camera_controls.addWidget(self.capture_face_button)
        
        face_layout.addLayout(camera_controls)
        layout.addLayout(face_layout)
        
        # Create user button
        self.create_user_button = QPushButton("Create User")
        self.create_user_button.clicked.connect(self.create_user)
        layout.addWidget(self.create_user_button)
        
        self.add_user_tab.setLayout(layout)
        
    def load_users(self):
        """Load users into the table"""
        subadmins = self.user_db.get_all_subadmins()
        
        self.users_table.setRowCount(len(subadmins))
        
        for row, user in enumerate(subadmins):
            self.users_table.setItem(row, 0, QTableWidgetItem(user.user_id))
            self.users_table.setItem(row, 1, QTableWidgetItem(user.username))
            self.users_table.setItem(row, 2, QTableWidgetItem(user.role))
            self.users_table.setItem(row, 3, QTableWidgetItem(str(user.assigned_cameras)))
            last_login = user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else "Never"
            self.users_table.setItem(row, 4, QTableWidgetItem(last_login))
            
            # Delete button
            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda checked, uid=user.user_id: self.delete_user(uid))
            self.users_table.setCellWidget(row, 5, delete_button)
            
    def start_registration_camera(self):
        """Start camera for face registration"""
        try:
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                self.timer.start(50)
                self.capture_face_button.setEnabled(True)
                self.start_camera_button.setText("Stop Camera")
                self.start_camera_button.clicked.disconnect()
                self.start_camera_button.clicked.connect(self.stop_registration_camera)
            else:
                QMessageBox.warning(self, "Error", "Camera not available")
        except Exception as e:
            logger.error(f"Camera setup failed: {e}")
            QMessageBox.warning(self, "Error", "Camera setup failed")
            
    def stop_registration_camera(self):
        """Stop camera"""
        self.timer.stop()
        if self.camera:
            self.camera.release()
        self.capture_face_button.setEnabled(False)
        self.start_camera_button.setText("Start Camera")
        self.start_camera_button.clicked.disconnect()
        self.start_camera_button.clicked.connect(self.start_registration_camera)
        self.reg_camera_label.clear()
        
    def update_camera_frame(self):
        """Update camera frame for registration"""
        if not self.camera or not self.camera.isOpened():
            return
            
        ret, frame = self.camera.read()
        if not ret:
            return
            
        # Flip frame horizontally for mirror effect
        frame = cv2.flip(frame, 1)
        
        # Display frame
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(self.reg_camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.reg_camera_label.setPixmap(scaled_pixmap)
        
    def capture_face(self):
        """Capture face for registration"""
        if not self.camera or not self.camera.isOpened():
            return
            
        ret, frame = self.camera.read()
        if not ret:
            return
            
        # Store the captured frame
        self.captured_frame = cv2.flip(frame, 1)
        QMessageBox.information(self, "Success", "Face captured! Now create the user.")
        
    def create_user(self):
        """Create a new user"""
        user_id = self.user_id_input.text()
        username = self.new_username_input.text()
        password = self.new_password_input.text()
        role = self.role_combo.currentText()
        
        if not all([user_id, username, password]):
            QMessageBox.warning(self, "Error", "Please fill all fields")
            return
            
        # Get assigned cameras
        assigned_cameras = []
        for i, checkbox in enumerate(self.camera_checkboxes):
            if checkbox.isChecked():
                assigned_cameras.append(i)
                
        if not assigned_cameras:
            QMessageBox.warning(self, "Error", "Please assign at least one camera")
            return
            
        # Hash password
        password_hash = self.user_db._hash_password(password)
        
        # Create user
        success = self.user_db.create_user(
            user_id=user_id,
            username=username,
            password_hash=password_hash,
            role=role,
            assigned_cameras=assigned_cameras
        )
        
        if success:
            # Register face if captured
            if hasattr(self, 'captured_frame'):
                face_success = self.face_auth.register_user_face(user_id, self.captured_frame)
                if face_success:
                    QMessageBox.information(self, "Success", "User created with face authentication!")
                else:
                    QMessageBox.warning(self, "Warning", "User created but face registration failed")
            else:
                QMessageBox.information(self, "Success", "User created successfully!")
                
            # Clear form
            self.user_id_input.clear()
            self.new_username_input.clear()
            self.new_password_input.clear()
            for checkbox in self.camera_checkboxes:
                checkbox.setChecked(False)
            
            # Refresh user list
            self.load_users()
            
        else:
            QMessageBox.warning(self, "Error", "User creation failed")
            
    def delete_user(self, user_id: str):
        """Delete a user"""
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete user {user_id}?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success = self.user_db.delete_user(user_id)
            if success:
                QMessageBox.information(self, "Success", "User deleted successfully")
                self.load_users()
            else:
                QMessageBox.warning(self, "Error", "User deletion failed")
                
    def closeEvent(self, event):
        """Clean up camera on close"""
        self.timer.stop()
        if self.camera:
            self.camera.release()
        event.accept()
