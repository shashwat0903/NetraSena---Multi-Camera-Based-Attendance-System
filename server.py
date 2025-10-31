"""
Server Application for Multi-Camera Face Tracking & Attendance System
Runs on the server laptop, handles all camera processing and face recognition
"""

from flask import Flask, render_template, jsonify, request, send_file, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2
import base64
import threading
import time
import os
from datetime import datetime, date
from core.camera_manager import CameraManager
from core.face_detection import FaceDetector
from core.face_tracker import FaceTracker
from core.attendance_manager import AttendanceManager
from core.alert_system import AlertSystem
import yaml
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
CORS(app)  # Enable CORS for all routes
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global variables
camera_manager = None
face_detector = None
face_tracker = None
attendance_manager = None
alert_system = None
processing_active = False
attendance_mode = False
camera_threads = {}
frame_buffers = {}

def initialize_system():
    """Initialize all system components"""
    global camera_manager, face_detector, face_tracker, attendance_manager, alert_system
    
    try:
        logger.info("Initializing system components...")
        
        # Load configuration
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize camera manager
        camera_manager = CameraManager('config/camera_config.yaml')
        logger.info(f"Initialized {len(camera_manager.cameras)} cameras")
        
        # Initialize face detector
        try:
            face_detector = FaceDetector(config)
            face_detector.load_known_faces('data/known_faces')
            logger.info(f"Face detector initialized with {len(face_detector.known_faces)} known faces")
        except Exception as e:
            logger.error(f"Failed to initialize face detector: {str(e)}")
            logger.info("Tip: Make sure insightface models are downloaded in ./models directory")
            raise
        
        # Initialize face tracker
        face_tracker = FaceTracker()
        logger.info("Face tracker initialized")
        
        # Initialize attendance manager
        attendance_manager = AttendanceManager()
        logger.info("Attendance manager initialized")
        
        # Initialize alert system
        alert_system = AlertSystem(config)
        logger.info("Alert system initialized")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing system: {str(e)}")
        return False

