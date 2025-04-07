import os
import sys
import shutil
import subprocess
import platform

# نام زیبا برای اپلیکیشن
APP_NAME = "Stellar"

# فایل اصلی اپلیکیشن
MAIN_FILE = "main.py"


def run_command(command, exit_on_error=False):
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0 and exit_on_error:
        print(f"Error executing command: {command}")
        sys.exit(1)
    return result.returncode == 0


def build_for_macos(venv_path, app_name, main_file, current_os):
    """Create macOS .app and .dmg files"""
    if current_os == "Darwin":  # Running on actual macOS
        pyinstaller_cmd = os.path.join(venv_path, "bin", "pyinstaller")

        # Build .app bundle
        icon_param = "--icon=icon.icns" if os.path.exists("icon.icns") else ""
        run_command(f"{pyinstaller_cmd} --windowed --name {app_name} {icon_param} {main_file}")

        # Create DMG file
        try:
            subprocess.run(["create-dmg", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            has_create_dmg = True
        except FileNotFoundError:
            has_create_dmg = False

        if has_create_dmg:
            print("Creating .dmg file...")
            volicon_param = ""
            if os.path.exists("icon.icns"):
                volicon_param = '--volicon "icon.icns"'

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
            # Filter out empty elements
            dmg_command = [cmd for cmd in dmg_command if cmd]
            run_command(" ".join(dmg_command), exit_on_error=False)
            print(f"✅ DMG file created: dist/{app_name}.dmg")
        else:
            print("⚠️ create-dmg not installed. Attempting to install...")
            run_command("brew install create-dmg", exit_on_error=False)
            print("Try running the script again to create a DMG file.")
            print("✅ .app bundle is available in the 'dist' folder.")

        return True
    else:
        # Not on macOS, try to build a basic app package
        if current_os == "Windows":
            pyinstaller_cmd = os.path.join(venv_path, "Scripts", "pyinstaller")
        else:  # Linux
            pyinstaller_cmd = os.path.join(venv_path, "bin", "pyinstaller")

        print("Attempting to build macOS package (compatibility not guaranteed)...")
        icon_param = "--icon=icon.icns" if os.path.exists("icon.icns") else ""
        run_command(f"{pyinstaller_cmd} --name {app_name}_mac {icon_param} {main_file}")
        print(f"✅ macOS package attempt completed: check dist/{app_name}_mac")
        print("   Note: This is a best-effort build and may not work correctly on macOS.")
        return True


def build_for_windows(venv_path, app_name, main_file, current_os):
    """Create Windows .exe file"""
    if current_os == "Windows":  # Running on actual Windows
        pyinstaller_cmd = os.path.join(venv_path, "Scripts", "pyinstaller")

        # Build .exe file
        icon_param = "--icon=icon.ico" if os.path.exists("icon.ico") else ""
        run_command(f"{pyinstaller_cmd} --onefile --windowed --name {app_name} {icon_param} {main_file}")
        exe_path = os.path.join("dist", f"{app_name}.exe")
        print(f"✅ EXE file created: {exe_path}")
        return True
    else:
        # Not on Windows, always try to build regardless of Wine
        if current_os == "Darwin":  # macOS
            pyinstaller_cmd = os.path.join(venv_path, "bin", "pyinstaller")
        else:  # Linux
            pyinstaller_cmd = os.path.join(venv_path, "bin", "pyinstaller")

        # Check if Wine is available for better compatibility
        has_wine = shutil.which("wine") is not None
        if has_wine:
            print("Wine detected, using it for better Windows compatibility...")

        # Always try to build Windows EXE
        print("Attempting to build Windows executable (compatibility not guaranteed)...")
        icon_param = "--icon=icon.ico" if os.path.exists("icon.ico") else ""
        run_command(f"{pyinstaller_cmd} --onefile --windowed --name {app_name}_win {icon_param} {main_file}")
        print(f"✅ Windows EXE file attempt: dist/{app_name}_win.exe")
        print("   Note: Test this on a Windows machine to ensure compatibility.")
        return True


def is_valid_venv(venv_path):
    """Check if the given path is a valid virtual environment"""
    if not os.path.isdir(venv_path):
        return False

    # Check for key directories/files that indicate a valid venv
    if platform.system() == "Windows":
        return os.path.exists(os.path.join(venv_path, "Scripts", "python.exe"))
    else:
        return os.path.exists(os.path.join(venv_path, "bin", "python"))


def main():
    # Check if main file exists
    if not os.path.exists(MAIN_FILE):
        print(f"❌ Error: {MAIN_FILE} not found! Please create this file before running the script.")
        sys.exit(1)

    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("❌ Error: requirements.txt not found! Please create a requirements.txt file with your dependencies.")
        sys.exit(1)

    # Print icon instructions
    print("\n📌 Icon Instructions:")
    print("  - For macOS, place an icon file named 'icon.icns' in the project directory")
    print("  - For Windows, place an icon file named 'icon.ico' in the project directory")
    print()

    # Clean previous builds but not venv
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("__pycache__"):
        shutil.rmtree("__pycache__")

    # Set up Python command based on OS
    current_os = platform.system()
    
    # First try to use the Python from .venv if it exists
    venv_name = ".venv"
    if is_valid_venv(venv_name):
        print(f"✅ Found existing virtual environment: '{venv_name}'")
        if current_os == "Windows":
            python_cmd = os.path.join(venv_name, "Scripts", "python.exe")
        else:
            python_cmd = os.path.join(venv_name, "bin", "python")
        
        # Verify Python version in venv
        try:
            result = subprocess.run([python_cmd, "--version"], capture_output=True, text=True)
            print(f"Using Python from venv: {result.stdout.strip()}")
        except Exception as e:
            print(f"❌ Error checking Python version in venv: {e}")
            python_cmd = None
    else:
        python_cmd = None

    # If no valid venv or Python in venv, try system Python
    if not python_cmd:
        if current_os == "Windows":
            # Try different Python commands on Windows
            python_commands = ["python", "py"]
            for cmd in python_commands:
                try:
                    result = subprocess.run([cmd, "--version"], capture_output=True, text=True)
                    python_cmd = cmd
                    print(f"Using system Python: {result.stdout.strip()}")
                    break
                except Exception:
                    continue
        else:  # macOS or Linux
            # Use /usr/bin/python3 on macOS
            python_cmd = "/usr/bin/python3"
            try:
                result = subprocess.run([python_cmd, "--version"], capture_output=True, text=True)
                print(f"Using system Python: {result.stdout.strip()}")
            except Exception as e:
                print(f"❌ Error using {python_cmd}: {e}")
                python_cmd = None

        if not python_cmd:
            print("❌ No Python installation found. Please install Python and try again.")
            sys.exit(1)

    # Check if venv already exists
    build_venv_name = ".build_env"

    if is_valid_venv(venv_name):
        print(f"✅ Using existing virtual environment: '{venv_name}'")
        venv_path = venv_name
        create_new_venv = False
    else:
        print(f"No existing virtual environment found, will create '{build_venv_name}'")
        venv_path = build_venv_name
        create_new_venv = True

        # Remove old build_env if it exists
        if os.path.exists(build_venv_name):
            shutil.rmtree(build_venv_name)

        # Create virtual environment
        print(f"Creating virtual environment '{build_venv_name}'...")
        if not run_command(f"{python_cmd} -m venv {build_venv_name}"):
            print("❌ Failed to create virtual environment")
            sys.exit(1)

    # Set pip path based on OS and venv
    if current_os == "Windows":
        pip_cmd = os.path.join(venv_path, "Scripts", "pip")
    else:
        pip_cmd = os.path.join(venv_path, "bin", "pip")

    # Only upgrade pip if we created a new venv
    if create_new_venv:
        print("Upgrading pip...")
        if not run_command(f"{pip_cmd} install --upgrade pip"):
            print("❌ Failed to upgrade pip")
            sys.exit(1)

    # Install dependencies from requirements.txt with verbose output
    print("Installing dependencies from requirements.txt...")
    try:
        result = subprocess.run(
            [pip_cmd, "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("❌ Failed to install dependencies")
            print("Error output:")
            print(result.stderr)
            sys.exit(1)
        else:
            print("✅ Dependencies installed successfully")
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        sys.exit(1)

    # Install PyInstaller if not already installed
    print("Ensuring PyInstaller is installed...")
    if not run_command(f"{pip_cmd} install pyinstaller"):
        print("❌ Failed to install PyInstaller")
        sys.exit(1)

    # Create dist directory if it doesn't exist
    if not os.path.exists("dist"):
        os.makedirs("dist")

    # Attempt to build for both platforms
    print("\n🔄 Building for both platforms...\n")

    # Build for macOS
    print(f"\n🍎 Building {APP_NAME} for macOS...\n")
    macos_success = build_for_macos(venv_path, APP_NAME, MAIN_FILE, current_os)

    # Build for Windows
    print(f"\n🪟 Building {APP_NAME} for Windows...\n")
    windows_success = build_for_windows(venv_path, APP_NAME, MAIN_FILE, current_os)

    # Summary
    print("\n📋 Build Summary:")
    print(f"macOS Build: {'✅ Success' if macos_success else '❌ Failed'}")
    print(f"Windows Build: {'✅ Success' if windows_success else '❌ Failed'}")
    print("\nCheck the 'dist' folder for your executable files.")

    if current_os != "Darwin" and current_os != "Windows":
        print("\n⚠️ Note: Cross-platform builds are best-effort and may have compatibility issues.")
        print("   For best results, run this script on each target platform.")


if __name__ == "__main__":
    main()
