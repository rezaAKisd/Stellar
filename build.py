import os
import sys
import shutil
import subprocess
import platform
import glob
from typing import Optional, Tuple

# نام زیبا برای اپلیکیشن
APP_NAME = "Stellar"

# فایل اصلی اپلیکیشن
MAIN_FILE = "main.py"

# Minimum required Python version
MIN_PYTHON_VERSION = (3, 9)

# Clean up patterns
CLEANUP_PATTERNS = [
    "*.spec",
    "build/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log"
]

def get_python_version(python_path: str) -> Tuple[int, int]:
    """Get Python version as a tuple of (major, minor)"""
    try:
        result = subprocess.run([python_path, "--version"], capture_output=True, text=True)
        version_str = result.stdout.strip().split()[1]  # e.g., "3.9.6"
        major, minor = map(int, version_str.split('.')[:2])
        return (major, minor)
    except Exception as e:
        print(f"Error getting Python version: {e}")
        return (0, 0)

def check_python_version(python_path: str) -> bool:
    """Check if Python version meets minimum requirements"""
    version = get_python_version(python_path)
    if version < MIN_PYTHON_VERSION:
        print(f"Error: Python version {version[0]}.{version[1]} is below minimum required version {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}")
        return False
    return True

def clean_up():
    """Clean up temporary files and build artifacts"""
    print("Cleaning up temporary files...")
    for pattern in CLEANUP_PATTERNS:
        for file in glob.glob(pattern):
            if os.path.isdir(file):
                shutil.rmtree(file, ignore_errors=True)
            else:
                try:
                    os.remove(file)
                except Exception:
                    pass

