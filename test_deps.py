#!/usr/bin/env python3
"""Test script to check dependencies"""

print("Testing dependencies...")

try:
    import cv2
    print("✓ OpenCV imported successfully")
except ImportError as e:
    print(f"✗ OpenCV import failed: {e}")

try:
    import numpy as np
    print(f"✓ NumPy imported successfully (version: {np.__version__})")
except ImportError as e:
    print(f"✗ NumPy import failed: {e}")

try:
    import onnxruntime
    print(f"✓ ONNXRuntime imported successfully (version: {onnxruntime.__version__})")
except ImportError as e:
    print(f"✗ ONNXRuntime import failed: {e}")

try:
    import insightface
    print("✓ InsightFace imported successfully")
except ImportError as e:
    print(f"✗ InsightFace import failed: {e}")

try:
    from PyQt5.QtWidgets import QApplication
    print("✓ PyQt5 imported successfully")
except ImportError as e:
    print(f"✗ PyQt5 import failed: {e}")

print("Dependency test completed.")
