import sys
import time
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QPushButton, QTabWidget, QScrollArea, QGridLayout,
                            QMessageBox, QFileDialog, QComboBox, QSlider, QSpinBox, QFrame,
                            QSplitter, QCheckBox, QMenuBar, QAction, QStatusBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QImage, QIcon, QFont
from loguru import logger
from typing import Dict, Optional, Tuple, List
import numpy as np
import cv2
from pathlib import Path

from core.face_detection import FaceDetector
from core.camera_manager import CameraManager
from core.alert_system import AlertEvent, AlertSystem
from core.database import FaceDatabase
from core.static_face_tracker import StaticFaceTracker
from core.entry_exit_tracker import EntryExitTracker
from core.utils import numpy_to_pixmap, resize_image, draw_face_info
from core.user_management import User
from ui.login_system import LoginDialog, UserManagementDialog
from ui.improved_face_manager import ImprovedFaceManagerDialog
from ui.alert_panel import AlertPanel
from ui.history_viewer import HistoryViewer
from ui.entry_exit_statistics import EntryExitStatisticsDialog

class RoleBasedMainWindow(QMainWindow):
    def __init__(self, config, current_user: User):
        """
        Initialize the main window with role-based access control
        
        Args:
            config (dict): The application configuration dictionary
            current_user (User): The currently logged-in user
        """
        super().__init__()
        self.config = config
        self.current_user = current_user
        self.setWindowTitle(f"{config['app']['name']} v{config['app']['version']} - {current_user.username} ({current_user.role})")
        self.setWindowIcon(QIcon(config['app']['logo']))
        self.setGeometry(100, 100, 1400, 900)
        
        self.processing_interval = 1.0
        self.pinned_camera = None  # For admin to pin a single camera
        
        # Initialize core components
        self.face_detector = FaceDetector(config)
        self.camera_manager = CameraManager('config/camera_config.yaml')
        self.alert_system = AlertSystem(config)
        self.database = FaceDatabase(config['app']['database_path'])
        
        # Initialize entry/exit tracking system
        self.entry_exit_tracker = EntryExitTracker(config['app']['database_path'])
        
        # Initialize face tracker for static detection
        self.face_tracker = StaticFaceTracker(timeout_seconds=30, min_detection_confidence=0.6)
        
        # Load known faces
        self.face_detector.load_known_faces(config['app']['known_faces_dir'])
        
        # Load suspects
        self.face_detector.load_suspects(config['app']['suspects_dir'])
        
        # Camera display widgets
        self.camera_displays: Dict[int, QLabel] = {}
        self.camera_stats: Dict[int, Dict] = {}
        
        # UI Components
        self.init_ui()
        
        # Start cameras based on user permissions
        self.start_assigned_cameras()
        
        # Setup update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(100)  # 10 FPS for UI updates
        
        # Track last processed time per camera
        self.last_processed: Dict[int, float] = {}
        
    def init_ui(self):
        """Set up the main user interface based on user role"""
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self.setup_menu_bar()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Add tabs based on user role
        self.setup_monitor_tab()
        
        if self.current_user.role == 'admin':
            self.setup_admin_tabs()
        else:
            self.setup_subadmin_tabs()
            
        # Status bar
        self.setup_status_bar()
        
    def setup_menu_bar(self):
        """Set up the application's menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        if self.current_user.role == 'admin':
            # User management (admin only)
            user_mgmt_action = QAction('User Management', self)
            user_mgmt_action.triggered.connect(self.open_user_management)
            file_menu.addAction(user_mgmt_action)
            
            # Face management (admin only)
            face_mgmt_action = QAction('Face Management', self)
            face_mgmt_action.triggered.connect(self.open_face_management)
            file_menu.addAction(face_mgmt_action)
            
            file_menu.addSeparator()
        
        # Logout
        logout_action = QAction('Logout', self)
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)
        
        # Exit
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        # Entry/Exit Statistics (available to all users)
        entry_exit_action = QAction('Entry/Exit Statistics', self)
        entry_exit_action.triggered.connect(self.open_entry_exit_statistics)
        view_menu.addAction(entry_exit_action)
        
        view_menu.addSeparator()
        
        if self.current_user.role == 'admin':
            # Pin camera (admin only)
            pin_menu = view_menu.addMenu('Pin Camera')
            for cam_id in self.current_user.assigned_cameras:
                camera_name = self.camera_manager.cameras[cam_id].name if cam_id in self.camera_manager.cameras else f"Camera {cam_id}"
                pin_action = QAction(camera_name, self)
                pin_action.triggered.connect(lambda checked, cid=cam_id: self.pin_camera(cid))
                pin_menu.addAction(pin_action)
                
            # Unpin camera
            unpin_action = QAction('Unpin Camera', self)
            unpin_action.triggered.connect(self.unpin_camera)
            view_menu.addAction(unpin_action)
            
            view_menu.addSeparator()
        
        # Fullscreen
        fullscreen_action = QAction('Toggle Fullscreen', self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
    def setup_monitor_tab(self):
        """Set up the main monitoring tab"""
        monitor_widget = QWidget()
        monitor_layout = QVBoxLayout(monitor_widget)
        
        # Camera grid
        self.camera_scroll = QScrollArea()
        self.camera_grid_widget = QWidget()
        self.camera_grid_layout = QGridLayout(self.camera_grid_widget)
        
        # Create camera displays for assigned cameras
        self.create_camera_displays()
        
        self.camera_scroll.setWidget(self.camera_grid_widget)
        self.camera_scroll.setWidgetResizable(True)
        monitor_layout.addWidget(self.camera_scroll)
        
        # Stats panel
        self.stats_frame = QFrame()
        self.stats_frame.setFixedHeight(80)
        self.stats_layout = QHBoxLayout(self.stats_frame)
        
        self.total_faces_label = QLabel("Total Faces: 0")
        self.suspects_label = QLabel("Suspects: 0")
        self.active_cameras_label = QLabel(f"Active Cameras: {len(self.current_user.assigned_cameras)}")
        
        self.stats_layout.addWidget(self.total_faces_label)
        self.stats_layout.addWidget(self.suspects_label)
        self.stats_layout.addWidget(self.active_cameras_label)
        self.stats_layout.addStretch()
        
        monitor_layout.addWidget(self.stats_frame)
        
        self.tab_widget.addTab(monitor_widget, "Monitor")
        
    def setup_admin_tabs(self):
        """Set up additional tabs for admin users"""
        # History tab
        self.history_tab = HistoryViewer(self.database)
        self.tab_widget.addTab(self.history_tab, "History")
        
        # Alert panel
        self.alert_panel = AlertPanel(self.alert_system)
        self.tab_widget.addTab(self.alert_panel, "Alerts")
        
        # System controls
        self.setup_system_controls_tab()
        
    def setup_subadmin_tabs(self):
        """Set up limited tabs for subadmin users"""
        # Limited history (only for assigned cameras)
        self.history_tab = HistoryViewer(self.database, camera_filter=self.current_user.assigned_cameras)
        self.tab_widget.addTab(self.history_tab, "History")
        
    def setup_system_controls_tab(self):
        """Set up system controls tab (admin only)"""
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # Alert controls
        alert_frame = QFrame()
        alert_frame.setFrameStyle(QFrame.StyledPanel)
        alert_layout = QVBoxLayout(alert_frame)
        
        alert_layout.addWidget(QLabel("Alert Settings"))
        
        self.alert_enabled_checkbox = QCheckBox("Enable Alerts")
        self.alert_enabled_checkbox.setChecked(self.alert_system.alert_enabled)
        self.alert_enabled_checkbox.toggled.connect(self.toggle_alerts)
        alert_layout.addWidget(self.alert_enabled_checkbox)
        
        self.screenshot_enabled_checkbox = QCheckBox("Enable Screenshots")
        self.screenshot_enabled_checkbox.setChecked(self.alert_system.screenshot_enabled)
        self.screenshot_enabled_checkbox.toggled.connect(self.toggle_screenshots)
        alert_layout.addWidget(self.screenshot_enabled_checkbox)
        
        controls_layout.addWidget(alert_frame)
        
        # Camera controls
        camera_frame = QFrame()
        camera_frame.setFrameStyle(QFrame.StyledPanel)
        camera_layout = QVBoxLayout(camera_frame)
        
        camera_layout.addWidget(QLabel("Camera Controls"))
        
        restart_cameras_button = QPushButton("Restart All Cameras")
        restart_cameras_button.clicked.connect(self.restart_cameras)
        camera_layout.addWidget(restart_cameras_button)
        
        controls_layout.addWidget(camera_frame)
        
        controls_layout.addStretch()
        
        self.tab_widget.addTab(controls_widget, "Controls")
        
    def setup_status_bar(self):
        """Set up the status bar"""
        self.status_bar = self.statusBar()
        self.status_label = QLabel("Ready")
        self.user_label = QLabel(f"User: {self.current_user.username} ({self.current_user.role})")
        
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.user_label)
        
    def create_camera_displays(self):
        """Create camera display widgets for assigned cameras"""
        if self.pinned_camera is not None:
            # Show only pinned camera
            self.create_single_camera_display(self.pinned_camera, 0, 0)
        else:
            # Show all assigned cameras
            cols = 3 if len(self.current_user.assigned_cameras) > 4 else 2
            for i, cam_id in enumerate(self.current_user.assigned_cameras):
                row = i // cols
                col = i % cols
                self.create_single_camera_display(cam_id, row, col)
                
    def create_single_camera_display(self, cam_id: int, row: int, col: int):
        """Create a single camera display widget"""
        camera_frame = QFrame()
        camera_frame.setFrameStyle(QFrame.StyledPanel)
        camera_layout = QVBoxLayout(camera_frame)
        
        # Camera name
        camera_name = self.camera_manager.cameras[cam_id].name if cam_id in self.camera_manager.cameras else f"Camera {cam_id}"
        name_label = QLabel(camera_name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        camera_layout.addWidget(name_label)
        
        # Camera display
        camera_display = QLabel()
        camera_display.setMinimumSize(320, 240)
        camera_display.setStyleSheet("border: 2px solid black; background-color: #f0f0f0;")
        camera_display.setAlignment(Qt.AlignCenter)
        camera_display.setText("No Signal")
        camera_layout.addWidget(camera_display)
        
        # Camera stats
        stats_label = QLabel("Faces: 0 | Suspects: 0")
        stats_label.setAlignment(Qt.AlignCenter)
        camera_layout.addWidget(stats_label)
        
        self.camera_displays[cam_id] = camera_display
        self.camera_stats[cam_id] = {'faces': 0, 'suspects': 0, 'stats_label': stats_label}
        
        self.camera_grid_layout.addWidget(camera_frame, row, col)
        
    def start_assigned_cameras(self):
        """Start cameras assigned to the current user"""
        for cam_id in self.current_user.assigned_cameras:
            if cam_id in self.camera_manager.cameras:
                self.camera_manager.start_camera(cam_id)
                logger.info(f"Started camera {cam_id} for user {self.current_user.username}")
            else:
                logger.warning(f"Camera {cam_id} not found in configuration")
                
    def update(self):
        """Update the UI with latest camera frames"""
        current_time = time.time()
        
        # Update camera displays for assigned cameras
        for cam_id in self.current_user.assigned_cameras:
            if cam_id not in self.camera_displays:
                continue
                
            # Rate limiting
            if cam_id in self.last_processed:
                if current_time - self.last_processed[cam_id] < self.processing_interval:
                    continue
                    
            frame = self.camera_manager.get_frame(cam_id)
            if frame is not None:
                processed_frame, alert_triggered = self.process_frame(cam_id, frame)
                
                # Update display
                pixmap = numpy_to_pixmap(processed_frame)
                if pixmap:
                    display_widget = self.camera_displays[cam_id]
                    scaled_pixmap = pixmap.scaled(display_widget.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    display_widget.setPixmap(scaled_pixmap)
                    
                self.last_processed[cam_id] = current_time
            else:
                # Show "No Signal" for cameras without frames
                self.camera_displays[cam_id].setText("No Signal")
                
        # Update overall stats
        self.update_overall_stats()
        
    def process_frame(self, cam_id: int, frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Process a video frame for face detection and recognition"""
        alert_triggered = False
        try:
            # Use regular detection for all cameras
            faces = self.face_detector.detect_faces(frame)
            
            if not faces:
                # Draw existing tracked faces
                active_tracks = self.face_tracker.get_active_tracks(cam_id)
                for tracked_face in active_tracks:
                    color = (0, 0, 255) if tracked_face.is_suspect else (0, 255, 0)
                    frame = draw_face_info(
                        frame, tracked_face.bbox,
                        name=tracked_face.name + (" [SUSPECT]" if tracked_face.is_suspect else "") + " [TRACKED]",
                        confidence=tracked_face.confidence,
                        camera_name=self.camera_manager.cameras[cam_id].name,
                        age=tracked_face.age,
                        gender=tracked_face.gender,
                        timestamp=time.time(),
                        color=color
                    )
                return frame, False
                
            # Recognize faces (including suspects)
            recognized_faces = self.face_detector.recognize_faces_with_suspects(faces)
            
            # Update tracking with new detections
            tracked_faces = self.face_tracker.update_tracking(cam_id, recognized_faces)
            
            # Process each recognized face
            face_count = 0
            suspect_count = 0
            
            for face, known_face, confidence, is_suspect in recognized_faces:
                camera_name = self.camera_manager.cameras[cam_id].name
                face_count += 1
                
                if known_face:
                    # Draw face info
                    color = (0, 0, 255) if is_suspect else (0, 255, 0)
                    
                    # Check if this is a newly tracked face that should trigger an alert
                    should_alert = any(
                        tf.name == known_face.name and tf.detection_count == 1 
                        for tf in tracked_faces
                    )
                    
                    frame = draw_face_info(
                        frame, face.bbox,
                        name=known_face.name + (" [SUSPECT]" if is_suspect else ""),
                        confidence=confidence,
                        camera_name=camera_name,
                        age=face.age,
                        gender=face.gender,
                        timestamp=time.time(),
                        color=color
                    )
                    
                    # Trigger alert only for newly detected faces AND only for suspects
                    if should_alert:
                        # Create alert event for logging purposes
                        alert_event = self.alert_system.create_alert_event(
                            cam_id, camera_name,
                            known_face.name, face, confidence,
                            frame, is_suspect=is_suspect
                        )
                        
                        # Only trigger sound/notification alerts for suspects
                        if is_suspect:
                            self.alert_system.trigger_alert(
                                cam_id, camera_name,
                                known_face.name, face, confidence,
                                frame, is_suspect=is_suspect
                            )
                            alert_triggered = True
                            suspect_count += 1
                        
                        # Log all face events to database (both users and suspects)
                        self.database.log_face_event(alert_event)
                    
                    # Process entry/exit tracking for ALL recognized faces (moved outside should_alert)
                    # Track on entry gate (camera 1) and exit gate (camera 2)
                    if cam_id in [1, 2]:  # Track all recognized faces (both users and suspects)
                        try:
                            logger.info(f"Entry/exit tracking: {known_face.name} detected on camera {cam_id} ({camera_name}) - suspect: {is_suspect}")
                            self.entry_exit_tracker.process_detection(
                                known_face.name, cam_id, camera_name, confidence
                            )
                        except Exception as e:
                            logger.error(f"Error in entry/exit tracking for {known_face.name}: {e}")
                            import traceback
                            logger.error(f"Traceback: {traceback.format_exc()}")
                    else:
                        logger.debug(f"Camera {cam_id} ({camera_name}) not configured for entry/exit tracking")
                else:
                    # Unknown face
                    frame = draw_face_info(
                        frame, face.bbox,
                        name="Unknown",
                        confidence=confidence,
                        camera_name=camera_name,
                        age=face.age,
                        gender=face.gender,
                        timestamp=time.time()
                    )
            
            # Update camera stats
            self.update_camera_stats(cam_id, face_count, suspect_count)
            
        except Exception as e:
            logger.error(f"Error processing frame from camera {cam_id}: {e}")
            
        return frame, alert_triggered
        
    def update_camera_stats(self, cam_id: int, face_count: int, suspect_count: int):
        """Update camera statistics"""
        if cam_id in self.camera_stats:
            self.camera_stats[cam_id]['faces'] = face_count
            self.camera_stats[cam_id]['suspects'] = suspect_count
            stats_label = self.camera_stats[cam_id]['stats_label']
            stats_label.setText(f"Faces: {face_count} | Suspects: {suspect_count}")
            
    def update_overall_stats(self):
        """Update overall system statistics"""
        total_faces = sum(stats['faces'] for stats in self.camera_stats.values())
        total_suspects = sum(stats['suspects'] for stats in self.camera_stats.values())
        active_cameras = len([cam_id for cam_id in self.current_user.assigned_cameras 
                             if self.camera_manager.get_frame(cam_id) is not None])
        
        self.total_faces_label.setText(f"Total Faces: {total_faces}")
        self.suspects_label.setText(f"Suspects: {total_suspects}")
        self.active_cameras_label.setText(f"Active Cameras: {active_cameras}")
        
    def pin_camera(self, cam_id: int):
        """Pin a single camera view (admin only)"""
        if self.current_user.role != 'admin':
            return
            
        self.pinned_camera = cam_id
        
        # Clear existing displays
        for i in reversed(range(self.camera_grid_layout.count())):
            self.camera_grid_layout.itemAt(i).widget().setParent(None)
        
        # Create single camera display
        self.camera_displays.clear()
        self.camera_stats.clear()
        self.create_single_camera_display(cam_id, 0, 0)
        
        logger.info(f"Pinned camera {cam_id}")
        
    def unpin_camera(self):
        """Unpin camera and show all cameras (admin only)"""
        if self.current_user.role != 'admin':
            return
            
        self.pinned_camera = None
        
        # Clear existing displays
        for i in reversed(range(self.camera_grid_layout.count())):
            self.camera_grid_layout.itemAt(i).widget().setParent(None)
        
        # Recreate all camera displays
        self.camera_displays.clear()
        self.camera_stats.clear()
        self.create_camera_displays()
        
        logger.info("Unpinned camera - showing all cameras")
        
    def toggle_alerts(self, enabled: bool):
        """Toggle alert system (admin only)"""
        if self.current_user.role == 'admin':
            self.alert_system.enable_alerts(enabled)
            
    def toggle_screenshots(self, enabled: bool):
        """Toggle screenshot capture (admin only)"""
        if self.current_user.role == 'admin':
            self.alert_system.enable_screenshots(enabled)
            
    def restart_cameras(self):
        """Restart all cameras (admin only)"""
        if self.current_user.role == 'admin':
            self.camera_manager.stop_all_cameras()
            time.sleep(1)
            self.start_assigned_cameras()
            QMessageBox.information(self, "Success", "Cameras restarted successfully")
            
    def open_user_management(self):
        """Open user management dialog (admin only)"""
        if self.current_user.role == 'admin':
            dialog = UserManagementDialog(self.face_detector, self)
            dialog.exec_()
            
    def open_face_management(self):
        """Open face management dialog (admin only)"""
        if self.current_user.role == 'admin':
            dialog = ImprovedFaceManagerDialog(self.face_detector, self.config, self)
            dialog.exec_()
    
    def open_entry_exit_statistics(self):
        """Open entry/exit statistics dialog"""
        try:
            dialog = EntryExitStatisticsDialog(self.entry_exit_tracker, self)
            dialog.exec_()
        except Exception as e:
            logger.error(f"Error opening entry/exit statistics: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open entry/exit statistics: {str(e)}")
            
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
            
    def logout(self):
        """Logout current user"""
        reply = QMessageBox.question(self, "Logout", "Are you sure you want to logout?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()
            
    def closeEvent(self, event):
        """Handle window close event"""
        reply = QMessageBox.question(self, "Exit", "Are you sure you want to exit?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.camera_manager.stop_all_cameras()
            self.alert_system.shutdown()
            event.accept()
        else:
            event.ignore()
