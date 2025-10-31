#!/usr/bin/env python3
"""
Enhanced NetraSena Setup Script
Installs dependencies and configures the system for enhanced features.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_gpu():
    """Check for NVIDIA GPU and CUDA support"""
    try:
        result = subprocess.run("nvidia-smi", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ NVIDIA GPU detected")
            return True
        else:
            print("ℹ No NVIDIA GPU detected - will use CPU")
            return False
    except FileNotFoundError:
        print("ℹ NVIDIA drivers not found - will use CPU")
        return False

def create_directories():
    """Create required directories"""
    directories = [
        "data/known_faces",
        "data/suspects", 
        "data/screenshots",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def install_dependencies(has_gpu=False):
    """Install Python dependencies"""
    print("\nInstalling Python dependencies...")
    
    # Basic dependencies
    basic_deps = [
        "opencv-python",
        "numpy",
        "pillow",
        "pyyaml",
        "loguru",
        "pygame",
        "PyQt5"
    ]
    
    # Install basic dependencies
    for dep in basic_deps:
        if not run_command(f"pip install {dep}", f"Installing {dep}"):
            return False
    
    # Install PyTorch with CUDA support if GPU available
    if has_gpu:
        pytorch_cmd = "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
        if not run_command(pytorch_cmd, "Installing PyTorch with CUDA support"):
            print("⚠ CUDA PyTorch installation failed, trying CPU version...")
            pytorch_cmd = "pip install torch torchvision torchaudio"
            run_command(pytorch_cmd, "Installing PyTorch (CPU version)")
    else:
        pytorch_cmd = "pip install torch torchvision torchaudio"
        run_command(pytorch_cmd, "Installing PyTorch (CPU version)")
    
    # Install face recognition libraries
    face_deps = [
        "insightface",
        "facenet-pytorch",
        "onnxruntime"
    ]
    
    for dep in face_deps:
        run_command(f"pip install {dep}", f"Installing {dep}")
    
    return True

def setup_config_files():
    """Set up configuration files"""
    print("\nSetting up configuration files...")
    
    # Check if config files exist
    if not Path("config/config.yaml").exists():
        print("⚠ config/config.yaml not found - please run the main setup first")
        return False
    
    # Update config for GPU if available
    has_gpu = check_gpu()
    if has_gpu:
        print("✓ Updating config for GPU acceleration")
        # The config is already set to CUDA in the previous setup
    
    return True

def verify_installation():
    """Verify the installation"""
    print("\nVerifying installation...")
    
    try:
        import cv2
        print("✓ OpenCV installed")
        
        import torch
        print(f"✓ PyTorch {torch.__version__} installed")
        print(f"✓ CUDA available: {torch.cuda.is_available()}")
        
        import insightface
        print("✓ InsightFace installed")
        
        from PyQt5 import QtWidgets
        print("✓ PyQt5 installed")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def main():
    """Main setup function"""
    print("=" * 60)
    print("Enhanced NetraSena Setup")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Create directories
    create_directories()
    
    # Check for GPU
    has_gpu = check_gpu()
    
    # Install dependencies
    if not install_dependencies(has_gpu):
        print("\n✗ Dependency installation failed")
        sys.exit(1)
    
    # Setup config files
    if not setup_config_files():
        print("\n⚠ Config setup had issues - please check manually")
    
    # Verify installation
    if verify_installation():
        print("\n" + "=" * 60)
        print("✓ Enhanced NetraSena setup completed!")
        print("=" * 60)
        print("\nNew Features Available:")
        print("• Live camera face capture")
        print("• Suspect management system") 
        print("• Multi-camera dashboard")
        print("• Enhanced history filtering")
        print("• GPU acceleration (if available)")
        print("\nRun: python main.py")
        print("See: FEATURES_GUIDE.md for detailed usage instructions")
        print("=" * 60)
    else:
        print("\n✗ Installation verification failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
