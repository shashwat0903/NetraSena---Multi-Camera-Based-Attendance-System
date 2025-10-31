#!/usr/bin/env python3
"""
Camera detection and testing script
"""

import cv2
import sys

def test_camera(index):
    """Test if a camera at given index is available"""
    try:
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            return ret and frame is not None
        return False
    except:
        return False

def find_available_cameras():
    """Find all available camera indices"""
    print("Scanning for available cameras...")
    available_cameras = []
    
    # Test camera indices 0-5
    for i in range(6):
        if test_camera(i):
            available_cameras.append(i)
            print(f"✓ Camera {i} is available")
        else:
            print(f"✗ Camera {i} is not available")
    
    return available_cameras

def test_camera_detailed(index):
    """Test camera with detailed information"""
    print(f"\nTesting Camera {index} in detail...")
    
    try:
        cap = cv2.VideoCapture(index)
        
        if not cap.isOpened():
            print(f"✗ Cannot open camera {index}")
            return False
        
        # Get camera properties
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"Camera properties: {width}x{height} @ {fps} FPS")
        
        # Try to read a frame
        ret, frame = cap.read()
        if ret:
            print(f"✓ Successfully read frame: {frame.shape}")
            success = True
        else:
            print("✗ Failed to read frame")
            success = False
        
        cap.release()
        return success
        
    except Exception as e:
        print(f"✗ Error testing camera {index}: {e}")
        return False

if __name__ == "__main__":
    print("Camera Detection and Testing")
    print("=" * 40)
    
    # Find available cameras
    available = find_available_cameras()
    
    if not available:
        print("\n⚠ No cameras found!")
        print("Possible solutions:")
        print("1. Check if camera is connected and not used by another app")
        print("2. Update camera drivers")
        print("3. Check camera permissions")
        print("4. Try running as administrator")
        sys.exit(1)
    
    print(f"\nFound {len(available)} available camera(s): {available}")
    
    # Test each available camera in detail
    for cam_id in available:
        test_camera_detailed(cam_id)
    
    print("\n" + "=" * 40)
    print("Camera testing completed!")
    
    if available:
        print(f"✓ Update camera_config.yaml to use camera: {available[0]}")
    else:
        print("✗ No working cameras found")
