import os
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
                            QLabel, QFileDialog, QMessageBox, QLineEdit, QComboBox, QTabWidget, 
                            QWidget, QFrame, QGridLayout, QTextEdit, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont
from loguru import logger
import cv2
import numpy as np
from pathlib import Path
import shutil

from core.utils import numpy_to_pixmap, resize_image

class ImprovedFaceManagerDialog(QDialog):
    def __init__(self, face_detector, config, parent=None):
        """
        Initialize the improved FaceManagerDialog with upload functionality.
        """
        super().__init__(parent)
        self.face_detector = face_detector
        self.config = config
        self.known_faces_dir = Path(config['app']['known_faces_dir'])
        self.suspects_dir = Path(config['app']['suspects_dir'])
        self.current_image = None
        self.current_face_type = "known"
        
        # Ensure directories exist
        self.known_faces_dir.mkdir(parents=True, exist_ok=True)
        self.suspects_dir.mkdir(parents=True, exist_ok=True)
        
        self.setWindowTitle("NetraSena - Face Management")
        self.setGeometry(200, 200, 1200, 800)
        
        self.init_ui()
        self.load_face_lists()
        
    def init_ui(self):
        """Set up the UI components with tabs for Known Faces and Suspects."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Face Management System")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Known Faces Tab
        self.known_faces_tab = self.create_face_management_tab("known")
        self.tab_widget.addTab(self.known_faces_tab, "Known Faces")
        
        # Suspects Tab
        self.suspects_tab = self.create_face_management_tab("suspect")
        self.tab_widget.addTab(self.suspects_tab, "Suspects")
        
        layout.addWidget(self.tab_widget)
        
        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        close_layout.addWidget(self.close_btn)
        layout.addLayout(close_layout)
        
        self.setLayout(layout)
        
    def create_face_management_tab(self, face_type):
        """Create a comprehensive face management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left panel - Face list
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.StyledPanel)
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        # Face list
        list_label = QLabel(f"{'Known Faces' if face_type == 'known' else 'Suspects'}")
        list_label.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(list_label)
        
        face_list = QListWidget()
        face_list.setMinimumHeight(400)
        if face_type == "known":
            self.known_face_list = face_list
            face_list.currentItemChanged.connect(lambda c, p: self.on_face_selected(c, p, "known"))
        else:
            self.suspect_face_list = face_list
            face_list.currentItemChanged.connect(lambda c, p: self.on_face_selected(c, p, "suspect"))
        left_layout.addWidget(face_list)
        
        # Delete button
        delete_btn = QPushButton(f"Delete Selected {'Face' if face_type == 'known' else 'Suspect'}")
        delete_btn.clicked.connect(lambda: self.delete_face(face_type))
        left_layout.addWidget(delete_btn)
        
        content_layout.addWidget(left_panel)
        
        # Right panel - Add/Edit faces
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        
        # Add face section
        add_label = QLabel(f"Add New {'Face' if face_type == 'known' else 'Suspect'}")
        add_label.setFont(QFont("Arial", 12, QFont.Bold))
        right_layout.addWidget(add_label)
        
        # Name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText(f"Enter {'person' if face_type == 'known' else 'suspect'} name")
        if face_type == "known":
            self.known_name_input = name_input
        else:
            self.suspect_name_input = name_input
        name_layout.addWidget(name_input)
        right_layout.addLayout(name_layout)
        
        # Image preview
        preview_label = QLabel("Image Preview:")
        preview_label.setFont(QFont("Arial", 10, QFont.Bold))
        right_layout.addWidget(preview_label)
        
        image_preview = QLabel()
        image_preview.setMinimumSize(300, 200)
        image_preview.setMaximumSize(300, 200)
        image_preview.setStyleSheet("border: 2px solid black; background-color: #f0f0f0;")
        image_preview.setAlignment(Qt.AlignCenter)
        image_preview.setText("No Image Selected")
        if face_type == "known":
            self.known_image_preview = image_preview
        else:
            self.suspect_image_preview = image_preview
        right_layout.addWidget(image_preview)
        
        # Upload button
        upload_btn = QPushButton("Upload Image")
        upload_btn.clicked.connect(lambda: self.upload_image(face_type))
        right_layout.addWidget(upload_btn)
        
        # Add face button
        add_btn = QPushButton(f"Add {'Face' if face_type == 'known' else 'Suspect'}")
        add_btn.clicked.connect(lambda: self.add_face(face_type))
        right_layout.addWidget(add_btn)
        
        # Selected face details
        right_layout.addWidget(QLabel(""))  # Spacer
        details_label = QLabel("Selected Face Details:")
        details_label.setFont(QFont("Arial", 10, QFont.Bold))
        right_layout.addWidget(details_label)
        
        details_text = QTextEdit()
        details_text.setMaximumHeight(100)
        details_text.setReadOnly(True)
        if face_type == "known":
            self.known_details_text = details_text
        else:
            self.suspect_details_text = details_text
        right_layout.addWidget(details_text)
        
        # Edit selected face
        edit_name_layout = QHBoxLayout()
        edit_name_layout.addWidget(QLabel("Edit Name:"))
        edit_name_input = QLineEdit()
        if face_type == "known":
            self.known_edit_name_input = edit_name_input
        else:
            self.suspect_edit_name_input = edit_name_input
        edit_name_layout.addWidget(edit_name_input)
        right_layout.addLayout(edit_name_layout)
        
        # Update face button
        update_btn = QPushButton(f"Update {'Face' if face_type == 'known' else 'Suspect'}")
        update_btn.clicked.connect(lambda: self.update_face(face_type))
        right_layout.addWidget(update_btn)
        
        right_layout.addStretch()
        content_layout.addWidget(right_panel)
        
        layout.addLayout(content_layout)
        return tab
        
    def upload_image(self, face_type):
        """Upload an image file for face recognition"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, 
            f"Select {'Face' if face_type == 'known' else 'Suspect'} Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        if file_path:
            try:
                # Load and display the image
                image = cv2.imread(file_path)
                if image is None:
                    QMessageBox.warning(self, "Error", "Could not load the selected image.")
                    return
                
                # Store the image
                self.current_image = image
                self.current_face_type = face_type
                
                # Display preview
                preview_widget = self.known_image_preview if face_type == "known" else self.suspect_image_preview
                
                # Resize image for preview
                height, width = image.shape[:2]
                if height > 200 or width > 300:
                    scale = min(300/width, 200/height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    resized_image = cv2.resize(image, (new_width, new_height))
                else:
                    resized_image = image
                
                # Convert to QPixmap and display
                rgb_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
                pixmap = numpy_to_pixmap(rgb_image)
                if pixmap:
                    preview_widget.setPixmap(pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                
                logger.info(f"Image uploaded for {face_type}")
                
            except Exception as e:
                logger.error(f"Error uploading image: {e}")
                QMessageBox.warning(self, "Error", f"Error loading image: {e}")
    
    def add_face(self, face_type):
        """Add a new face to the database"""
        name_input = self.known_name_input if face_type == "known" else self.suspect_name_input
        name = name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a name.")
            return
        
        if self.current_image is None or self.current_face_type != face_type:
            QMessageBox.warning(self, "Error", "Please upload an image first.")
            return
        
        try:
            # Detect faces in the uploaded image
            faces = self.face_detector.detect_faces(self.current_image)
            
            if not faces:
                QMessageBox.warning(self, "Error", "No faces detected in the uploaded image. Please try another image.")
                return
            
            if len(faces) > 1:
                reply = QMessageBox.question(
                    self, "Multiple Faces", 
                    f"Multiple faces detected. Use the first detected face?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            
            # Use the first detected face
            face = faces[0]
            
            # Save to appropriate directory
            save_dir = self.known_faces_dir if face_type == "known" else self.suspects_dir
            
            # Create filename
            import time
            timestamp = int(time.time())
            filename = f"{name}_{timestamp}.jpg"
            file_path = save_dir / filename
            
            # Save the image
            cv2.imwrite(str(file_path), self.current_image)
            
            # Add to face detector
            if face_type == "known":
                success = self.face_detector.add_known_face(self.current_image, name, str(self.known_faces_dir))
            else:
                success = self.face_detector.add_suspect(self.current_image, name, str(self.suspects_dir))
            
            if success:
                QMessageBox.information(self, "Success", f"{'Face' if face_type == 'known' else 'Suspect'} '{name}' added successfully!")
                
                # Clear inputs
                name_input.clear()
                self.current_image = None
                preview_widget = self.known_image_preview if face_type == "known" else self.suspect_image_preview
                preview_widget.setText("No Image Selected")
                preview_widget.setPixmap(QPixmap())
                
                # Reload face lists
                self.load_face_lists()
                
            else:
                QMessageBox.warning(self, "Error", f"Failed to add {'face' if face_type == 'known' else 'suspect'}.")
                
        except Exception as e:
            logger.error(f"Error adding {face_type}: {e}")
            QMessageBox.warning(self, "Error", f"Error adding {'face' if face_type == 'known' else 'suspect'}: {e}")
    
    def delete_face(self, face_type):
        """Delete selected face"""
        face_list = self.known_face_list if face_type == "known" else self.suspect_face_list
        current_item = face_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a face to delete.")
            return
        
        face_name = current_item.text().split(" (")[0]  # Remove file info
        
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete '{face_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if face_type == "suspect":
                    # Remove from suspects
                    success = self.face_detector.remove_suspect(face_name)
                else:
                    # Remove known face (find and delete file)
                    success = self.delete_known_face_file(face_name)
                
                if success:
                    QMessageBox.information(self, "Success", f"{'Face' if face_type == 'known' else 'Suspect'} deleted successfully!")
                    self.load_face_lists()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete face.")
                    
            except Exception as e:
                logger.error(f"Error deleting {face_type}: {e}")
                QMessageBox.warning(self, "Error", f"Error deleting face: {e}")
    
    def delete_known_face_file(self, face_name):
        """Delete known face file"""
        try:
            for file_path in self.known_faces_dir.glob("*"):
                if file_path.stem.startswith(face_name):
                    file_path.unlink()
                    logger.info(f"Deleted known face file: {file_path}")
                    # Reload known faces
                    self.face_detector.load_known_faces(str(self.known_faces_dir))
                    return True
            return False
        except Exception as e:
            logger.error(f"Error deleting known face file: {e}")
            return False
    
    def update_face(self, face_type):
        """Update selected face name"""
        face_list = self.known_face_list if face_type == "known" else self.suspect_face_list
        edit_input = self.known_edit_name_input if face_type == "known" else self.suspect_edit_name_input
        
        current_item = face_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a face to update.")
            return
        
        new_name = edit_input.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Error", "Please enter a new name.")
            return
        
        old_name = current_item.text().split(" (")[0]
        
        try:
            # For known faces, rename file
            if face_type == "known":
                for file_path in self.known_faces_dir.glob("*"):
                    if file_path.stem.startswith(old_name):
                        new_filename = file_path.name.replace(old_name, new_name)
                        new_path = file_path.parent / new_filename
                        file_path.rename(new_path)
                        logger.info(f"Renamed {file_path} to {new_path}")
                        break
                
                # Reload known faces
                self.face_detector.load_known_faces(str(self.known_faces_dir))
                
            else:
                # For suspects, update in memory (would need database update)
                QMessageBox.information(self, "Info", "Suspect name update not implemented yet.")
                return
            
            QMessageBox.information(self, "Success", f"{'Face' if face_type == 'known' else 'Suspect'} name updated successfully!")
            edit_input.clear()
            self.load_face_lists()
            
        except Exception as e:
            logger.error(f"Error updating {face_type}: {e}")
            QMessageBox.warning(self, "Error", f"Error updating face: {e}")
    
    def on_face_selected(self, current, previous, face_type):
        """Handle face selection"""
        if current is None:
            return
        
        face_name = current.text().split(" (")[0]
        details_text = self.known_details_text if face_type == "known" else self.suspect_details_text
        edit_input = self.known_edit_name_input if face_type == "known" else self.suspect_edit_name_input
        
        # Update details
        details_text.setText(f"Name: {face_name}\nType: {'Known Face' if face_type == 'known' else 'Suspect'}")
        
        # Set edit input
        edit_input.setText(face_name)
    
    def load_face_lists(self):
        """Load face lists from directories"""
        try:
            # Load known faces
            self.known_face_list.clear()
            if self.known_faces_dir.exists():
                for file_path in self.known_faces_dir.glob("*.jpg"):
                    face_name = file_path.stem.split("_")[0]  # Remove timestamp
                    self.known_face_list.addItem(f"{face_name} ({file_path.name})")
            
            # Load suspects
            self.suspect_face_list.clear()
            if self.suspects_dir.exists():
                for file_path in self.suspects_dir.glob("*.jpg"):
                    face_name = file_path.stem
                    self.suspect_face_list.addItem(f"{face_name} ({file_path.name})")
                    
            logger.info("Face lists loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading face lists: {e}")
