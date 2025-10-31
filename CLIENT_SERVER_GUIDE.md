# Client-Server Architecture Guide

## 📋 Overview

The attendance system now runs in a **client-server architecture**:

- **Server**: Runs on one laptop with cameras, handles all face recognition and processing
- **Clients**: Connect from any device (laptop, tablet, phone) via web browser to view and control the system

## 🖥️ Server Setup

### 1. Install Dependencies

First, install all required packages on the **server laptop**:

```bash
pip install -r requirements.txt
```

### 2. Start the Server

**Option A: Using the batch file (Windows)**
```bash
start_server.bat
```

**Option B: Manual start**
```bash
python server.py
```

The server will start on port 5000 by default.

### 3. Find Your Server IP Address

**On Windows:**
```bash
ipconfig
```
Look for "IPv4 Address" (e.g., 192.168.1.100)

**On Linux/Mac:**
```bash
ifconfig
# or
ip addr show
```

## 💻 Client Setup

### Accessing from Any Device

1. **On the same laptop** (server):
   - Open browser: `http://localhost:5000`

2. **From other devices on the same network**:
   - Open browser: `http://[SERVER-IP]:5000`
   - Example: `http://192.168.1.100:5000`

### Supported Browsers
- ✅ Chrome/Edge (Recommended)
- ✅ Firefox
- ✅ Safari
- ⚠️ Internet Explorer (Not recommended)

## 🎮 Using the Client Interface

### Control Panel

1. **Start System**: Begins camera processing and face recognition
2. **Stop System**: Stops all processing
3. **Attendance Mode**: Toggle to enable/disable attendance recording
4. **Refresh Daily**: Reset attendance for a new day
5. **Test Database**: Check MongoDB connection and view data
6. **Generate PDF**: Create attendance report for selected date

### Live Features

- **Camera Feeds**: See live video from all cameras with face detection boxes
- **Present List**: People who have been marked present today
- **Absent List**: Known people not yet marked present
- **Real-time Updates**: Attendance updates automatically every 2 seconds

## 🔧 Configuration

### Environment Variables

Create a `.env` file or set these variables:

```bash
SERVER_HOST=0.0.0.0        # Listen on all network interfaces
SERVER_PORT=5000           # Server port
```

### Firewall Settings

**Windows Firewall:**
1. Open Windows Defender Firewall
2. Click "Advanced settings"
3. Add inbound rule for port 5000
4. Allow TCP connections

**Or use PowerShell (as Administrator):**
```powershell
New-NetFirewallRule -DisplayName "Attendance Server" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

## 🌐 Network Architecture

```
┌─────────────────────────────────────────┐
│         SERVER LAPTOP                    │
│  - Cameras connected                     │
│  - Face recognition processing           │
│  - MongoDB database                      │
│  - Flask server (port 5000)             │
└──────────────┬──────────────────────────┘
               │
               │ Local Network (WiFi/LAN)
               │
    ┌──────────┴──────────┬──────────────┐
    │                     │              │
┌───▼────┐         ┌──────▼───┐    ┌────▼─────┐
│CLIENT 1│         │CLIENT 2  │    │CLIENT 3  │
│Browser │         │Browser   │    │Browser   │
└────────┘         └──────────┘    └──────────┘
```

## 📡 API Endpoints

### System Control
- `GET /api/system/status` - Get system status
- `POST /api/processing/start` - Start processing
- `POST /api/processing/stop` - Stop processing

### Camera Management
- `GET /api/cameras/list` - List all cameras

### Attendance
- `POST /api/attendance/mode` - Toggle attendance mode
- `GET /api/attendance/present` - Get present list
- `GET /api/attendance/absent` - Get absent list
- `POST /api/attendance/refresh` - Refresh daily attendance
- `POST /api/attendance/pdf` - Generate PDF report

### Face Management
- `GET /api/faces/known` - Get known faces list
- `POST /api/faces/add` - Add new face

### Database
- `GET /api/database/test` - Test database connection

## 🔌 WebSocket Events

The system uses WebSocket for real-time communication:

### Server → Client
- `frame_update` - Camera frame with detected faces
- `attendance_update` - Updated attendance lists

### Client → Server
- `request_attendance_update` - Request current attendance data

## 🔒 Security Considerations

### For Production Use:

1. **Change the secret key** in `server.py`:
   ```python
   app.config['SECRET_KEY'] = 'your-secure-random-key-here'
   ```

2. **Enable authentication** (add login system)

3. **Use HTTPS** (add SSL certificates)

4. **Restrict access** (firewall rules, IP whitelist)

5. **Secure MongoDB** (use authentication, not default connection)

## 🐛 Troubleshooting

### Server won't start
- Check if port 5000 is already in use
- Try a different port: `set SERVER_PORT=8080`
- Check firewall settings

### Clients can't connect
- Verify server IP address
- Check firewall allows incoming connections on port 5000
- Ensure both devices are on the same network
- Try disabling VPN

### No video showing
- Check camera permissions
- Verify cameras are connected to server laptop
- Click "Start System" button
- Check browser console for errors (F12)

### Slow performance
- Reduce number of cameras in `camera_config.yaml`
- Lower video quality in `server.py` (JPEG quality setting)
- Ensure good network connection
- Close other applications on server laptop

## 📊 Performance Tips

1. **Network**: Use wired connection for server if possible
2. **Cameras**: Reduce resolution in camera config if needed
3. **Clients**: Limit to 5-10 concurrent clients for best performance
4. **Processing**: Adjust frame processing rate in `server.py` (line with `time.sleep(0.03)`)

## 🔄 Updating the System

1. Stop the server
2. Pull latest changes or update files
3. Install any new dependencies: `pip install -r requirements.txt`
4. Restart the server

## 📝 Logs

Server logs are displayed in the console and saved to:
- `logs/app.log` - Application logs
- `logs/error.log` - Error logs

## 💡 Tips

- Keep the server laptop plugged in and on AC power
- Use a stable network connection
- Monitor CPU/RAM usage on server
- Regularly backup the MongoDB database
- Test with one client first before multiple connections

## 🆘 Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Test database connection with "Test Database" button
3. Verify camera connections with `test_cameras.py`
4. Check network connectivity with `ping [SERVER-IP]`
