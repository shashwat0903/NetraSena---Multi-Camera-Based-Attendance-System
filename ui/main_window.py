import sys
import time
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QPushButton, QTabWidget, QScrollArea, QGridLayout,
                            QMessageBox, QFileDialog, QComboBox, QSlider, QSpinBox, QFrame, QCheckBox, QGroupBox, QListWidget, QDateEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QDate
from PyQt5.QtGui import QPixmap, QImage, QIcon
from loguru import logger
from typing import Dict, Optional, Tuple
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
from core.face_tracker import FaceTracker
from .face_manager import FaceManagerDialog
from .alert_panel import AlertPanel
from .history_viewer import HistoryViewer
from core.attendance_manager import AttendanceManager

class MainWindow(QMainWindow):
    def __init__(self, config, attendance_manager: AttendanceManager):
        """
        Initialize the main window and all core components.
        
        Args:
            config (dict): The application configuration dictionary.
            attendance_manager (AttendanceManager): The attendance manager instance.
        """
        super().__init__()
        self.config = config
        self.attendance_manager = attendance_manager
        self.setWindowTitle(f"{config['app']['name']} v{config['app']['version']}")
        self.setWindowIcon(QIcon(config['app']['logo']))
        self.setGeometry(100, 100, 1200, 800)
        
        self.processing_interval = 1.0  # Increased to 1 second for better stability
        
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
        
        # UI Components
        self.init_ui()
        
        # Start camera threads
        self.camera_manager.start_all_cameras()
        
        # Setup update timer - reduced frequency for better performance
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(100)  # 10 FPS for UI updates to prevent lag
        
        # Track last processed time per camera to limit processing
        self.last_processed: Dict[int, float] = {}
        
    def init_ui(self):
        """
        Set up the main user interface, including tabs, layouts, and status/menu bars.
        """
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Add tabs
        self.setup_monitor_tab()
        self.setup_multicam_tab()
        self.setup_controls_tab()
        self.setup_history_tab()
        self.setup_attendance_tab()
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_label = QLabel("Ready")
        self.status_bar.addPermanentWidget(self.status_label)
        
        # Menu bar
        self.setup_menu_bar()
        
    def setup_menu_bar(self):
        """
        Set up the application's menu bar with actions like exiting, opening tools, and toggling fullscreen.
        """
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        exit_action = file_menu.addAction('Exit')
        exit_action.triggered.connect(self.close)
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        face_manager_action = tools_menu.addAction('Face Manager')
        face_manager_action.triggered.connect(self.open_face_manager)
        
        alert_panel_action = tools_menu.addAction('Alert Panel')
        alert_panel_action.triggered.connect(self.open_alert_panel)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        fullscreen_action = view_menu.addAction('Toggle Fullscreen')
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        
    def setup_monitor_tab(self):
        """
        Set up the 'Monitor' tab which displays live camera feeds in a scrollable grid layout.
        """

        monitor_tab = QWidget()
        self.tab_widget.addTab(monitor_tab, "Monitor")
        
        # Scroll area for camera feeds
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Container for camera feeds
        self.camera_container = QWidget()
        self.camera_grid = QGridLayout(self.camera_container)
        self.camera_grid.setSpacing(10)
        
        scroll.setWidget(self.camera_container)
        
        # Layout for monitor tab
        layout = QVBoxLayout(monitor_tab)
        layout.addWidget(scroll)
        
        # Add camera labels
        self.camera_labels = {}
        for cam_id in self.camera_manager.cameras:
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumSize(400, 300)
            self.camera_labels[cam_id] = label
            self.camera_grid.addWidget(label, (cam_id // 2), (cam_id % 2))
            
    def setup_controls_tab(self):
        """
        Set up the 'Controls' tab, which allows users to start/stop cameras,
        adjust recognition threshold, and modify processing intervals.
        """
        controls_tab = QWidget()
        self.tab_widget.addTab(controls_tab, "Controls")
        
        layout = QVBoxLayout(controls_tab)
        
        # Camera controls
        camera_group = QWidget()
        camera_layout = QVBoxLayout(camera_group)
        
        camera_title = QLabel("Camera Controls")
        camera_title.setAlignment(Qt.AlignCenter)
        camera_layout.addWidget(camera_title)
        
        # Camera selection combo
        self.camera_combo = QComboBox()
        for cam_id, cam_config in self.camera_manager.cameras.items():
            self.camera_combo.addItem(f"Camera {cam_id}: {cam_config.name}", cam_id)
        camera_layout.addWidget(self.camera_combo)
        
        # Camera control buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Camera")
        self.start_btn.clicked.connect(self.start_selected_camera)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Camera")
        self.stop_btn.clicked.connect(self.stop_selected_camera)
        btn_layout.addWidget(self.stop_btn)
        
        self.reload_config_btn = QPushButton("Reload Config")
        self.reload_config_btn.clicked.connect(self.reload_camera_config)
        btn_layout.addWidget(self.reload_config_btn)
        
        camera_layout.addLayout(btn_layout)
        
        # Recognition threshold control
        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("Recognition Threshold:")
        threshold_layout.addWidget(threshold_label)
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(50, 100)  # 0.5 to 1.0 in 0.01 increments
        self.threshold_slider.setValue(int(self.config['recognition']['recognition_threshold'] * 100))
        self.threshold_slider.valueChanged.connect(self.update_threshold)
        threshold_layout.addWidget(self.threshold_slider)
        
        self.threshold_value = QLabel(f"{self.threshold_slider.value() / 100:.2f}")
        threshold_layout.addWidget(self.threshold_value)
        
        camera_layout.addLayout(threshold_layout)
        
        layout.addWidget(camera_group)
        
        # Processing interval control
        interval_group = QWidget()
        interval_layout = QHBoxLayout(interval_group)
        
        interval_label = QLabel("Processing Interval (ms):")
        interval_layout.addWidget(interval_label)
        
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 5000)
        self.interval_spin.setValue(int(self.processing_interval * 1000))
        self.interval_spin.valueChanged.connect(self.update_processing_interval)
        interval_layout.addWidget(self.interval_spin)
        
        layout.addWidget(interval_group)
        
        # Status display
        status_group = QWidget()
        status_layout = QVBoxLayout(status_group)
        
        status_title = QLabel("System Status")
        status_title.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(status_title)
        
        self.status_display = QLabel("Loading status...")
        self.status_display.setWordWrap(True)
        status_layout.addWidget(self.status_display)
        
        layout.addWidget(status_group)
        
    def setup_history_tab(self):
        """
        Set up the 'History' tab, which displays historical records of recognized faces or alerts.
        """
        self.history_viewer = HistoryViewer(self.database, self.config)
        self.tab_widget.addTab(self.history_viewer, "History")
        
    def setup_multicam_tab(self):
        """
        Set up the multi-camera view tab with individual camera databases and controls.
        """
        multicam_tab = QWidget()
        self.tab_widget.addTab(multicam_tab, "Multi-Camera View")
        
        layout = QVBoxLayout(multicam_tab)
        
        # Controls row
        controls_layout = QHBoxLayout()
        
        # Start all cameras button
        start_all_btn = QPushButton("Start All Cameras")
        start_all_btn.clicked.connect(self.start_all_cameras)
        controls_layout.addWidget(start_all_btn)
        
        # Stop all cameras button
        stop_all_btn = QPushButton("Stop All Cameras")
        stop_all_btn.clicked.connect(self.stop_all_cameras)
        controls_layout.addWidget(stop_all_btn)
        
        # Spacer
        controls_layout.addStretch()
        
        # Status label
        self.multicam_status = QLabel("Ready")
        controls_layout.addWidget(self.multicam_status)
        
        layout.addLayout(controls_layout)
        
        # Scroll area for cameras
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Container for camera widgets
        self.multicam_container = QWidget()
        self.multicam_layout = QGridLayout(self.multicam_container)
        self.multicam_layout.setSpacing(15)
        
        scroll.setWidget(self.multicam_container)
        layout.addWidget(scroll)
        
        # Create camera widgets
        self.camera_widgets = {}
        for i, (cam_id, camera) in enumerate(self.camera_manager.cameras.items()):
            camera_widget = self.create_camera_widget(cam_id, camera)
            self.camera_widgets[cam_id] = camera_widget
            
            # Arrange in grid (2 columns)
            row = i // 2
            col = i % 2
            self.multicam_layout.addWidget(camera_widget, row, col)
    
    def create_camera_widget(self, cam_id, camera):
        """Create a widget for individual camera with controls and display"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.StyledPanel)
        widget.setMinimumSize(400, 350)
        
        layout = QVBoxLayout(widget)
        
        # Camera title and status
        title_layout = QHBoxLayout()
        title_label = QLabel(f"Camera {cam_id}: {camera.name}")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        title_layout.addWidget(title_label)
        
        status_label = QLabel("●")
        status_label.setStyleSheet("color: red; font-size: 14px;")
        title_layout.addWidget(status_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # Camera display
        camera_display = QLabel()
        camera_display.setAlignment(Qt.AlignCenter)
        camera_display.setMinimumSize(380, 280)
        camera_display.setStyleSheet("border: 1px solid gray; background-color: black;")
        camera_display.setText("Camera Stopped")
        layout.addWidget(camera_display)
        
        # Camera controls
        controls_layout = QHBoxLayout()
        
        start_btn = QPushButton("Start")
        start_btn.clicked.connect(lambda: self.start_single_camera(cam_id))
        controls_layout.addWidget(start_btn)
        
        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(lambda: self.stop_single_camera(cam_id))
        controls_layout.addWidget(stop_btn)
        
        # Detection stats
        stats_label = QLabel("Faces: 0 | Suspects: 0")
        stats_label.setStyleSheet("font-size: 10px;")
        controls_layout.addWidget(stats_label)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Store references
        widget.camera_display = camera_display
        widget.status_label = status_label
        widget.stats_label = stats_label
        widget.start_btn = start_btn
        widget.stop_btn = stop_btn
        
        return widget
    
    def setup_attendance_tab(self):
        """Sets up the attendance tab."""
        attendance_tab = QWidget()
        self.tab_widget.addTab(attendance_tab, "Attendance")
        layout = QVBoxLayout(attendance_tab)

        # Attendance mode switch
        self.attendance_mode_checkbox = QCheckBox("Enable Attendance Mode")
        self.attendance_mode_checkbox.stateChanged.connect(self.toggle_attendance_mode)
        layout.addWidget(self.attendance_mode_checkbox)

        # Control buttons
        button_layout = QHBoxLayout()
        
        self.refresh_attendance_btn = QPushButton("Refresh Daily Attendance")
        self.refresh_attendance_btn.clicked.connect(self.refresh_daily_attendance)
        button_layout.addWidget(self.refresh_attendance_btn)
        
        self.reload_known_people_btn = QPushButton("Reload Known People")
        self.reload_known_people_btn.clicked.connect(self.reload_known_people)
        button_layout.addWidget(self.reload_known_people_btn)
        
        self.test_db_btn = QPushButton("Test Database Connection")
        self.test_db_btn.clicked.connect(self.test_database_connection)
        button_layout.addWidget(self.test_db_btn)
        
        layout.addLayout(button_layout)

        # Status layout
        status_layout = QHBoxLayout()
        
        # People inside box (marked attendance today)
        inside_box = QGroupBox("Present Today (Marked Attendance)")
        self.inside_list = QListWidget()
        inside_layout = QVBoxLayout(inside_box)
        inside_layout.addWidget(self.inside_list)
        status_layout.addWidget(inside_box)

        # People outside box (haven't marked attendance today)
        outside_box = QGroupBox("Absent Today (No Attendance)")
        self.outside_list = QListWidget()
        outside_layout = QVBoxLayout(outside_box)
        outside_layout.addWidget(self.outside_list)
        status_layout.addWidget(outside_box)
        
        layout.addLayout(status_layout)

        # PDF Generation section
        pdf_layout = QVBoxLayout()
        pdf_label = QLabel("Generate Attendance PDF:")
        pdf_layout.addWidget(pdf_label)
        
        pdf_controls = QHBoxLayout()
        
        # Date selection
        self.pdf_date_edit = QDateEdit()
        self.pdf_date_edit.setDate(QDate.currentDate())
        self.pdf_date_edit.setCalendarPopup(True)
        pdf_controls.addWidget(QLabel("Select Date:"))
        pdf_controls.addWidget(self.pdf_date_edit)
        
        # Generate PDF button
        self.generate_pdf_btn = QPushButton("Generate PDF for Selected Date")
        self.generate_pdf_btn.clicked.connect(self.generate_attendance_pdf)
        pdf_controls.addWidget(self.generate_pdf_btn)
        
        pdf_layout.addLayout(pdf_controls)
        layout.addLayout(pdf_layout)

        self.update_attendance_lists()

    def refresh_daily_attendance(self):
        """Manually refresh daily attendance"""
        if hasattr(self, 'attendance_manager') and self.attendance_manager:
            self.attendance_manager.refresh_daily_attendance()
            self.update_attendance_lists()
            self.status_label.setText("Daily attendance refreshed")

    def reload_known_people(self):
        """Reload known people from the known_faces directory"""
        if hasattr(self, 'attendance_manager') and self.attendance_manager:
            self.attendance_manager.load_known_people()
            self.update_attendance_lists()
            self.status_label.setText(f"Reloaded {len(self.attendance_manager.all_known_people)} known people")

    def test_database_connection(self):
        """Test the MongoDB database connection and show debug info"""
        if hasattr(self, 'attendance_manager') and self.attendance_manager:
            success = self.attendance_manager.test_connection()
            if success:
                self.status_label.setText("Database connection test successful - check console for details")
            else:
                self.status_label.setText("Database connection test failed - check console for details")
        else:
            self.status_label.setText("Attendance manager not available")

    def toggle_attendance_mode(self, state):
        is_enabled = state == Qt.Checked
        self.status_label.setText(f"Attendance Mode: {'Enabled' if is_enabled else 'Disabled'}")

    def update_attendance_lists(self):
        """Update both inside and outside lists"""
        if not hasattr(self, 'attendance_manager') or not self.attendance_manager:
            return
            
        # Update inside list
        self.inside_list.clear()
        inside_people = self.attendance_manager.get_people_inside()
        for person in inside_people:
            self.inside_list.addItem(person)
            
        # Update outside list
        self.outside_list.clear()
        outside_people = self.attendance_manager.get_people_outside()
        for person in outside_people:
            self.outside_list.addItem(person)

    def update_outside_list(self):
        """Legacy method - now calls update_attendance_lists"""
        self.update_attendance_lists()

    def generate_attendance_pdf(self):
        """Generate PDF for the selected date"""
        if hasattr(self, 'attendance_manager') and self.attendance_manager:
            # Get selected date
            selected_date = self.pdf_date_edit.date().toPyDate()
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save PDF", 
                f"attendance_report_{selected_date.strftime('%Y%m%d')}.pdf", 
                "PDF Files (*.pdf)"
            )
            
            if file_path:
                success = self.attendance_manager.generate_attendance_pdf(file_path, selected_date)
                if success:
                    QMessageBox.information(
                        self, 
                        "Success", 
                        f"Attendance report for {selected_date} saved to {file_path}"
                    )
                else:
                    QMessageBox.warning(
                        self, 
                        "Warning", 
                        f"No attendance data found for {selected_date} or unable to generate PDF"
                    )
        else:
            QMessageBox.warning(self, "Error", "Attendance manager not available")

    def start_all_cameras(self):
        """Start all cameras and clear tracking"""
        self.camera_manager.start_all_cameras()
        self.face_tracker.clear_all_tracks()  # Clear all tracking when restarting
        self.multicam_status.setText("All cameras started")
        for cam_id, widget in self.camera_widgets.items():
            widget.status_label.setStyleSheet("color: green; font-size: 14px;")
            widget.camera_display.setText("Starting...")
    
    def stop_all_cameras(self):
        """Stop all cameras and clear tracking"""
        self.camera_manager.stop_all_cameras()
        self.face_tracker.clear_all_tracks()  # Clear all tracking when stopping
        self.multicam_status.setText("All cameras stopped")
        for cam_id, widget in self.camera_widgets.items():
            widget.status_label.setStyleSheet("color: red; font-size: 14px;")
            widget.camera_display.setText("Camera Stopped")
            widget.stats_label.setText("Faces: 0 | Suspects: 0")
    
    def start_single_camera(self, cam_id):
        """Start a single camera and clear its tracking"""
        self.camera_manager.start_camera(cam_id)
        self.face_tracker.clear_camera_tracks(cam_id)  # Clear tracking for this camera
        widget = self.camera_widgets[cam_id]
        widget.status_label.setStyleSheet("color: green; font-size: 14px;")
        widget.camera_display.setText("Starting...")
    
    def stop_single_camera(self, cam_id):
        """Stop a single camera and clear its tracking"""
        self.camera_manager.stop_camera(cam_id)
        self.face_tracker.clear_camera_tracks(cam_id)  # Clear tracking for this camera
        widget = self.camera_widgets[cam_id]
        widget.status_label.setStyleSheet("color: red; font-size: 14px;")
        widget.camera_display.setText("Camera Stopped")
        widget.stats_label.setText("Faces: 0 | Suspects: 0")

    def open_face_manager(self):
        """
        Open the face manager dialog to allow adding or removing known faces,
        and reloads known faces into the face detector after closing the dialog.
        """
        dialog = FaceManagerDialog(
            self.face_detector, 
            self.config['app']['known_faces_dir'],
            self.config['app']['suspects_dir'],
            self.camera_manager
        )
        dialog.exec_()
        # Refresh known faces after dialog closes
        self.face_detector.load_known_faces(self.config['app']['known_faces_dir'])
        
    def open_alert_panel(self):
        """
        Open the alert panel dialog to view and manage triggered alerts.
        """
        dialog = AlertPanel(self.alert_system)
        dialog.exec_()
        
    def toggle_fullscreen(self):
        """
        Toggle the application's fullscreen mode.
        """
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
            
    def start_selected_camera(self):
        """
        Start the camera selected from the combo box.
        Updates the status label upon success.
        """
        cam_id = self.camera_combo.currentData()
        if self.camera_manager.start_camera(cam_id):
            self.status_label.setText(f"Started camera {cam_id}")
            
    def stop_selected_camera(self):
        """
        Stop the camera selected from the combo box.
        Updates the status label upon success.
        """
        cam_id = self.camera_combo.currentData()
        if self.camera_manager.stop_camera(cam_id):
            self.status_label.setText(f"Stopped camera {cam_id}")
            
    def reload_camera_config(self):
        """
        Reload the camera configuration from the config file.
        Updates the camera combo box with new configurations.
        """
        try:
            self.camera_manager.reload_config('config/camera_config.yaml')
            
            # Update the camera combo box
            self.camera_combo.clear()
            for cam_id, cam_config in self.camera_manager.cameras.items():
                self.camera_combo.addItem(f"Camera {cam_id}: {cam_config.name}", cam_id)
            
            self.status_label.setText("Camera configuration reloaded successfully")
            
        except Exception as e:
            self.status_label.setText(f"Failed to reload config: {str(e)}")
            
    def update_threshold(self, value):
        """
        Update the face recognition threshold used by the face detector.
        
        Args:
            value (int): New threshold slider value (scaled to 0.0 - 1.0).
        """
        threshold = value / 100
        self.face_detector.recognition_threshold = threshold
        self.threshold_value.setText(f"{threshold:.2f}")
        
    def update_processing_interval(self, value):
        """
        Update the interval (in seconds) for how frequently frames should be processed.
        
        Args:
            value (int): Interval in milliseconds.
        """
        self.processing_interval = value / 1000
        
    def update(self):
        """
        Main update loop called by the QTimer every ~30ms.
        It fetches frames from cameras, processes them if the interval allows,
        and displays them on the GUI. Also updates system status.
        """
        try:
            # Update camera feeds
            frames = self.camera_manager.get_all_frames()
            
            for cam_id, frame in frames.items():
                if frame is None:
                    continue
                    
                # Check if we should process this frame
                current_time = time.time()
                last_time = self.last_processed.get(cam_id, 0)
                if current_time - last_time < self.processing_interval:
                    # Just display the frame without processing
                    self.display_frame(cam_id, frame)
                    continue
                    
                # Process the frame (face detection and recognition)
                processed_frame, alert_triggered = self.process_frame(cam_id, frame)
                
                # Display the processed frame
                self.display_frame(cam_id, processed_frame)
                
                # Update last processed time
                self.last_processed[cam_id] = current_time
                
            # Update status display
            self.update_status()
            
            # Update attendance lists if attendance mode is enabled
            if hasattr(self, 'attendance_manager') and self.attendance_manager and hasattr(self, 'attendance_mode_checkbox') and self.attendance_mode_checkbox.isChecked():
                self.update_attendance_lists()
            
        except Exception as e:
            logger.error(f"Error in update loop: {e}")
            self.status_label.setText(f"Error: {str(e)}")
            
    def process_frame(self, cam_id: int, frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Process a video frame for face detection and recognition with static tracking.

        Args:
            cam_id (int): ID of the camera providing the frame.
            frame (np.ndarray): The frame to process.

        Returns:
            Tuple[np.ndarray, bool]: The processed frame and a boolean indicating if an alert was triggered.
        """
        alert_triggered = False
        try:
            # Use regular detection for all cameras (enhanced detection had issues)
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
                    color = (0, 0, 255) if is_suspect else (0, 255, 0)  # Red for suspects, green for known
                    
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
            
            # Attendance processing
            if hasattr(self, 'attendance_manager') and self.attendance_manager and hasattr(self, 'attendance_mode_checkbox') and self.attendance_mode_checkbox.isChecked():
                # Track all seen people for local fallback
                if not hasattr(self.attendance_manager, '_all_seen_people'):
                    self.attendance_manager._all_seen_people = set()
                
                for face, known_face, confidence, is_suspect in recognized_faces:
                    if known_face and known_face.name != 'Unknown':
                        person_name = known_face.name
                        self.attendance_manager._all_seen_people.add(person_name)
                        
                        # Update their presence (they're currently being seen)
                        self.attendance_manager.update_person_presence(person_name)
                        
                        # Mark attendance as present (only once per day)
                        success = self.attendance_manager.mark_attendance(person_name)
                        if success:
                            logger.info(f"Marked attendance for {person_name}: present")
                        else:
                            logger.info(f"Marked local attendance for {person_name}: present")

        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            
        return frame, alert_triggered
        
    def display_frame(self, cam_id: int, frame: np.ndarray):
        """
        Display the processed frame in the corresponding camera view.

        Args:
            cam_id (int): ID of the camera.
            frame (np.ndarray): Frame to display.
        """
        try:
            if frame is None:
                return
                
            # Convert to QPixmap and display
            pixmap = numpy_to_pixmap(frame)
            
            # Update monitor tab camera labels
            if cam_id in self.camera_labels:
                self.camera_labels[cam_id].setPixmap(pixmap)
            
            # Update multi-camera view widgets
            if hasattr(self, 'camera_widgets') and cam_id in self.camera_widgets:
                widget = self.camera_widgets[cam_id]
                scaled_pixmap = pixmap.scaled(
                    widget.camera_display.width(), widget.camera_display.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation)
                widget.camera_display.setPixmap(scaled_pixmap)
                
                # Update status indicator
                widget.status_label.setStyleSheet("color: green; font-size: 14px;")
            
        except Exception as e:
            logger.error(f"Error displaying frame: {e}")
            
    def update_camera_stats(self, cam_id: int, face_count: int, suspect_count: int):
        """Update detection statistics for a specific camera"""
        try:
            if hasattr(self, 'camera_widgets') and cam_id in self.camera_widgets:
                widget = self.camera_widgets[cam_id]
                widget.stats_label.setText(f"Faces: {face_count} | Suspects: {suspect_count}")
        except Exception as e:
            logger.error(f"Error updating camera stats: {e}")

    def update_status(self):
        """
        Update the application's status display with:
        - Camera running/stopped status
        - Known faces in the database
        - Recent alerts (last 3)
        """
        try:
            status_text = []
            
            # Camera status
            status_text.append("=== Camera Status ===")
            for cam_id, cam_config in self.camera_manager.cameras.items():
                running = cam_id in self.camera_manager.capture_threads
                status_text.append(
                    f"Camera {cam_id} ({cam_config.name}): {'Running' if running else 'Stopped'}"
                )
                
            # Face database status
            status_text.append("\n=== Face Database ===")
            status_text.append(f"Known faces: {len(self.face_detector.known_faces)}")
            
            # Alert status
            status_text.append("\n=== Alerts ===")
            recent_alerts = self.alert_system.get_recent_alerts(3)
            if recent_alerts:
                for alert in recent_alerts:
                    time_str = time.strftime("%H:%M:%S", time.localtime(alert.timestamp))
                    status_text.append(
                        f"{time_str}: {alert.face_name} on {alert.camera_name} "
                        f"(Confidence: {alert.confidence:.2f})"
                    )
            else:
                status_text.append("No recent alerts")
                
            self.status_display.setText("\n".join(status_text))
            
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            
    def closeEvent(self, event):
        """
        Handle the application window close event.

        Performs cleanup:
        - Stops all camera threads
        - Stops the UI update timer
        - Saves configuration (if needed)
        """
        try:
            # Stop all cameras
            self.camera_manager.stop_all_cameras()
            
            # Stop update timer
            self.update_timer.stop()
            
            # Save configuration
            # (Add configuration saving logic here if needed)
            
            event.accept()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            event.accept()