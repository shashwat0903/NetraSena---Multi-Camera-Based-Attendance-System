from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                            QPushButton, QLabel, QFileDialog, QMessageBox, QComboBox, QDateEdit,
                            QGroupBox, QGridLayout, QTextEdit, QSplitter, QWidget, QHeaderView)
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QFont
from loguru import logger
import time
from datetime import datetime, timedelta
from pathlib import Path

class EntryExitStatisticsDialog(QDialog):
    """Dialog for viewing entry/exit statistics and exporting data"""
    
    def __init__(self, entry_exit_tracker, parent=None):
        super().__init__(parent)
        self.entry_exit_tracker = entry_exit_tracker
        self.setWindowTitle("Entry/Exit Statistics & Analytics")
        self.setGeometry(200, 200, 1200, 800)
        
        self.init_ui()
        self.load_data()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_data)
        self.refresh_timer.start(10000)  # Refresh every 10 seconds
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Entry/Exit Statistics & Analytics")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh Data")
        self.refresh_btn.clicked.connect(self.load_data)
        control_layout.addWidget(self.refresh_btn)
        
        self.export_btn = QPushButton("Export to Excel")
        self.export_btn.clicked.connect(self.export_data)
        control_layout.addWidget(self.export_btn)
        
        self.clear_old_btn = QPushButton("Clear Old Sessions")
        self.clear_old_btn.clicked.connect(self.clear_old_sessions)
        control_layout.addWidget(self.clear_old_btn)
        
        self.clear_all_btn = QPushButton("Clear All Data")
        self.clear_all_btn.clicked.connect(self.clear_all_data)
        self.clear_all_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; }")
        control_layout.addWidget(self.clear_all_btn)
        control_layout.addWidget(self.clear_old_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(main_splitter)
        
        # Current occupants section
        occupants_group = QGroupBox("Current Occupants")
        occupants_layout = QVBoxLayout(occupants_group)
        
        self.occupants_label = QLabel("Loading...")
        self.occupants_label.setWordWrap(True)
        occupants_layout.addWidget(self.occupants_label)
        
        main_splitter.addWidget(occupants_group)
        
        # Statistics table
        stats_group = QGroupBox("Person Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(8)
        self.stats_table.setHorizontalHeaderLabels([
            "Person Name", "Total Entries", "Total Exits", "Total Duration (min)",
            "Average Duration (min)", "Last Entry", "Last Exit", "Current Status"
        ])
        
        # Make table sortable and resize columns to content
        self.stats_table.setSortingEnabled(True)
        header = self.stats_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(7):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        stats_layout.addWidget(self.stats_table)
        main_splitter.addWidget(stats_group)
        
        # Recent events section
        events_group = QGroupBox("Recent Entry/Exit Events")
        events_layout = QVBoxLayout(events_group)
        
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(6)
        self.events_table.setHorizontalHeaderLabels([
            "Person Name", "Event Type", "Camera", "Date/Time", "Confidence", "Duration (min)"
        ])
        
        self.events_table.setSortingEnabled(True)
        events_header = self.events_table.horizontalHeader()
        events_header.setStretchLastSection(True)
        for i in range(5):
            events_header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        events_layout.addWidget(self.events_table)
        main_splitter.addWidget(events_group)
        
        # Set splitter proportions
        main_splitter.setSizes([100, 300, 200])
    
    def load_data(self):
        """Load and display current data"""
        try:
            logger.info("Loading entry/exit statistics data...")
            
            # Update current occupants
            occupants = self.entry_exit_tracker.get_current_occupants()
            logger.info(f"Current occupants: {occupants}")
            
            if occupants:
                occupants_text = f"People currently inside ({len(occupants)}): " + ", ".join(occupants)
            else:
                occupants_text = "No one currently inside"
            self.occupants_label.setText(occupants_text)
            
            # Update statistics table
            self.load_statistics()
            
            # Update recent events
            self.load_recent_events()
            
            logger.info("Entry/exit data loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading entry/exit data: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.warning(self, "Error", f"Failed to load data: {str(e)}")
    
    def load_statistics(self):
        """Load person statistics into table"""
        try:
            stats = self.entry_exit_tracker.get_person_statistics()
            
            self.stats_table.setRowCount(len(stats))
            
            for row, stat in enumerate(stats):
                # Person name
                self.stats_table.setItem(row, 0, QTableWidgetItem(stat['person_name']))
                
                # Total entries
                self.stats_table.setItem(row, 1, QTableWidgetItem(str(stat['total_entries'])))
                
                # Total exits
                self.stats_table.setItem(row, 2, QTableWidgetItem(str(stat['total_exits'])))
                
                # Total duration
                duration_text = f"{stat['total_duration_minutes']:.1f}" if stat['total_duration_minutes'] else "0.0"
                self.stats_table.setItem(row, 3, QTableWidgetItem(duration_text))
                
                # Average duration
                avg_duration_text = f"{stat['average_duration_minutes']:.1f}" if stat['average_duration_minutes'] else "0.0"
                self.stats_table.setItem(row, 4, QTableWidgetItem(avg_duration_text))
                
                # Last entry
                last_entry = ""
                if stat['last_entry_time']:
                    last_entry = datetime.fromtimestamp(stat['last_entry_time']).strftime("%Y-%m-%d %H:%M:%S")
                self.stats_table.setItem(row, 5, QTableWidgetItem(last_entry))
                
                # Last exit
                last_exit = ""
                if stat['last_exit_time']:
                    last_exit = datetime.fromtimestamp(stat['last_exit_time']).strftime("%Y-%m-%d %H:%M:%S")
                self.stats_table.setItem(row, 6, QTableWidgetItem(last_exit))
                
                # Current status
                status_item = QTableWidgetItem(stat['current_status'])
                if stat['current_status'] == 'inside':
                    status_item.setBackground(Qt.green)
                else:
                    status_item.setBackground(Qt.lightGray)
                self.stats_table.setItem(row, 7, status_item)
                
        except Exception as e:
            logger.error(f"Error loading statistics: {e}")
    
    def load_recent_events(self):
        """Load recent entry/exit events"""
        try:
            import sqlite3
            
            with sqlite3.connect(self.entry_exit_tracker.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT person_name, event_type, camera_name, timestamp, confidence, duration_minutes
                    FROM entry_exit_events 
                    ORDER BY timestamp DESC 
                    LIMIT 50
                ''')
                events = cursor.fetchall()
            
            self.events_table.setRowCount(len(events))
            
            for row, event in enumerate(events):
                # Person name
                self.events_table.setItem(row, 0, QTableWidgetItem(event[0]))
                
                # Event type
                event_item = QTableWidgetItem(event[1].upper())
                if event[1] == 'entry':
                    event_item.setBackground(Qt.lightGreen)
                else:
                    event_item.setBackground(Qt.lightBlue)
                self.events_table.setItem(row, 1, event_item)
                
                # Camera name
                self.events_table.setItem(row, 2, QTableWidgetItem(event[2]))
                
                # Date/time
                datetime_str = datetime.fromtimestamp(event[3]).strftime("%Y-%m-%d %H:%M:%S")
                self.events_table.setItem(row, 3, QTableWidgetItem(datetime_str))
                
                # Confidence
                confidence_text = f"{event[4]:.2%}" if event[4] else ""
                self.events_table.setItem(row, 4, QTableWidgetItem(confidence_text))
                
                # Duration
                duration_text = f"{event[5]:.1f}" if event[5] else ""
                self.events_table.setItem(row, 5, QTableWidgetItem(duration_text))
                
        except Exception as e:
            logger.error(f"Error loading recent events: {e}")
    
    def export_data(self):
        """Export data to Excel file"""
        try:
            # Get save location
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"entry_exit_data_{timestamp}.xlsx"
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Entry/Exit Data", default_filename,
                "Excel Files (*.xlsx);;All Files (*)"
            )
            
            if filename:
                success = self.entry_exit_tracker.export_to_excel(filename)
                if success:
                    QMessageBox.information(self, "Success", f"Data exported successfully to {filename}")
                else:
                    QMessageBox.warning(self, "Error", "Failed to export data")
                    
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
    
    def clear_old_sessions(self):
        """Clear old sessions without exit records"""
        try:
            reply = QMessageBox.question(
                self, "Confirm", 
                "This will clean up sessions older than 24 hours without exit records. Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.entry_exit_tracker.cleanup_old_sessions(24)
                self.load_data()
                QMessageBox.information(self, "Success", "Old sessions cleaned up successfully")
                
        except Exception as e:
            logger.error(f"Error clearing old sessions: {e}")
            QMessageBox.critical(self, "Error", f"Failed to clear old sessions: {str(e)}")

    def clear_all_data(self):
        """Clear all entry/exit data"""
        try:
            reply = QMessageBox.question(
                self, "Confirm Clear All Data", 
                "⚠️ WARNING: This will permanently delete ALL entry/exit data including:\n\n"
                "• All entry/exit events\n"
                "• All person sessions\n" 
                "• All statistics\n"
                "• Active sessions in memory\n\n"
                "This action cannot be undone. Are you sure?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Double confirmation
                confirm_reply = QMessageBox.question(
                    self, "Final Confirmation",
                    "Last chance! This will delete ALL data permanently.\n\nProceed?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if confirm_reply == QMessageBox.Yes:
                    success = self.entry_exit_tracker.clear_all_data()
                    if success:
                        self.load_data()
                        QMessageBox.information(self, "Success", "All entry/exit data cleared successfully")
                    else:
                        QMessageBox.critical(self, "Error", "Failed to clear all data. Check logs for details.")
                
        except Exception as e:
            logger.error(f"Error clearing all data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to clear all data: {str(e)}")
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        event.accept()
