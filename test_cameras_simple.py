#!/usr/bin/env python3
"""
Simple camera test without timeout property
"""
import cv2
import time

def test_cameras():
    """Test all cameras without using unsupported properties"""
    
    cameras = [
        {"id": 0, "name": "Laptop Camera", "source": 0},
        {"id": 1, "name": "CP Plus Camera 1", "source": "rtsp://admin:qwerty12@@192.168.5.138:554/cam/realmonitor?channel=1&subtype=1"},
        {"id": 2, "name": "CP Plus Camera 2", "source": "rtsp://admin:qwerty12@@192.168.5.136:554/cam/realmonitor?channel=1&subtype=1"},
        {"id": 3, "name": "CP Plus Camera 3", "source": "rtsp://admin:qwerty12@@192.168.5.137:554/cam/realmonitor?channel=1&subtype=1"}
    ]
    
    print("Testing cameras without timeout property...")
    print("=" * 60)
    
    for camera in cameras:
        print(f"\nTesting {camera['name']} (ID: {camera['id']})")
        print(f"Source: {camera['source']}")
        
        try:
            cap = cv2.VideoCapture(camera['source'])
            
            # Only set buffer size for RTSP cameras
            if isinstance(camera['source'], str) and camera['source'].startswith('rtsp://'):
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if cap.isOpened():
                print("  ✓ Camera opened successfully")
                
                # Try to read a frame with timeout simulation
                start_time = time.time()
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    height, width = frame.shape[:2]
                    read_time = time.time() - start_time
                    print(f"  ✓ Frame read successful: {width}x{height} ({read_time:.2f}s)")
                else:
                    print("  ✗ Could not read frame")
            else:
                print("  ✗ Could not open camera")
                
            cap.release()
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == "__main__":
    test_cameras()
