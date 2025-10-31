"""
Camera Configuration Helper
This script helps optimize camera settings and provides troubleshooting information.
"""

import cv2
import yaml
from pathlib import Path

def optimize_camera_config():
    """Optimize camera configuration based on actual camera capabilities"""
    
    config_path = "config/camera_config.yaml"
    
    # Load current config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("Camera Configuration Optimizer")
    print("=" * 50)
    
    optimized_cameras = []
    
    for camera in config['cameras']:
        cam_id = camera['id']
        print(f"\nOptimizing Camera {cam_id}: {camera['name']}")
        
        if not camera['enabled']:
            print("  Status: DISABLED - Skipping")
            optimized_cameras.append(camera)
            continue
            
        try:
            source = int(camera['source']) if str(camera['source']).isdigit() else camera['source']
            cap = cv2.VideoCapture(source)
            
            # Set timeout for IP cameras
            if isinstance(source, str) and source.startswith('rtsp://'):
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_TIMEOUT, 5000)  # 5 second timeout
            
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    actual_height, actual_width = frame.shape[:2]
                    print(f"  Actual resolution: {actual_width}x{actual_height}")
                    
                    # Update camera config with actual resolution
                    camera['resolution']['width'] = actual_width
                    camera['resolution']['height'] = actual_height
                    
                    # Optimize FPS for IP cameras
                    if isinstance(source, str) and source.startswith('rtsp://'):
                        camera['fps'] = 5  # Lower FPS for IP cameras
                        print(f"  Optimized FPS: {camera['fps']}")
                    
                    print("  Status: ✓ OPTIMIZED")
                else:
                    print("  Status: ✗ Cannot read frame")
                    camera['enabled'] = False
            else:
                print("  Status: ✗ Cannot connect")
                camera['enabled'] = False
                
            cap.release()
            
        except Exception as e:
            print(f"  Status: ✗ Error - {e}")
            camera['enabled'] = False
            
        optimized_cameras.append(camera)
    
    # Save optimized config
    optimized_config = {'cameras': optimized_cameras}
    
    backup_path = "config/camera_config_original.yaml"
    with open(backup_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    print(f"\nOriginal config backed up to: {backup_path}")
    
    with open(config_path, 'w') as f:
        yaml.dump(optimized_config, f, default_flow_style=False)
    print(f"Optimized config saved to: {config_path}")
    
    print("\nOptimization complete!")
    print("Enabled cameras:", sum(1 for cam in optimized_cameras if cam['enabled']))

if __name__ == "__main__":
    optimize_camera_config()
