# Quick Start Guide - Client-Server Architecture

## 🚀 Quick Start (5 minutes)

### Step 1: Install Dependencies (Server Laptop Only)

```bash
cd multi-cam-face-tracker-main
pip install Flask Flask-SocketIO Flask-CORS python-socketio eventlet
```

### Step 2: Start the Server

**Windows:**
```bash
start_server.bat
```

**Or manually:**
```bash
python server.py
```

You'll see output like:
```
========================================
Multi-Camera Face Tracking & Attendance System - SERVER
========================================

System initialized successfully!
Cameras available: 2
Known faces: 5
MongoDB connected: True

Starting server on 0.0.0.0:5000
Clients can connect to: http://<server-ip>:5000
========================================
```

### Step 3: Find Your Server IP Address

**Windows PowerShell:**
```powershell
ipconfig | findstr IPv4
```

Example output: `192.168.1.100`

### Step 4: Connect from Clients

**On the same laptop:**
- Open browser → `http://localhost:5000`

**From other devices (phones, tablets, laptops):**
- Open browser → `http://192.168.1.100:5000`
  (Replace with your actual server IP)

## 🎯 What You Can Do

### From Any Client Device:

1. **Start/Stop System** - Control camera processing
2. **Enable Attendance Mode** - Begin recording attendance
3. **View Live Cameras** - See real-time video feeds with face detection
4. **Monitor Attendance** - See who's present/absent in real-time
5. **Generate Reports** - Create PDF for any date
6. **Refresh Daily** - Reset attendance for new day

## 📱 Supported Devices

✅ **Server Laptop** - Runs all processing
✅ **Windows/Mac/Linux Clients** - Via web browser
✅ **Android Tablets/Phones** - Via Chrome browser
✅ **iOS iPads/iPhones** - Via Safari browser

## 🔧 Troubleshooting

### Can't Connect to Server?

1. **Check server is running** - Look for "Starting server" message
2. **Check IP address** - Run `ipconfig` on server
3. **Check firewall** - Allow port 5000
   ```powershell
   New-NetFirewallRule -DisplayName "Attendance Server" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
   ```
4. **Same network** - Both devices must be on same WiFi/LAN

### No Camera Feed?

1. Click "Start System" button on client
2. Check cameras are connected to server laptop
3. Verify `camera_config.yaml` has cameras enabled

### Slow Performance?

1. Reduce number of cameras in config
2. Close other applications on server
3. Use wired ethernet instead of WiFi for server

## 🏗️ Architecture Overview

```
┌─────────────────────────┐
│   SERVER LAPTOP         │
│   - Cameras             │◄──── Only this laptop needs cameras
│   - Face Recognition    │
│   - MongoDB Database    │
│   - Flask Server        │
└────────┬────────────────┘
         │
         │ WiFi/LAN
         │
    ┌────┴──────┬──────────────┬─────────┐
    │           │              │         │
┌───▼───┐  ┌───▼───┐    ┌─────▼────┐  ┌▼────┐
│Client1│  │Client2│    │ Client3  │  │ ... │
│Browser│  │Browser│    │ Browser  │  └─────┘
└───────┘  └───────┘    └──────────┘
   PC       Laptop       Tablet/Phone
```

## 💡 Key Features

### Real-time Updates
- Camera feeds stream at ~30 FPS
- Attendance updates every 2 seconds
- Instant face detection and recognition

### Multi-User Support
- Multiple clients can connect simultaneously
- All clients see the same data
- Changes sync across all connected devices

### Network Flexibility
- Works on local network (LAN/WiFi)
- No internet required
- Secure local communication

## 📝 Example Workflow

1. **Teacher/Admin** starts server on main laptop
2. **Security Guard** opens browser on tablet → monitors camera feeds
3. **Principal** opens browser on office PC → views attendance reports
4. **Student** marked present when detected by any camera (if attendance mode enabled)
5. **Admin** generates PDF report at end of day

## 🎓 Next Steps

1. Read full documentation: `CLIENT_SERVER_GUIDE.md`
2. Configure cameras: Edit `config/camera_config.yaml`
3. Add known faces: Place photos in `data/known_faces/`
4. Test system: Use "Test Database" button on client

## 🆘 Need Help?

Check the logs on server:
- Console output (terminal window)
- `logs/app.log`
- `logs/error.log`

Common issues and solutions in `CLIENT_SERVER_GUIDE.md`
