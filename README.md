# Stellar

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

Stellar is a desktop application for merging videos and images, built with PySide6.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/Stellar.git
cd Stellar

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Features

- Merge multiple video files into one
- Beautiful and intuitive user interface
- Support for various video formats
- Cross-platform compatibility (Windows, macOS, Linux)
- Automated builds and releases
- System-specific Python version support

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

## Installation

### Windows

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### macOS/Linux

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running the Application

```bash
# Activate the virtual environment (if not already activated)
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Run the application
python main.py
```

### Building Executables

The project includes a build script that can create platform-specific executables. The script will automatically:
1. Find a compatible Python installation (3.9 or higher)
2. Create a clean virtual environment
3. Install all required dependencies
4. Build the executable for the specified platform
5. Clean up temporary files

#### Local Build

```bash
# For Windows
export BUILD_PLATFORM=windows
python build.py

# For macOS
export BUILD_PLATFORM=macos
python build.py

# For Linux
export BUILD_PLATFORM=linux
python build.py
```

#### Automated Builds (CI/CD)

The project uses GitHub Actions for automated builds. When you push to the master branch:
1. Three parallel jobs run to build for Windows, macOS, and Linux
2. Each job uses the system Python on the respective platform
3. A new release is created with all platform builds

To test the CI/CD workflow locally:
```bash
# Install act (GitHub Actions local runner)
brew install act

# List available jobs
act -l

# Run all jobs
act
```

## Configuration

### Default Settings

- Output format: MP4
- Video codec: H.264
- Audio codec: AAC
- Resolution: Same as first input video
- Frame rate: Same as first input video

### Supported Platforms

- Windows 10/11 (64-bit)
- macOS 10.15 or later
- Linux (Ubuntu 20.04 or later)

## Troubleshooting

### Common Issues

1. **Python Version Issues**
   - Ensure you have Python 3.9 or higher installed
   - The build script will automatically find a compatible version
   - Check available Python versions: `python --version`

2. **Missing Dependencies**
   - Ensure all requirements are installed: `pip install -r requirements.txt`
   - The build script will handle dependency installation

3. **Build Issues**
   - Clean up previous builds: Delete `dist/` and `build/` directories
   - Ensure virtual environment is activated
   - Check BUILD_PLATFORM environment variable is set correctly

4. **Video Processing Issues**
   - Verify input video formats are supported
   - Check available disk space
   - Ensure sufficient system memory

## Contributing

We welcome contributions! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on:
- Code style
- Pull request process
- Development workflow

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python -m pytest`
5. Submit a pull request

## Support

- [Discord Community](https://discord.gg/your-invite-link)
- [GitHub Issues](https://github.com/yourusername/Stellar/issues)
- Email: your.email@example.com

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to all contributors
- Special thanks to the open-source community
- Inspired by similar projects 