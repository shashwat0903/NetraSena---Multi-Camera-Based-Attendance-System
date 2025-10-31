# NetraSena - Enhanced Features Guide

## Overview
This enhanced version of NetraSena includes several new powerful features:

1. **Live Camera Face Capture** - Add faces directly from camera feed
2. **Suspect Management System** - Track and alert on suspect faces
3. **Multi-Camera Dashboard** - View all cameras simultaneously 
4. **Enhanced History with Filtering** - Filter by camera, person, and suspect status
5. **CUDA GPU Acceleration** - Faster face recognition with NVIDIA GPUs

## New Features

### 1. Live Camera Face Capture
- **Location**: Face Manager → Start Live Camera button
- **Usage**: 
  1. Click "Face Manager" in the main window
  2. Click "Start Live Camera" to begin camera feed
  3. Position face in camera view
  4. Click "Capture Face" when face is detected
  5. Enter name and choose to add as "Known Person" or "Suspect"

### 2. Suspect Management System
- **Purpose**: Track individuals who should trigger high-priority alerts
- **Features**:
  - Separate suspects directory (`data/suspects/`)
  - Red bounding boxes for suspects (vs green for known faces)
  - Different alert sound for suspect detection
  - Suspect filtering in history view
  - Telegram notifications marked as "SUSPECT DETECTED!"

#### Adding Suspects:
1. **Via Face Manager**: Use "Suspects" tab to add/manage suspects
2. **Via Image Upload**: Import suspect photos directly
3. **Via Live Capture**: Capture suspect faces from camera feed

### 3. Multi-Camera Dashboard
- **Location**: Main Window → "Multi-Camera View" tab
- **Features**:
  - Individual camera controls (start/stop each camera)
  - Real-time face detection statistics per camera
  - Camera status indicators (green=active, red=stopped)
  - Grid layout showing all cameras simultaneously
  - Individual camera databases and history

### 4. Enhanced History and Filtering
- **Location**: Main Window → "History" tab
- **New Filters**:
  - **Type Filter**: View "All", "Known Only", or "Suspects Only"
  - **Camera Filter**: Filter by specific camera
  - **Date Range**: Custom date filtering
  - **Face Filter**: Filter by specific person

#### History Features:
- Suspect entries marked with `[SUSPECT]` indicator
- Screenshots linked to each detection
- Individual camera statistics
- Export capabilities for security reports

### 5. CUDA GPU Acceleration
- **Setup**: Device is set to "cuda" in `config/config.yaml`
- **Benefits**: 5-10x faster face recognition processing
- **Requirements**: NVIDIA GPU with CUDA support
- **Verification**: Check logs for "CUDA available: True"

## Configuration Files

### Main Configuration (`config/config.yaml`)
```yaml
app:
  suspects_dir: "data/suspects"          # New: Suspects directory
  suspect_alert_sound: "assets/suspect_alert.wav"  # New: Suspect alert sound

recognition:
  device: "cuda"  # GPU acceleration (use "cpu" for CPU-only)
```

### Camera Configuration (`config/camera_config.yaml`)
```yaml
cameras:
  - id: 0
    name: "Front Door"
    source: 0                    # Camera index or RTSP URL
    enabled: true
    resolution:
      width: 1280
      height: 720
    fps: 30
```

## Directory Structure
```
data/
├── known_faces/        # Regular known faces
├── suspects/           # Suspect faces (NEW)
├── screenshots/        # Detection screenshots
└── database.db        # SQLite database with suspect tracking

logs/                   # Application logs
assets/
├── alert.wav          # Regular alert sound
└── suspect_alert.wav  # Suspect alert sound (NEW)
```

## Database Schema Updates
The database now includes suspect tracking:
- `face_logs` table has new `is_suspect` column
- Suspect detections are flagged and filterable
- Individual camera statistics available

## Usage Workflows

### Adding a New Person
1. Go to Face Manager → "Known Faces" tab
2. Either:
   - Import image file, or
   - Start live camera and capture face
3. Enter person's name
4. Click "Add Person"

### Adding a Suspect
1. Go to Face Manager → "Suspects" tab
2. Either:
   - Import suspect image, or  
   - Start live camera and capture suspect face
3. Enter suspect identifier/name
4. Click "Add Suspect"

### Monitoring Multiple Cameras
1. Go to "Multi-Camera View" tab
2. Click "Start All Cameras" or start individual cameras
3. Monitor real-time feeds with face detection overlays
4. View detection statistics per camera

### Reviewing History
1. Go to "History" tab
2. Set filters:
   - Date range for specific time period
   - Camera for specific location
   - Type: "Suspects Only" for security review
3. Click "Refresh" to apply filters
4. Click entries to view screenshots and details

## Alerts and Notifications

### Visual Alerts
- **Known Faces**: Green bounding box with name
- **Suspects**: Red bounding box with "[SUSPECT]" label
- **Unknown Faces**: Blue bounding box labeled "Unknown"

### Audio Alerts
- **Known Faces**: Standard alert sound
- **Suspects**: Distinct suspect alert sound (higher priority)

### Telegram Notifications
- **Known Faces**: "🚨 Face detected!"
- **Suspects**: "🚨 SUSPECT DETECTED!"
- Includes photo, camera location, confidence, and timestamp

## Performance Optimization

### GPU Acceleration (NVIDIA)
- Ensure CUDA-enabled PyTorch is installed
- Set `device: "cuda"` in config
- Monitor GPU usage in Task Manager

### Multi-Camera Performance
- Adjust `max_batch_size` in config for GPU memory
- Lower camera resolution/FPS if needed
- Use hardware-accelerated video codecs when available

## Security Features

### Suspect Tracking
- High-priority alerts for security personnel
- Separate storage and management
- Audit trail in database
- Integration with security protocols

### Privacy Protection
- Local processing (no cloud dependencies)
- Encrypted database storage option
- Configurable data retention policies
- GDPR compliance features

## Troubleshooting

### Camera Issues
- Check camera permissions and drivers
- Verify camera sources in config
- Test individual cameras in Multi-Camera View

### CUDA Issues
- Verify NVIDIA drivers are installed
- Check PyTorch CUDA installation: `python -c "import torch; print(torch.cuda.is_available())"`
- Falls back to CPU if CUDA unavailable

### Performance Issues
- Reduce camera resolution/FPS  
- Lower `max_batch_size` setting
- Enable hardware acceleration
- Monitor system resources

## API and Integration

The system can be extended with:
- REST API for external integration
- Webhook notifications
- MQTT messaging for IoT integration
- Custom alert actions and rules

## Future Enhancements
- Facial recognition accuracy improvements
- Multi-person tracking
- Behavior analysis
- Integration with access control systems
- Mobile app for remote monitoring
