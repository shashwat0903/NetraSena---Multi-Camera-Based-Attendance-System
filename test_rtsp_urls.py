#!/usr/bin/env python3
"""
Quick test for CP Plus camera RTSP URLs
"""
import cv2
import time

def test_rtsp_urls():
    """Test the CP Plus camera RTSP URLs"""
    
    # Test URLs for CP Plus cameras
    test_urls = [
        "rtsp://admin:pass12@192.168.5.138:554/cam/realmonitor?channel=1&subtype=0",
        "rtsp://admin:pass12@192.168.5.136:554/cam/realmonitor?channel=1&subtype=0", 
        "rtsp://admin:pass12@192.168.5.137:554/cam/realmonitor?channel=1&subtype=0"
    ]
    
    # Alternative URLs to try if the first ones don't work
    alternative_urls = [
        # For 192.168.5.138
        [
            "rtsp://admin:pass12@192.168.5.138:554/cam/realmonitor?channel=1&subtype=1",
            "rtsp://admin:pass12@192.168.5.138:554/stream1",
            "rtsp://admin:pass12@192.168.5.138:554/live.sdp",
            "rtsp://admin:pass12@192.168.5.138:554/Streaming/Channels/1"
        ],
        # For 192.168.5.136  
        [
            "rtsp://admin:pass12@192.168.5.136:554/cam/realmonitor?channel=1&subtype=1",
            "rtsp://admin:pass12@192.168.5.136:554/stream1",
            "rtsp://admin:pass12@192.168.5.136:554/live.sdp",
            "rtsp://admin:pass12@192.168.5.136:554/Streaming/Channels/1"
        ],
        # For 192.168.5.137
        [
            "rtsp://admin:pass12@192.168.5.137:554/cam/realmonitor?channel=1&subtype=1",
            "rtsp://admin:pass12@192.168.5.137:554/stream1", 
            "rtsp://admin:pass12@192.168.5.137:554/live.sdp",
            "rtsp://admin:pass12@192.168.5.137:554/Streaming/Channels/1"
        ]
    ]
    
    print("Testing CP Plus Camera RTSP URLs...")
    print("=" * 60)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\nTesting Camera {i}: {url}")
        
        try:
            cap = cv2.VideoCapture(url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer size
            cap.set(cv2.CAP_PROP_TIMEOUT, 10000)  # 10 second timeout
            
            if cap.isOpened():
                print("  ✓ Connection successful")
                
                # Try to read a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    height, width = frame.shape[:2]
                    print(f"  ✓ Frame read successful: {width}x{height}")
                else:
                    print("  ✗ Could not read frame")
            else:
                print("  ✗ Could not connect")
                
                # Try alternative URLs
                print(f"  Trying alternative URLs for Camera {i}...")
                for alt_url in alternative_urls[i-1]:
                    print(f"    Testing: {alt_url}")
                    alt_cap = cv2.VideoCapture(alt_url)
                    alt_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    alt_cap.set(cv2.CAP_PROP_TIMEOUT, 5000)
                    
                    if alt_cap.isOpened():
                        ret, frame = alt_cap.read()
                        if ret and frame is not None:
                            height, width = frame.shape[:2]
                            print(f"    ✓ Alternative URL works: {width}x{height}")
                            print(f"    ** Use this URL: {alt_url}")
                            break
                        else:
                            print("    ✗ Connected but no frame")
                    else:
                        print("    ✗ No connection")
                    alt_cap.release()
                    
            cap.release()
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            
    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == "__main__":
    test_rtsp_urls()
