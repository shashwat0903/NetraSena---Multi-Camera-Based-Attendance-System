#!/usr/bin/env python3
"""
Simple IP Camera Test Script
This script tests if IP cameras are working and can detect faces
"""

import cv2
import numpy as np
import time
import yaml
import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_single_ip_camera():
    """Test a single IP camera manually"""
    print("Testing single IP camera...")
    
    # Test with camera 2 (the one that showed some detection in debug)
    rtsp_url = "rtsp://admin:qwerty12@@192.168.5.113:554/cam/realmonitor?channel=1&subtype=1"
    
    # Open camera
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        print("Failed to open camera")
        return False
    
    # Set properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 5)
    
    # Test face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    frame_count = 0
    detection_count = 0
    
    for i in range(10):  # Test 10 frames
        ret, frame = cap.read()
        if not ret:
            print(f"Failed to read frame {i}")
            continue
        
        frame_count += 1
        print(f"Frame {i}: shape={frame.shape}")
        
        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces using OpenCV's cascade (simpler test)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0:
            detection_count += 1
            print(f"  Found {len(faces)} faces using OpenCV cascade")
            
            # Draw rectangles around faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        else:
            print(f"  No faces detected")
        
        # Save test frame
        output_dir = Path("data/test_frames")
        output_dir.mkdir(exist_ok=True)
        frame_path = output_dir / f"test_frame_{i}.jpg"
        cv2.imwrite(str(frame_path), frame)
        
        time.sleep(0.5)  # Small delay
    
    cap.release()
    print(f"Test completed: {detection_count}/{frame_count} frames had faces")
    return detection_count > 0

def test_insightface_on_ip_camera():
    """Test insightface on IP camera"""
    print("Testing insightface on IP camera...")
    
    try:
        from core.face_detection import FaceDetector
        
        # Load configuration
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize face detector
        face_detector = FaceDetector(config)
        
        # Test with camera 2
        rtsp_url = "rtsp://admin:qwerty12@@192.168.5.113:554/cam/realmonitor?channel=1&subtype=1"
        cap = cv2.VideoCapture(rtsp_url)
        
        if not cap.isOpened():
            print("Failed to open camera")
            return False
        
        # Set properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 5)
        
        frame_count = 0
        detection_count = 0
        
        for i in range(5):  # Test 5 frames
            ret, frame = cap.read()
            if not ret:
                print(f"Failed to read frame {i}")
                continue
            
            frame_count += 1
            print(f"Frame {i}: shape={frame.shape}")
            
            # Test both detection methods
            faces_regular = face_detector.detect_faces(frame)
            faces_enhanced = face_detector.detect_faces_enhanced(frame)
            
            print(f"  Regular detection: {len(faces_regular)} faces")
            print(f"  Enhanced detection: {len(faces_enhanced)} faces")
            
            if len(faces_regular) > 0 or len(faces_enhanced) > 0:
                detection_count += 1
            
            # Save test frame with detection results
            test_frame = frame.copy()
            
            # Draw regular detection in green
            for face in faces_regular:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                cv2.rectangle(test_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(test_frame, f"Regular: {face.det_score:.2f}", 
                           (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Draw enhanced detection in blue
            for face in faces_enhanced:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                cv2.rectangle(test_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(test_frame, f"Enhanced: {face.det_score:.2f}", 
                           (x1, y1-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            
            # Save frame
            output_dir = Path("data/test_frames")
            output_dir.mkdir(exist_ok=True)
            frame_path = output_dir / f"insightface_test_frame_{i}.jpg"
            cv2.imwrite(str(frame_path), test_frame)
            
            time.sleep(1)
        
        cap.release()
        print(f"InsightFace test completed: {detection_count}/{frame_count} frames had faces")
        return detection_count > 0
        
    except Exception as e:
        print(f"Error in insightface test: {e}")
        return False

if __name__ == "__main__":
    print("Starting IP camera face detection tests...")
    
    # Test 1: Simple OpenCV cascade detection
    print("\n=== Test 1: OpenCV Cascade Detection ===")
    opencv_result = test_single_ip_camera()
    
    # Test 2: InsightFace detection
    print("\n=== Test 2: InsightFace Detection ===")
    insightface_result = test_insightface_on_ip_camera()
    
    print("\n=== Test Results ===")
    print(f"OpenCV Detection: {'PASS' if opencv_result else 'FAIL'}")
    print(f"InsightFace Detection: {'PASS' if insightface_result else 'FAIL'}")
    
    if not opencv_result and not insightface_result:
        print("\nBoth tests failed. Possible issues:")
        print("1. Camera connection problem")
        print("2. No faces in camera view")
        print("3. Poor lighting conditions")
        print("4. Camera resolution/format issues")
    elif opencv_result and not insightface_result:
        print("\nOpenCV works but InsightFace doesn't. Possible InsightFace configuration issue.")
    elif not opencv_result and insightface_result:
        print("\nInsightFace works but OpenCV doesn't. This is unusual.")
    else:
        print("\nBoth tests passed! Face detection should work.")
