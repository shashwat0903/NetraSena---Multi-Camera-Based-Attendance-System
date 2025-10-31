#!/usr/bin/env python3
"""
IP Camera Face Detection Debug Script
This script tests face detection on IP cameras and logs detailed information
"""

import cv2
import numpy as np
import time
import yaml
from loguru import logger
from pathlib import Path
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.face_detection import FaceDetector
from core.camera_manager import CameraManager
from core.utils import draw_face_info

def load_config():
    """Load configuration from YAML file"""
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def test_ip_camera_face_detection():
    """Test face detection on IP cameras"""
    logger.info("Starting IP camera face detection test")
    
    # Load configuration
    config = load_config()
    if not config:
        return False
    
    # Initialize face detector
    face_detector = FaceDetector(config)
    face_detector.load_known_faces(config['app']['known_faces_dir'])
    
    # Initialize camera manager
    camera_manager = CameraManager('config/camera_config.yaml')
    camera_manager.start_all_cameras()
    
    # Give cameras time to initialize
    time.sleep(3)
    
    # Test each IP camera (cameras 1-4)
    for cam_id in range(1, 5):
        logger.info(f"Testing Camera {cam_id}")
        
        # Check if camera is available
        if cam_id not in camera_manager.cameras:
            logger.error(f"Camera {cam_id} not found")
            continue
            
        camera_config = camera_manager.cameras[cam_id]
        logger.info(f"Camera {cam_id} config: {camera_config.name}, source: {camera_config.source}")
        
        # Test multiple frames
        for frame_num in range(5):
            frame = camera_manager.get_frame(cam_id)
            if frame is None:
                logger.warning(f"No frame from camera {cam_id}")
                continue
                
            logger.info(f"Frame {frame_num+1} from camera {cam_id}: shape={frame.shape}")
            
            # Test both regular and enhanced detection
            faces_regular = face_detector.detect_faces(frame)
            faces_enhanced = face_detector.detect_faces_enhanced(frame)
            
            logger.info(f"Camera {cam_id} Frame {frame_num+1}:")
            logger.info(f"  Regular detection: {len(faces_regular)} faces")
            logger.info(f"  Enhanced detection: {len(faces_enhanced)} faces")
            
            # Log face details
            if faces_regular:
                for i, face in enumerate(faces_regular):
                    logger.info(f"  Regular Face {i+1}: bbox={face.bbox}, confidence={face.det_score}")
            
            if faces_enhanced:
                for i, face in enumerate(faces_enhanced):
                    logger.info(f"  Enhanced Face {i+1}: bbox={face.bbox}, confidence={face.det_score}")
                    
            # Test recognition
            if faces_enhanced:
                recognized = face_detector.recognize_faces_with_suspects(faces_enhanced)
                for i, (face, known_face, confidence, is_suspect) in enumerate(recognized):
                    name = known_face.name if known_face else "Unknown"
                    logger.info(f"  Recognition {i+1}: {name} (confidence={confidence:.3f}, suspect={is_suspect})")
            
            # Save test frame with detection results
            test_frame = frame.copy()
            for i, face in enumerate(faces_enhanced):
                color = (0, 255, 0)  # Green for detected faces
                test_frame = draw_face_info(
                    test_frame, face.bbox,
                    name=f"Face {i+1}",
                    confidence=face.det_score,
                    camera_name=f"Camera {cam_id}",
                    age=face.age,
                    gender=face.gender,
                    timestamp=time.time(),
                    color=color
                )
            
            # Save frame
            output_dir = Path("data/debug_frames")
            output_dir.mkdir(exist_ok=True)
            frame_path = output_dir / f"cam{cam_id}_frame{frame_num+1}_{int(time.time())}.jpg"
            cv2.imwrite(str(frame_path), test_frame)
            logger.info(f"  Saved debug frame: {frame_path}")
            
            time.sleep(1)  # Wait between frames
    
    # Stop cameras
    camera_manager.stop_all_cameras()
    logger.info("IP camera face detection test completed")
    return True

def test_detection_parameters():
    """Test different detection parameters"""
    logger.info("Testing detection parameters")
    
    config = load_config()
    if not config:
        return False
    
    # Test with different thresholds
    test_thresholds = [0.3, 0.5, 0.7, 0.9]
    
    for threshold in test_thresholds:
        logger.info(f"Testing with detection threshold: {threshold}")
        
        # Modify config
        config['recognition']['detection_threshold'] = threshold
        
        # Initialize detector
        face_detector = FaceDetector(config)
        
        # Test with a known good frame
        camera_manager = CameraManager('config/camera_config.yaml')
        camera_manager.start_all_cameras()
        time.sleep(2)
        
        frame = camera_manager.get_frame(1)  # Test with camera 1
        if frame is not None:
            faces = face_detector.detect_faces_enhanced(frame)
            logger.info(f"  Threshold {threshold}: {len(faces)} faces detected")
        
        camera_manager.stop_all_cameras()
        time.sleep(1)

if __name__ == "__main__":
    logger.add("logs/debug_face_detection.log", rotation="1 MB")
    
    logger.info("Starting face detection debug session")
    
    # Test 1: IP camera face detection
    test_ip_camera_face_detection()
    
    # Test 2: Different detection parameters
    test_detection_parameters()
    
    logger.info("Debug session completed")
