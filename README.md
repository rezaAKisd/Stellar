# VideoMergerUI

A user-friendly application for merging videos and images with a graphical user interface.

## Features

- Merge multiple videos and images into a single file
- Process multiple folders simultaneously
- Support for various video formats and codecs
- Drag & Drop graphical user interface
- Advanced output quality settings
- Cross-platform support

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Sufficient disk space for dependencies

## Installation

### 1. Create Virtual Environment

#### Windows:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate
```

#### macOS/Linux:
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

### 2. Install Dependencies

After activating the virtual environment, install the dependencies:

```bash
pip install -r requirements.txt
```

### 3. Run the Application

#### Method 1: Direct Execution
```bash
python main.py
```

#### Method 2: Build Executable
To create an executable file, use the `build.py` script:

```bash
python build.py
```

After running the script, executable files will be created in the `dist` folder:
- Windows: `VideoMerger.exe`
- macOS: `VideoMerger.app`

## Usage

1. Launch the application
2. Drag and drop folders containing videos and images into the main window
3. Configure your settings:
   - Image display duration
   - Output quality
   - Output filename
   - Other settings
4. Click the "Start Processing" button

## Default Settings

- Image display duration: 10 seconds
- Output quality: Original
- Video codec: libx264
- Video bitrate: 700k
- Audio codec: aac
- Audio bitrate: 128k
- FPS: 30

## Supported Platforms

- Windows 10/11
- macOS 10.15 or higher
- Linux (tested on Ubuntu 20.04)

## Troubleshooting

### Common Issues

1. **Dependency Installation Errors**:
   - Ensure the virtual environment is activated
   - Run `pip install -r requirements.txt` again

2. **Application Runtime Errors**:
   - Verify all dependencies are installed
   - Reactivate the virtual environment
   - Restart the application

3. **Executable Build Issues**:
   - Ensure PyInstaller is installed
   - Run the `build.py` script again

## Contributing

We welcome contributions from the community! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/yourusername/VideoMergerUI/tags).

## Authors

- **Your Name** - *Initial work* - [YourUsername](https://github.com/yourusername)

See also the list of [contributors](https://github.com/yourusername/VideoMergerUI/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Acknowledgments

- Thanks to all contributors who have helped with this project
- Special thanks to the open source community for their tools and libraries

## Support

If you encounter any issues or have suggestions:
1. Check the [existing issues](https://github.com/yourusername/VideoMergerUI/issues)
2. Create a new issue with detailed information
3. Join our [Discord community](https://discord.gg/your-server) for real-time support 