def process_camera_feed(camera_id):
    """Process individual camera feed and stream to clients"""
    global processing_active, attendance_mode
    
    logger.info(f"Starting camera processing for camera {camera_id}")
    
    while processing_active:
        try:
            if camera_id not in camera_manager.cameras:
                break
            
            # Get camera config
            camera_config = camera_manager.cameras[camera_id]
            
            # Get frame from camera manager's queue
            frame = camera_manager.get_frame(camera_id)
            
            if frame is None:
                time.sleep(0.03)
                continue
            
            # Process frame for face detection
            processed_frame = frame.copy()
            
            # Detect faces first
            detected_faces = face_detector.detect_faces(frame)
            
            # Then recognize/match them against known faces
            results = face_detector.recognize_faces(detected_faces)
            
            detected_names = []
            
            for face, known_face, confidence in results:
                if known_face:
                    name = known_face.name
                    detected_names.append(name)
                    
                    # Mark attendance if mode is enabled
                    if attendance_mode:
                        attendance_manager.mark_attendance(name)
                    
                    # Draw on frame
                    x1, y1, x2, y2 = face.bbox.astype(int)
                    color = (0, 255, 0)  # Green for known faces
                    cv2.rectangle(processed_frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Add name and confidence
                    label = f"{name} ({confidence:.2f})"
                    cv2.putText(processed_frame, label, (x1, y1-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                else:
                    # Unknown face
                    x1, y1, x2, y2 = face.bbox.astype(int)
                    color = (0, 0, 255)  # Red for unknown
                    cv2.rectangle(processed_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(processed_frame, "Unknown", (x1, y1-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Store in buffer
            frame_buffers[camera_id] = {
                'frame': frame_base64,
                'detected': detected_names,
                'timestamp': time.time()
            }
            
            # Emit to all connected clients
            socketio.emit('frame_update', {
                'camera_id': camera_id,
                'camera_name': camera_config.name,
                'frame': frame_base64,
                'detected': detected_names
            })
            
            time.sleep(0.03)  # ~30 FPS
            
        except Exception as e:
            logger.error(f"Error processing camera {camera_id}: {str(e)}")
            time.sleep(1)
    
    logger.info(f"Stopped camera processing for camera {camera_id}")

# REST API Endpoints

@app.route('/')
def index():
    """Serve the main client interface"""
    return render_template('client.html')

@app.route('/favicon.ico')
def favicon():
    """Return empty response for favicon to avoid 404 errors"""
    return '', 204

@app.route('/api/system/status')
def get_system_status():
    """Get current system status"""
    return jsonify({
        'active': processing_active,
        'attendance_mode': attendance_mode,
        'cameras': len(camera_manager.cameras) if camera_manager else 0,
        'connected': attendance_manager.connected if attendance_manager else False
    })

@app.route('/api/cameras/list')
def list_cameras():
    """List all available cameras"""
    try:
        if not camera_manager:
            return jsonify({'error': 'System not initialized'}), 500
        
        cameras = []
        for cam_id, cam_config in camera_manager.cameras.items():
            cameras.append({
                'id': cam_id,
                'name': cam_config.name,
                'enabled': cam_config.enabled
            })
        
        return jsonify({'cameras': cameras})
    except Exception as e:
        logger.error(f"Error in list_cameras: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/processing/start', methods=['POST'])
def start_processing():
    """Start camera processing"""
    global processing_active, camera_threads
    
    if processing_active:
        return jsonify({'message': 'Processing already active'})
    
    processing_active = True
    
    # Start cameras if not already started
    for camera_id in camera_manager.cameras.keys():
        # Check if camera thread is already running
        if camera_id not in camera_manager.capture_threads:
            camera_manager.start_camera(camera_id)
            logger.info(f"Started camera {camera_id}")
    
    # Give cameras a moment to start
    time.sleep(0.5)
    
    # Start processing thread for each camera
    for camera_id in camera_manager.cameras.keys():
        thread = threading.Thread(target=process_camera_feed, args=(camera_id,), daemon=True)
        thread.start()
        camera_threads[camera_id] = thread
    
    return jsonify({'message': 'Processing started', 'cameras': len(camera_threads)})

@app.route('/api/processing/stop', methods=['POST'])
def stop_processing():
    """Stop camera processing"""
    global processing_active, camera_threads
    
    processing_active = False
    
    # Wait for threads to finish
    for thread in camera_threads.values():
        thread.join(timeout=2)
    
    camera_threads.clear()
    frame_buffers.clear()
    
    return jsonify({'message': 'Processing stopped'})

@app.route('/api/attendance/mode', methods=['POST'])
def toggle_attendance_mode():
    """Toggle attendance mode on/off"""
    global attendance_mode
    
    data = request.json
    attendance_mode = data.get('enabled', False)
    
    return jsonify({
        'message': f"Attendance mode {'enabled' if attendance_mode else 'disabled'}",
        'enabled': attendance_mode
    })

@app.route('/api/attendance/present')
def get_present_list():
    """Get list of people currently present"""
    if not attendance_manager:
        return jsonify({'error': 'Attendance manager not initialized'}), 500
    
    present = list(attendance_manager.people_inside.keys())
    return jsonify({'present': present, 'count': len(present)})

@app.route('/api/attendance/absent')
def get_absent_list():
    """Get list of people currently absent"""
    if not attendance_manager:
        return jsonify({'error': 'Attendance manager not initialized'}), 500
    
    absent = attendance_manager.get_absent_people()
    return jsonify({'absent': absent, 'count': len(absent)})

@app.route('/api/attendance/refresh', methods=['POST'])
def refresh_attendance():
    """Refresh daily attendance"""
    if not attendance_manager:
        return jsonify({'error': 'Attendance manager not initialized'}), 500
    
    attendance_manager.refresh_daily_attendance()
    return jsonify({'message': 'Attendance refreshed'})

@app.route('/api/attendance/pdf', methods=['POST'])
def generate_pdf():
    """Generate attendance PDF for a specific date"""
    if not attendance_manager:
        return jsonify({'error': 'Attendance manager not initialized'}), 500
    
    data = request.json
    date_str = data.get('date', date.today().isoformat())
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        filename = f'attendance_{date_str}.pdf'
        filepath = os.path.join('data', filename)
        
        success = attendance_manager.generate_attendance_pdf(filepath, target_date)
        
        if success:
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': f'No attendance data found for {date_str}'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/faces/known')
def get_known_faces():
    """Get list of all known faces"""
    if not face_detector:
        return jsonify({'error': 'Face detector not initialized'}), 500
    
    known_faces = [kf.name for kf in face_detector.known_faces]
    return jsonify({'faces': known_faces, 'count': len(known_faces)})

@app.route('/api/faces/add', methods=['POST'])
def add_known_face():
    """Add a new known face"""
    if not face_detector:
        return jsonify({'error': 'Face detector not initialized'}), 500
    
    # Get uploaded image and name
    if 'image' not in request.files or 'name' not in request.form:
        return jsonify({'error': 'Image and name required'}), 400
    
    image = request.files['image']
    name = request.form['name']
    
    # Save image to known_faces directory
    known_faces_dir = 'data/known_faces'
    os.makedirs(known_faces_dir, exist_ok=True)
    
    filepath = os.path.join(known_faces_dir, f"{name}.jpg")
    image.save(filepath)
    
    # Reload face detector
    face_detector.load_known_faces(known_faces_dir)
    
    return jsonify({'message': f'Added face for {name}', 'total_faces': len(face_detector.known_faces)})

@app.route('/api/database/test')
def test_database():
    """Test database connection and return stats"""
    if not attendance_manager:
        return jsonify({'error': 'Attendance manager not initialized'}), 500
    
    if not attendance_manager.connected:
        return jsonify({'error': 'Database not connected'}), 500
    
    try:
        total_records = attendance_manager.collection.count_documents({})
        unique_dates = attendance_manager.collection.distinct('date')
        
        # Get sample records
        sample_records = list(attendance_manager.collection.find({}).limit(5))
        # Remove _id for JSON serialization
        for record in sample_records:
            record.pop('_id', None)
        
        return jsonify({
            'connected': True,
            'total_records': total_records,
            'unique_dates': sorted(unique_dates),
            'sample_records': sample_records
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket Events

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connection_response', {'status': 'connected', 'message': 'Welcome to the attendance system'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_attendance_update')
def handle_attendance_request():
    """Send current attendance data to client"""
    if attendance_manager:
        present = list(attendance_manager.people_inside.keys())
        absent = attendance_manager.get_absent_people()
        
        emit('attendance_update', {
            'present': present,
            'absent': absent,
            'timestamp': datetime.now().isoformat()
        })

def broadcast_attendance_updates():
    """Periodically broadcast attendance updates to all clients"""
    while processing_active:
        if attendance_manager:
            present = list(attendance_manager.people_inside.keys())
            absent = attendance_manager.get_absent_people()
            
            socketio.emit('attendance_update', {
                'present': present,
                'absent': absent,
                'timestamp': datetime.now().isoformat()
            })
        
        time.sleep(2)  # Update every 2 seconds

def main():
    """Main function to start the server"""
    print("=" * 60)
    print("Multi-Camera Face Tracking & Attendance System - SERVER")
    print("=" * 60)
    
    # Initialize system
    if not initialize_system():
        print("Failed to initialize system. Exiting...")
        return
    
    print("\nSystem initialized successfully!")
    print(f"Cameras available: {len(camera_manager.cameras)}")
    print(f"Known people: {len(attendance_manager.all_known_people)}")
    print(f"MongoDB connected: {attendance_manager.connected}")
    
    # Start attendance update broadcaster
    broadcaster = threading.Thread(target=broadcast_attendance_updates, daemon=True)
    broadcaster.start()
    
    # Get server configuration
    host = os.environ.get('SERVER_HOST', '0.0.0.0')  # Listen on all interfaces
    port = int(os.environ.get('SERVER_PORT', 5000))
    
    print(f"\nStarting server on {host}:{port}")
    print(f"Clients can connect to: http://<server-ip>:{port}")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Start the server
    try:
        socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        processing_active = False
        camera_manager.stop_all()

if __name__ == '__main__':
    main()