def run_command(command: str, exit_on_error: bool = False) -> bool:
    """Run a shell command and handle errors"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error code: {e.returncode}")
        if exit_on_error:
            sys.exit(1)
        return False

def get_python_path() -> Optional[str]:
    """Get the appropriate Python path based on OS and environment"""
    current_os = platform.system()
    
    # Try to use Python from .venv if it exists
    if os.path.exists(".venv"):
        if current_os == "Windows":
            python_path = os.path.join(".venv", "Scripts", "python.exe")
        else:
            python_path = os.path.join(".venv", "bin", "python")
        
        if os.path.exists(python_path) and check_python_version(python_path):
            return python_path
    
    # Try system Python
    if current_os == "Windows":
        for cmd in ["python", "py"]:
            try:
                if check_python_version(cmd):
                    return cmd
            except Exception:
                continue
    else:
        # Try different Python paths
        python_paths = [
            "/usr/bin/python3",
            "/usr/local/bin/python3",
            "/opt/homebrew/bin/python3",
            "python3"
        ]
        for path in python_paths:
            try:
                if check_python_version(path):
                    return path
            except Exception:
                continue
    
    return None

def setup_venv(python_path: str) -> Optional[str]:
    """Set up a virtual environment"""
    if not os.path.exists(".venv"):
        print(f"Creating virtual environment '.venv'...")
        if not run_command(f"{python_path} -m venv .venv"):
            return None
    else:
        print(f"Using existing virtual environment '.venv'")
    
    return ".venv"

def install_dependencies(venv_path: str) -> bool:
    """Install required dependencies"""
    current_os = platform.system()
    pip_cmd = os.path.join(venv_path, "Scripts", "pip") if current_os == "Windows" else os.path.join(venv_path, "bin", "pip")
    
    # Upgrade pip
    if not run_command(f"{pip_cmd} install --upgrade pip"):
        return False
    
    # Install dependencies
    if not run_command(f"{pip_cmd} install -r requirements.txt"):
        return False
    
    # Install PyInstaller
    if not run_command(f"{pip_cmd} install pyinstaller"):
        return False
    
    return True

def build_for_macos(venv_path: str, app_name: str, main_file: str) -> bool:
    """Build macOS application"""
    pyinstaller_cmd = os.path.join(venv_path, "bin", "pyinstaller")
    
    # Build .app bundle
    icon_param = "--icon=icon.icns" if os.path.exists("icon.icns") else ""
    if not run_command(f"{pyinstaller_cmd} --windowed --name {app_name} {icon_param} {main_file}"):
        return False
    
    # Create DMG file
    if not shutil.which("create-dmg"):
        print("Warning: create-dmg not found. Skipping DMG creation.")
        return True
    
    print("Creating .dmg file...")
    volicon_param = "--volicon icon.icns" if os.path.exists("icon.icns") else ""
    
    dmg_command = [
        "create-dmg",
        f"--volname {app_name}",
        volicon_param,
        "--window-pos 200 120",
        "--window-size 600 400",
        "--icon-size 100",
        f'--icon "{app_name}.app" 175 120',
        f'--hide-extension "{app_name}.app"',
        "--app-drop-link 425 120",
        f'"dist/{app_name}.dmg"',
        f'"dist/{app_name}.app"'
    ]
    
    return run_command(" ".join(cmd for cmd in dmg_command if cmd))

def build_for_windows(venv_path: str, app_name: str, main_file: str) -> bool:
    """Build Windows application"""
    pyinstaller_cmd = os.path.join(venv_path, "Scripts", "pyinstaller")
    
    icon_param = "--icon=icon.ico" if os.path.exists("icon.ico") else ""
    return run_command(f"{pyinstaller_cmd} --onefile --windowed --name {app_name} {icon_param} {main_file}")

def build_for_linux(venv_path: str, app_name: str, main_file: str) -> bool:
    """Build Linux application"""
    pyinstaller_cmd = os.path.join(venv_path, "bin", "pyinstaller")
    
    icon_param = "--icon=icon.png" if os.path.exists("icon.png") else ""
    return run_command(f"{pyinstaller_cmd} --onefile --name {app_name} {icon_param} {main_file}")

def main():
    # Clean up any existing build artifacts
    clean_up()
    
    # Check if main file exists
    if not os.path.exists(MAIN_FILE):
        print(f"Error: {MAIN_FILE} not found!")
        sys.exit(1)
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("Error: requirements.txt not found!")
        sys.exit(1)
    
    # Get build platform from environment variable
    build_platform = os.environ.get("BUILD_PLATFORM", "").lower()
    if not build_platform:
        print("Error: BUILD_PLATFORM environment variable not set!")
        print("Please set BUILD_PLATFORM to one of: windows, macos, linux")
        sys.exit(1)
    
    # Get Python path
    python_path = get_python_path()
    if not python_path:
        print(f"Error: No suitable Python installation found (minimum version: {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]})!")
        sys.exit(1)
    
    # Print Python version info
    version = get_python_version(python_path)
    print(f"Using Python {version[0]}.{version[1]}")
    
    # Set up virtual environment
    venv_path = setup_venv(python_path)
    if not venv_path:
        print("Error: Failed to create virtual environment!")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies(venv_path):
        print("Error: Failed to install dependencies!")
        sys.exit(1)
    
    # Create dist directory
    os.makedirs("dist", exist_ok=True)
    
    # Build for the specified platform
    print(f"\nBuilding for {build_platform}...\n")
    
    success = False
    if build_platform == "windows":
        success = build_for_windows(venv_path, APP_NAME, MAIN_FILE)
    elif build_platform == "macos":
        success = build_for_macos(venv_path, APP_NAME, MAIN_FILE)
    elif build_platform == "linux":
        success = build_for_linux(venv_path, APP_NAME, MAIN_FILE)
    else:
        print(f"Error: Unknown build platform: {build_platform}")
        sys.exit(1)
    
    if not success:
        print(f"Error: Failed to build for {build_platform}!")
        sys.exit(1)
    
    # Clean up temporary files
    clean_up()
    
    print("\nBuild completed successfully!")
    print(f"Check the 'dist' folder for your {build_platform} executable files.")

if __name__ == "__main__":
    main()
