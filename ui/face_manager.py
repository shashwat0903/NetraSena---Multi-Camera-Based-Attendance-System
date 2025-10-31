import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
                            QLabel, QFileDialog, QMessageBox, QLineEdit, QComboBox, QTabWidget, QWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from loguru import logger
import cv2
import numpy as np
from pathlib import Path

from core.utils import numpy_to_pixmap, resize_image

class FaceManagerDialog(QDialog):
    def __init__(self, face_detector, known_faces_dir, suspects_dir, camera_manager):
        """
        Initialize the FaceManagerDialog.

        Args:
            face_detector: An instance responsible for face detection and management.
            known_faces_dir (str or Path): Directory path where known face images are stored.
            suspects_dir (str or Path): Directory path where suspect face images are stored.
            camera_manager: Camera manager instance for live capture.
        """
        super().__init__()
        self.face_detector = face_detector
        self.known_faces_dir = known_faces_dir
        self.suspects_dir = suspects_dir
        self.camera_manager = camera_manager
        self.current_image = None
        self.capture_mode = False
        self.camera_timer = QTimer()
        self.camera_timer.timeout.connect(self.update_camera_feed)
        
        self.setWindowTitle("NetraSena - Face Manager")
        self.setGeometry(200, 200, 1000, 700)
        
        self.init_ui()
        self.load_face_lists()
        
    def init_ui(self):
        """
        Set up the UI components with tabs for Known Faces and Suspects.
        """
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Known Faces Tab
        self.known_faces_tab = self.create_face_tab("known")
        self.tab_widget.addTab(self.known_faces_tab, "Known Faces")
        
        # Suspects Tab
        self.suspects_tab = self.create_face_tab("suspect")
        self.tab_widget.addTab(self.suspects_tab, "Suspects")
        
        layout.addWidget(self.tab_widget)
        
        # Live Camera Capture Controls
        camera_layout = QHBoxLayout()
        
        self.start_camera_btn = QPushButton("Start Live Camera")
        self.start_camera_btn.clicked.connect(self.start_camera_capture)
        camera_layout.addWidget(self.start_camera_btn)
        
        self.stop_camera_btn = QPushButton("Stop Camera")
        self.stop_camera_btn.clicked.connect(self.stop_camera_capture)
        self.stop_camera_btn.setEnabled(False)
        camera_layout.addWidget(self.stop_camera_btn)
        
        self.capture_btn = QPushButton("Capture Face")
        self.capture_btn.clicked.connect(self.capture_face_from_camera)
        self.capture_btn.setEnabled(False)
        camera_layout.addWidget(self.capture_btn)
        
        layout.addLayout(camera_layout)
        
        # Close button
        close_layout = QHBoxLayout()
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        close_layout.addWidget(self.close_btn)
        layout.addLayout(close_layout)
        
        self.setLayout(layout)
        
    def create_face_tab(self, face_type):
        """Create a tab for either known faces or suspects"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Top section - face list and controls
        top_layout = QHBoxLayout()
        
        # Face list
        face_list = QListWidget()
        if face_type == "known":
            self.known_face_list = face_list
            face_list.currentItemChanged.connect(lambda c, p: self.on_face_selected(c, p, "known"))
        else:
            self.suspect_list = face_list
            face_list.currentItemChanged.connect(lambda c, p: self.on_face_selected(c, p, "suspect"))
        
        top_layout.addWidget(face_list, 3)
        
        # Face preview
        face_preview = QLabel()
        face_preview.setAlignment(Qt.AlignCenter)
        face_preview.setMinimumSize(300, 300)
        face_preview.setStyleSheet("border: 1px solid gray;")
        
        if face_type == "known":
            self.known_face_preview = face_preview
        else:
            self.suspect_preview = face_preview
            
        top_layout.addWidget(face_preview, 2)
        
        layout.addLayout(top_layout)
        
        # Middle section - face details
        middle_layout = QHBoxLayout()
        
        # Name input
        name_layout = QVBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        name_input = QLineEdit()
        
        if face_type == "known":
            self.known_name_input = name_input
        else:
            self.suspect_name_input = name_input
            
        name_layout.addWidget(name_input)
        middle_layout.addLayout(name_layout)
        
        layout.addLayout(middle_layout)
        
        # Bottom section - buttons
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton(f"Add {'Person' if face_type == 'known' else 'Suspect'}")
        add_btn.clicked.connect(lambda: self.add_face(face_type))
        button_layout.addWidget(add_btn)
        
        update_btn = QPushButton(f"Update {'Person' if face_type == 'known' else 'Suspect'}")
        update_btn.clicked.connect(lambda: self.update_face(face_type))
        button_layout.addWidget(update_btn)
        
        delete_btn = QPushButton(f"Delete {'Person' if face_type == 'known' else 'Suspect'}")
        delete_btn.clicked.connect(lambda: self.delete_face(face_type))
        button_layout.addWidget(delete_btn)
        
        import_btn = QPushButton("Import Image")
        import_btn.clicked.connect(lambda: self.import_image(face_type))
        button_layout.addWidget(import_btn)
        
        layout.addLayout(button_layout)
        
        return tab
        
    def load_face_lists(self):
        """Load both known faces and suspects lists"""
        self.load_face_list("known")
        self.load_face_list("suspect")
        
    def load_face_list(self, face_type):
        """
        Load and display face images from the directory into the list widget.
        Only image files with extensions .jpg, .jpeg, .png are considered.
        """
        if face_type == "known":
            face_list = self.known_face_list
            directory = self.known_faces_dir
        else:
            face_list = self.suspect_list
            directory = self.suspects_dir
            
        face_list.clear()
        directory = Path(directory)
        
        if not directory.exists():
            logger.warning(f"{face_type.title()} faces directory {directory} does not exist")
            return
            
        for face_file in directory.glob('*.*'):
            if face_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                face_list.addItem(face_file.stem)
                
    def on_face_selected(self, current, previous, face_type):
        """
        Triggered when a face is selected from the list.

        Args:
            current: The currently selected QListWidgetItem.
            previous: The previously selected QListWidgetItem.
            face_type: Either "known" or "suspect"
        """
        if face_type == "known":
            preview = self.known_face_preview
            name_input = self.known_name_input
            directory = self.known_faces_dir
        else:
            preview = self.suspect_preview
            name_input = self.suspect_name_input
            directory = self.suspects_dir
            
        if current is None:
            preview.clear()
            name_input.clear()
            return
            
        face_name = current.text()
        name_input.setText(face_name)
        
        # Load and display the face image
        face_path = Path(directory) / f"{face_name}{self.get_face_extension(face_name, directory)}"
        if not face_path.exists():
            QMessageBox.warning(self, "Error", f"Image file not found: {face_path}")
            return
            
        try:
            image = cv2.imread(str(face_path))
            if image is None:
                raise ValueError("Could not read image")
                
            self.current_image = image
            pixmap = numpy_to_pixmap(image)
            preview.setPixmap(pixmap.scaled(
                preview.width(), preview.height(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
            logger.error(f"Error loading face image: {e}")
            
    def get_face_extension(self, face_name: str, directory: str) -> str:
        """
        Search for the file extension of a face image by checking common image formats.

        Args:
            face_name (str): The base filename (without extension) of the face.
            directory (str): The directory to search in.

        Returns:
            str: The file extension including the dot (e.g., '.jpg'), or empty string if not found.
        """
        directory = Path(directory)
        for ext in ['.jpg', '.jpeg', '.png']:
            if (directory / f"{face_name}{ext}").exists():
                return ext
        return ''
        
    def add_face(self, face_type):
        """
        Add a new face image and update the face detector.
        
        Args:
            face_type: Either "known" or "suspect"
        """
        if face_type == "known":
            name_input = self.known_name_input
            directory = self.known_faces_dir
        else:
            name_input = self.suspect_name_input
            directory = self.suspects_dir
            
        name = name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", f"Please enter a name for the {face_type}")
            return
            
        if self.current_image is None:
            QMessageBox.warning(self, "Error", "Please import or capture an image first")
            return
            
        # Check if face already exists
        existing_files = list(Path(directory).glob(f"{name}.*"))
        if existing_files:
            QMessageBox.warning(self, "Error", f"A {face_type} with name '{name}' already exists")
            return
            
        # Add the face
        if face_type == "known":
            success = self.face_detector.add_known_face(self.current_image, name, directory)
        else:
            success = self.face_detector.add_suspect(self.current_image, name, directory)
            
        if success:
            QMessageBox.information(self, "Success", f"{face_type.title()} '{name}' added successfully")
            self.load_face_list(face_type)
        else:
            QMessageBox.warning(self, "Error", f"Failed to add {face_type}")
            
    def update_face(self, face_type):
        """
        Update an existing face with new image data.
        
        Args:
            face_type: Either "known" or "suspect"
        """
        if face_type == "known":
            face_list = self.known_face_list
            name_input = self.known_name_input
            directory = self.known_faces_dir
        else:
            face_list = self.suspect_list
            name_input = self.suspect_name_input
            directory = self.suspects_dir
            
        current_item = face_list.currentItem()
        if current_item is None:
            QMessageBox.warning(self, "Error", f"Please select a {face_type} to update")
            return
            
        old_name = current_item.text()
        new_name = name_input.text().strip()
        
        if not new_name:
            QMessageBox.warning(self, "Error", "Please enter a name")
            return
            
        if self.current_image is None:
            QMessageBox.warning(self, "Error", "Please import or capture an image first")
            return
            
        try:
            # Remove old face file
            old_extension = self.get_face_extension(old_name, directory)
            if old_extension:
                old_path = Path(directory) / f"{old_name}{old_extension}"
                if old_path.exists():
                    old_path.unlink()
                    
            # Add new face
            if face_type == "known":
                success = self.face_detector.add_known_face(self.current_image, new_name, directory)
                # Remove from known faces list and reload
                self.face_detector.load_known_faces(directory)
            else:
                success = self.face_detector.add_suspect(self.current_image, new_name, directory)
                # Remove from suspects list and reload
                self.face_detector.load_suspects(directory)
                
            if success:
                QMessageBox.information(self, "Success", f"{face_type.title()} updated successfully")
                self.load_face_list(face_type)
            else:
                QMessageBox.warning(self, "Error", f"Failed to update {face_type}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error updating {face_type}: {str(e)}")
            logger.error(f"Error updating {face_type}: {e}")
            
    def delete_face(self, face_type):
        """
        Delete the selected face from the database and file system.
        
        Args:
            face_type: Either "known" or "suspect"
        """
        if face_type == "known":
            face_list = self.known_face_list
            directory = self.known_faces_dir
        else:
            face_list = self.suspect_list
            directory = self.suspects_dir
            
        current_item = face_list.currentItem()
        if current_item is None:
            QMessageBox.warning(self, "Error", f"Please select a {face_type} to delete")
            return
            
        face_name = current_item.text()
        
        # Confirm deletion
        reply = QMessageBox.question(self, "Confirm Deletion", 
                                    f"Are you sure you want to delete {face_type} '{face_name}'?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
            
        try:
            # Remove from detector
            if face_type == "known":
                # Remove from known faces list
                self.face_detector.known_faces = [kf for kf in self.face_detector.known_faces if kf.name != face_name]
            else:
                # Remove from suspects list
                success = self.face_detector.remove_suspect(face_name)
                if not success:
                    QMessageBox.warning(self, "Error", f"Failed to remove {face_type} from detector")
                    
            # Remove file
            extension = self.get_face_extension(face_name, directory)
            if extension:
                file_path = Path(directory) / f"{face_name}{extension}"
                if file_path.exists():
                    file_path.unlink()
                    
            QMessageBox.information(self, "Success", f"{face_type.title()} '{face_name}' deleted successfully")
            self.load_face_list(face_type)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error deleting {face_type}: {str(e)}")
            logger.error(f"Error deleting {face_type}: {e}")
            
    def import_image(self, face_type):
        """
        Import an image file for face recognition.
        
        Args:
            face_type: Either "known" or "suspect"
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {face_type.title()} Image", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)")
            
        if not file_path:
            return
            
        try:
            image = cv2.imread(file_path)
            if image is None:
                QMessageBox.critical(self, "Error", "Failed to load the selected image")
                return
                
            self.current_image = image
            
            # Display the image
            if face_type == "known":
                preview = self.known_face_preview
            else:
                preview = self.suspect_preview
                
            pixmap = numpy_to_pixmap(image)
            preview.setPixmap(pixmap.scaled(
                preview.width(), preview.height(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation))
                
            QMessageBox.information(self, "Success", "Image imported successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error importing image: {str(e)}")
            logger.error(f"Error importing image: {e}")

    def closeEvent(self, event):
        """Handle dialog closing"""
        if self.capture_mode:
            self.stop_camera_capture()
        event.accept()

    def start_camera_capture(self):
        """Start live camera capture for face detection"""
        try:
            # Get the first available camera
            for cam_id, camera in self.camera_manager.cameras.items():
                if camera.enabled:
                    self.capture_camera = cv2.VideoCapture(camera.source)
                    if self.capture_camera.isOpened():
                        self.capture_mode = True
                        self.camera_timer.start(30)  # 30ms refresh rate
                        self.start_camera_btn.setEnabled(False)
                        self.stop_camera_btn.setEnabled(True)
                        self.capture_btn.setEnabled(True)
                        logger.info("Camera capture started")
                        return
                        
            QMessageBox.warning(self, "Error", "No available cameras found")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start camera: {str(e)}")
            logger.error(f"Error starting camera capture: {e}")
    
    def stop_camera_capture(self):
        """Stop live camera capture"""
        try:
            self.capture_mode = False
            self.camera_timer.stop()
            
            if hasattr(self, 'capture_camera'):
                self.capture_camera.release()
                del self.capture_camera
                
            self.start_camera_btn.setEnabled(True)
            self.stop_camera_btn.setEnabled(False)
            self.capture_btn.setEnabled(False)
            
            # Clear camera preview on current tab
            current_tab = self.tab_widget.currentIndex()
            if current_tab == 0:  # Known faces tab
                self.known_face_preview.clear()
                self.known_face_preview.setText("Camera stopped")
            else:  # Suspects tab
                self.suspect_preview.clear()
                self.suspect_preview.setText("Camera stopped")
                
            logger.info("Camera capture stopped")
            
        except Exception as e:
            logger.error(f"Error stopping camera capture: {e}")
    
    def update_camera_feed(self):
        """Update camera feed display"""
        if not self.capture_mode or not hasattr(self, 'capture_camera'):
            return
            
        try:
            ret, frame = self.capture_camera.read()
            if ret:
                # Detect faces in the frame
                faces = self.face_detector.detect_faces(frame)
                
                # Draw face bounding boxes
                display_frame = frame.copy()
                for face in faces:
                    bbox = face.bbox.astype(int)
                    cv2.rectangle(display_frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Face detected", (bbox[0], bbox[1]-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # Convert to QPixmap and display
                pixmap = numpy_to_pixmap(display_frame)
                
                # Show on current tab
                current_tab = self.tab_widget.currentIndex()
                if current_tab == 0:  # Known faces tab
                    self.known_face_preview.setPixmap(pixmap.scaled(
                        self.known_face_preview.width(), self.known_face_preview.height(),
                        Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:  # Suspects tab
                    self.suspect_preview.setPixmap(pixmap.scaled(
                        self.suspect_preview.width(), self.suspect_preview.height(),
                        Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        
        except Exception as e:
            logger.error(f"Error updating camera feed: {e}")
    
    def capture_face_from_camera(self):
        """Capture the current camera frame for face adding"""
        if not self.capture_mode or not hasattr(self, 'capture_camera'):
            QMessageBox.warning(self, "Error", "Camera is not active")
            return
            
        try:
            ret, frame = self.capture_camera.read()
            if ret:
                # Detect faces in the frame
                faces = self.face_detector.detect_faces(frame)
                
                if len(faces) == 0:
                    QMessageBox.warning(self, "No Face", "No faces detected in the current frame")
                    return
                elif len(faces) > 1:
                    QMessageBox.warning(self, "Multiple Faces", "Multiple faces detected. Please ensure only one face is visible.")
                    return
                
                # Use the detected face
                face = faces[0]
                bbox = face.bbox.astype(int)
                
                # Extract face region with some padding
                padding = 20
                x1 = max(0, bbox[0] - padding)
                y1 = max(0, bbox[1] - padding)
                x2 = min(frame.shape[1], bbox[2] + padding)
                y2 = min(frame.shape[0], bbox[3] + padding)
                
                face_image = frame[y1:y2, x1:x2]
                self.current_image = face_image
                
                QMessageBox.information(self, "Face Captured", "Face captured successfully! Enter a name and click Add.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to capture face: {str(e)}")
            logger.error(f"Error capturing face from camera: {e}")