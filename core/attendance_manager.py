import pymongo
import certifi
from datetime import datetime, timedelta, date
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import logging
import time
import os

class AttendanceManager:
    def __init__(self, db_name='attendance_system', collection_name='attendance'):
        self.client = None
        self.db = None
        self.collection = None
        self.connected = False
        
        # Track people currently inside (person_name -> last_seen_time)
        self.people_inside = {}
        self.exit_timeout = 300  # 5 minutes - mark as exit if not seen for this long
        
        # Track the current day for automatic daily refresh
        self.current_date = date.today()
        
        # Load all known people from known_faces directory
        self.all_known_people = set()
        self.load_known_people()
        
        try:
            # Try multiple connection approaches
            connection_strings = [
                "mongodb+srv://shashwat:shashwat123@test.1psy3pb.mongodb.net/",
                "mongodb+srv://shashwat:shashwat123@test.1psy3pb.mongodb.net/?retryWrites=true&w=majority&ssl=true&ssl_cert_reqs=CERT_NONE",
                "mongodb+srv://shashwat:shashwat123@test.1psy3pb.mongodb.net/?ssl=true&ssl_cert_reqs=CERT_NONE&authSource=admin"
            ]
            
            for conn_str in connection_strings:
                try:
                    self.client = pymongo.MongoClient(
                        conn_str,
                        serverSelectionTimeoutMS=5000,  # 5 second timeout
                        connectTimeoutMS=5000,
                        socketTimeoutMS=5000
                    )
                    # Test the connection
                    self.client.admin.command('ping')
                    self.db = self.client[db_name]
                    self.collection = self.db[collection_name]
                    self.connected = True
                    print(f"Successfully connected to MongoDB with connection string: {conn_str}")
                    break
                except Exception as e:
                    print(f"Failed to connect with {conn_str}: {str(e)}")
                    continue
                    
            if not self.connected:
                print("Warning: Could not connect to MongoDB. Attendance features will be disabled.")
                
        except Exception as e:
            print(f"MongoDB connection failed: {str(e)}")
            self.connected = False

    def load_known_people(self):
        """Load all known people from the known_faces directory"""
        try:
            known_faces_dir = 'data/known_faces'
            if os.path.exists(known_faces_dir):
                for filename in os.listdir(known_faces_dir):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        # Extract person name from filename (remove extension)
                        person_name = os.path.splitext(filename)[0]
                        self.all_known_people.add(person_name)
                print(f"Loaded {len(self.all_known_people)} known people: {list(self.all_known_people)}")
            else:
                print(f"Known faces directory not found: {known_faces_dir}")
        except Exception as e:
            print(f"Error loading known people: {str(e)}")

    def test_connection(self):
        """Test MongoDB connection and show database stats"""
        if not self.connected:
            print("MongoDB not connected!")
            return False
        
        try:
            # Test connection
            self.client.admin.command('ping')
            print("MongoDB connection is active!")
            
            # Show database info
            total_records = self.collection.count_documents({})
            print(f"Total records in collection: {total_records}")
            
            # Show all unique dates
            unique_dates = self.collection.distinct('date')
            print(f"Dates with data: {sorted(unique_dates)}")
            
            # Show sample records
            sample_records = list(self.collection.find({}).limit(5))
            print("Sample records:")
            for i, record in enumerate(sample_records):
                print(f"  {i+1}: {record}")
                
            return True
        except Exception as e:
            print(f"MongoDB connection test failed: {str(e)}")
            return False

    def refresh_daily_attendance(self):
        """Reset daily attendance tracking"""
        self.people_inside.clear()
        self.current_date = date.today()  # Update current date
        print(f"Daily attendance tracking refreshed for {self.current_date}")

    def get_today_start(self):
        """Get the start of today (midnight)"""
        today = date.today()
        return datetime.combine(today, datetime.min.time())

    def get_people_with_attendance_today(self):
        """Get list of people who have marked attendance today"""
        if not self.connected:
            return list(self.people_inside.keys())
        
        try:
            today_date = date.today().isoformat()
            people_today = self.collection.distinct('name', {
                'date': today_date,
                'status': 'present'
            })
            # Also include people in local tracking
            all_present = set(people_today)
            all_present.update(self.people_inside.keys())
            return list(all_present)
        except Exception as e:
            print(f"Error getting today's attendance: {str(e)}")
            return list(self.people_inside.keys())

    def mark_attendance(self, person_name):
        """Marks attendance for a person as present."""
        if not self.connected:
            print(f"MongoDB not connected. Marking local attendance for {person_name}")
            self.people_inside[person_name] = time.time()
            return False
            
        try:
            # Check if already marked today using date-specific query
            today_date = date.today().isoformat()
            existing_record = self.collection.find_one({
                'name': person_name,
                'date': today_date,
                'status': 'present'
            })
            
            if existing_record:
                print(f"{person_name} already marked present today")
                self.people_inside[person_name] = time.time()
                return True
            
            timestamp = datetime.now()
            # Store both timestamp and date for better querying
            self.collection.insert_one({
                'name': person_name,
                'timestamp': timestamp,
                'date': today_date,  # Store date as string for easier querying
                'status': 'present'
            })
            
            # Update local tracking
            self.people_inside[person_name] = time.time()
            print(f"Marked {person_name} as present for {today_date}")
            return True
        except Exception as e:
            print(f"Error marking attendance for {person_name}: {str(e)}")
            # Fallback to local tracking
            self.people_inside[person_name] = time.time()
            return False

    def check_daily_refresh(self):
        """Check if it's a new day and automatically refresh if needed"""
        today = date.today()
        if today != self.current_date:
            print(f"New day detected ({today}), refreshing daily attendance")
            self.refresh_daily_attendance()
            self.current_date = today
            return True
        return False

    def update_person_presence(self, person_name):
        """Update the last seen time for a person (call this when they're detected)"""
        # Check for daily refresh first
        self.check_daily_refresh()
        self.people_inside[person_name] = time.time()

    def get_people_outside(self):
        """Returns a list of people who haven't marked attendance today."""
        if not self.connected:
            # If not connected to DB, use local tracking
            outside_people = []
            for person in self.all_known_people:
                if person not in self.people_inside:
                    outside_people.append(person)
            return outside_people
            
        try:
            # Get people who have marked attendance today
            people_with_attendance = self.get_people_with_attendance_today()
            
            # Return all known people who haven't marked attendance today
            outside_people = []
            for person in self.all_known_people:
                if person not in people_with_attendance:
                    outside_people.append(person)
                    
            return outside_people
        except Exception as e:
            print(f"Error getting people outside: {str(e)}")
            # Fallback to local tracking
            outside_people = []
            for person in self.all_known_people:
                if person not in self.people_inside:
                    outside_people.append(person)
            return outside_people

    def get_people_inside(self):
        """Returns a list of people who have marked attendance today."""
        return self.get_people_with_attendance_today()
    
    def get_absent_people(self):
        """Returns a list of people who haven't marked attendance today (alias for get_people_outside)."""
        return self.get_people_outside()

    def get_attendance_for_date(self, target_date):
        """Get attendance records for a specific date"""
        if not self.connected:
            print(f"MongoDB not connected! Cannot fetch data for {target_date}")
            if target_date == date.today():
                return list(self.people_inside.keys())
            return []
        
        try:
            date_str = target_date.isoformat() if isinstance(target_date, date) else target_date
            print(f"Searching MongoDB for date: '{date_str}' with status: 'present' or 'entry'")
            
            # Debug: Check what's actually in the database
            all_records = list(self.collection.find({}, {'_id': 0}))
            print(f"Total records in database: {len(all_records)}")
            if all_records:
                print("Sample records:")
                for i, record in enumerate(all_records[:5]):  # Show first 5 records
                    print(f"  Record {i+1}: {record}")
            
            # Try the new format first (with date field)
            attendance_data = list(self.collection.find({
                'date': date_str,
                'status': {'$in': ['present', 'entry']}  # Accept both statuses
            }, {'_id': 0}))
            
            # If no records found with date field, try the old format (timestamp-based)
            if not attendance_data:
                print(f"No records found with date field, trying timestamp-based search...")
                
                # For timestamp-based search, create start and end of day
                from datetime import datetime, time
                target_datetime = datetime.strptime(date_str, '%Y-%m-%d').date()
                start_of_day = datetime.combine(target_datetime, time.min)
                end_of_day = datetime.combine(target_datetime, time.max)
                
                attendance_data = list(self.collection.find({
                    'timestamp': {
                        '$gte': start_of_day,
                        '$lte': end_of_day
                    },
                    'status': {'$in': ['present', 'entry']}  # Accept both statuses
                }, {'_id': 0}))
                
                print(f"Found {len(attendance_data)} records using timestamp search")
            
            print(f"Found {len(attendance_data)} attendance records for {date_str}")
            if attendance_data:
                print("Records found:")
                for record in attendance_data:
                    print(f"  - {record}")
            
            return attendance_data
        except Exception as e:
            print(f"Error getting attendance for {target_date}: {str(e)}")
            return []

    def get_date_range_attendance(self, start_date, end_date):
        """Get attendance records for a date range"""
        if not self.connected:
            return []
        
        try:
            start_str = start_date.isoformat() if isinstance(start_date, date) else start_date
            end_str = end_date.isoformat() if isinstance(end_date, date) else end_date
            
            attendance_data = list(self.collection.find({
                'date': {'$gte': start_str, '$lte': end_str},
                'status': 'present'
            }, {'_id': 0}).sort('date', 1))
            return attendance_data
        except Exception as e:
            print(f"Error getting attendance for date range: {str(e)}")
            return []

    def generate_attendance_pdf(self, file_path='attendance_report.pdf', target_date=None):
        """Generates a PDF report of the attendance for a specific date or today."""
        if not self.connected:
            print("MongoDB not connected. Cannot generate PDF report.")
            return False
        
        try:
            if target_date is None:
                target_date = date.today()
            
            print(f"Generating PDF for date: {target_date}")
            
            # Get attendance data for the specific date
            attendance_data = self.get_attendance_for_date(target_date)
            
            print(f"PDF generation: Found {len(attendance_data)} records")
            
            if not attendance_data:
                print(f"No attendance data found for {target_date} or unable to generate PDF")
                return False

            doc = SimpleDocTemplate(file_path, pagesize=letter)
            elements = []

            # Add title with date
            title_data = [['Attendance Report', f'Date: {target_date}']]
            title_table = Table(title_data)
            title_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 14),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ])
            title_table.setStyle(title_style)
            elements.append(title_table)

            # Add some space
            from reportlab.platypus import Spacer
            elements.append(Spacer(1, 20))

            # Create attendance table
            data = [['Name', 'Time', 'Status']]
            for record in attendance_data:
                # Handle timestamp field (could be datetime object or string)
                if 'timestamp' in record:
                    timestamp = record['timestamp']
                    if hasattr(timestamp, 'strftime'):  # datetime object
                        timestamp_str = timestamp.strftime("%H:%M:%S")
                    else:  # string or other format
                        timestamp_str = str(timestamp)
                else:
                    timestamp_str = "N/A"
                
                # Normalize status (convert "entry" to "Present" for display)
                status = record.get('status', 'Unknown')
                if status in ['entry', 'present']:
                    display_status = 'Present'
                else:
                    display_status = status.title()
                
                data.append([
                    record.get('name', 'Unknown'),
                    timestamp_str,
                    display_status
                ])

            table = Table(data)
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ])
            table.setStyle(style)

            elements.append(table)
            doc.build(elements)
            
            print(f"PDF report generated: {file_path}")
            return True
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            return False
