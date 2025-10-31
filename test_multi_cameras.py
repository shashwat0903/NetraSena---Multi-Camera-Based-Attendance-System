#!/usr/bin/env python3
"""
Test script for multiple camera connections
"""
import cv2
import time
import logging
from pathlib import Path
import sys

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent))

from core.camera_manager import CameraManager

def test_camera_connections():
    """Test all configured cameras"""
    print("Testing Multi-Camera Setup...")
    print("=" * 50)
    
    # Initialize camera manager
    config_path = "config/camera_config.yaml"
    try:
        camera_manager = CameraManager(config_path)
        print(f"✓ Loaded configuration with {len(camera_manager.cameras)} cameras")
    except Exception as e:
        print(f"✗ Failed to load camera configuration: {e}")
        return
    
    # Test each camera individually
    for cam_id, cam_config in camera_manager.cameras.items():
        print(f"\nTesting Camera ID {cam_id}: {cam_config.name}")
        print(f"  Source: {cam_config.source}")
        print(f"  Resolution: {cam_config.width}x{cam_config.height}")
        print(f"  FPS: {cam_config.fps}")
        
        if not cam_config.enabled:
            print("  Status: DISABLED")
            continue
        
        # Test camera connection
        try:
            source = int(cam_config.source) if str(cam_config.source).isdigit() else cam_config.source
            cap = cv2.VideoCapture(source)
            
            if not cap.isOpened():
                print(f"  Status: ✗ FAILED to open camera")
                continue
                
            # Try to read a frame
            ret, frame = cap.read()
            if ret:
                print(f"  Status: ✓ SUCCESS - Frame captured ({frame.shape[1]}x{frame.shape[0]})")
            else:
                print(f"  Status: ✗ FAILED to read frame")
                
            cap.release()
            
        except Exception as e:
            print(f"  Status: ✗ ERROR - {e}")
    
    print("\n" + "=" * 50)
    print("Testing complete!")

def test_multi_camera_preview():
    """Test multiple cameras with preview windows"""
    print("\nStarting multi-camera preview test...")
    print("Press 'q' to quit, 'ESC' to exit")
    
    config_path = "config/camera_config.yaml"
    camera_manager = CameraManager(config_path)
    
    # Start all cameras
    camera_manager.start_all_cameras()
    
    # Give cameras time to initialize
    time.sleep(2)
    
    try:
        while True:
            frames_captured = 0
            
            for cam_id in camera_manager.cameras:
                if camera_manager.cameras[cam_id].enabled:
                    frame = camera_manager.get_frame(cam_id)
                    if frame is not None:
                        # Resize frame for display
                        display_frame = cv2.resize(frame, (640, 480))
                        
                        # Add camera info to frame
                        cv2.putText(display_frame, f"Camera {cam_id}: {camera_manager.cameras[cam_id].name}", 
                                  (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        # Show frame
                        cv2.imshow(f"Camera {cam_id} - {camera_manager.cameras[cam_id].name}", display_frame)
                        frames_captured += 1
            
            if frames_captured == 0:
                print("No frames captured from any camera")
                break
                
            # Check for quit key
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # 'q' or ESC
                break
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        camera_manager.stop_all_cameras()
        cv2.destroyAllWindows()
        print("All cameras stopped and windows closed")

if __name__ == "__main__":
    # Test camera connections first
    test_camera_connections()
    
    # Ask user if they want to test preview
    response = input("\nWould you like to test camera preview? (y/n): ").lower()
    if response == 'y':
        test_multi_camera_preview()
