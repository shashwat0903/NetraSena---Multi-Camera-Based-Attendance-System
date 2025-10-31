#!/usr/bin/env python3
"""
Quick test for improved face detection
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

def load_config():
    """Load configuration from YAML file"""
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def quick_test():
    """Quick test of face detection improvements"""
    logger.info("Testing improved face detection")
    
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
    
    # Test Camera 2 (which showed faces in previous test)
    cam_id = 2
    logger.info(f"Testing Camera {cam_id}")
    
    for i in range(3):
        frame = camera_manager.get_frame(cam_id)
        if frame is None:
            logger.warning(f"No frame from camera {cam_id}")
            continue
            
        logger.info(f"Frame {i+1}: shape={frame.shape}")
        
        # Test detection
        faces = face_detector.detect_faces(frame)
        logger.info(f"Detected {len(faces)} faces")
        
        if faces:
            for j, face in enumerate(faces):
                logger.info(f"Face {j+1}: bbox={face.bbox}, confidence={face.det_score}")
                
            # Test recognition
            recognized = face_detector.recognize_faces_with_suspects(faces)
            for j, (face, known_face, confidence, is_suspect) in enumerate(recognized):
                name = known_face.name if known_face else "Unknown"
                logger.info(f"Recognition {j+1}: {name} (confidence={confidence:.3f})")
        
        time.sleep(1)
    
    # Stop cameras
    camera_manager.stop_all_cameras()
    logger.info("Test completed")
    return True

if __name__ == "__main__":
    logger.add("logs/quick_test.log", rotation="1 MB")
    quick_test()
