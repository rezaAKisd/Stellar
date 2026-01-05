# MyHighlights - Instagram Highlight Downloader

A polished desktop application for downloading and managing Instagram highlights, built with Python, QtPy, and aiograpi.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Qt](https://img.shields.io/badge/Qt-PySide6-green.svg)
![Instagram](https://img.shields.io/badge/Instagram-aiograpi-purple.svg)

## ✨ Features

- **Real Instagram Authentication** - Login with username, password, and 2FA support
- **Highlight Download** - Download Instagram highlights by pasting the link
- **Pause/Resume** - Control downloads with pause/resume functionality
- **Video Export** - Merge downloaded items into a single video file
- **Progress Tracking** - Real-time progress bars for downloads and exports
- **Session Persistence** - Save your login session for future use
- **Clean UI** - Modern, polished interface matching the wireframe design

## 📸 Screenshots

See the wireframe screenshots in the `Desktop/Screenshot...` files for the exact UI design.

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- PySide6 (or PyQt6)
- aiograpi
- moviepy
- qasync

### Installation

1. **Clone or navigate to the project directory**:
```bash
cd /Users/rezaakbari/PycharmProjects/Stellar
```

2. **Install dependencies**:
```bash
pip install qtpy pyside6 aiograpi moviepy qasync pillow requests
```

Or use the requirements file:
```bash
pip install -r requirements.txt
```

### Running the Application

```bash
python main.py
```

## 📖 User Guide

### 1. Login to Instagram

1. Enter your Instagram **username**
2. Enter your **password**
3. **Optional**: If you have 2FA enabled, enter the **6-digit code** (leave empty otherwise)
4. Click **"Log In"**

Your session will be saved securely, so you won't need to log in again.

**Note**: The 2FA code field is optional. Only enter a code if Instagram requires it for your account.

### 2. Download a Highlight

1. Go to Instagram and navigate to a highlight
2. Copy the highlight URL (should look like: `https://www.instagram.com/stories/highlights/...`)
3. Paste the URL in the input field
4. Click **"Add & Download"**

The download will start automatically!

### 3. Working with Jobs

Each highlight becomes a "job" with the following states:

- **Downloading** - Currently downloading items (you can pause)
- **Paused** - Download paused (click to resume)
- **Downloaded** - All items downloaded (ready to build video)
- **Building** - Video is being created (you can cancel)
- **Exported** - Video successfully created

### 4. Build a Video

1. Wait for download to complete
2. Click **"Build Video"**
3. Wait for the export to finish
4. Click **"View Output"** to see your video

### 5. Managing Downloads

- **Pause** - Pause an ongoing download
- **View Downloads** - Open the downloads folder
- **Build Video** - Create a merged video from downloaded items
- **Cancel** - Cancel video building
- **View Output** - Open the exports folder
- **📁** - Open the project folder
- **🗑** - Delete the job (files remain)

## 📁 Folder Structure

Downloaded content is organized as follows:

```
data/
├── Highlights/
│   └── <Highlight_Name>/
│       ├── downloads/     # Original media files
│       └── exports/       # Merged video files
└── .session/
    └── instagram_session.json  # Saved login session
```

## 🏗️ Architecture

### Project Structure

```
myhighlights/
├── models/              # Data models (Job, Auth)
├── services/            # Business logic
│   ├── instagram.py     # Instagram API (aiograpi)
│   ├── downloader.py    # Download manager
│   └── video_builder.py # Video composition (moviepy)
├── core/                # Application core
│   ├── state.py         # State management
│   └── config.py        # Configuration
└── ui/                  # User interface
    ├── main_window.py   # Main application window
    ├── widgets/         # UI components
    │   ├── header.py    # Login header
    │   ├── job_card.py  # Highlight job card
    │   └── toast.py     # Toast notifications
    └── styles.qss       # Stylesheet
```

### Key Technologies

- **QtPy** - Cross-platform Qt bindings
- **aiograpi** - Instagram API client
- **moviepy** - Video editing library
- **qasync** - Async/await support for Qt

## ⚙️ Configuration

Default settings in `myhighlights/core/config.py`:

- **Image duration**: 3 seconds per image in video
- **Video resolution**: 1080x1920 (Instagram story format)
- **FPS**: 30 frames per second
- **Toast duration**: 3 seconds

## 🔒 Security & Privacy

- **Session Storage**: Login sessions are saved in `data/.session/instagram_session.json`
- **No Password Storage**: Only session tokens are stored, never your password
- **Local Processing**: All downloads and video processing happen locally
- **Instagram TOS**: Only use this app for content you have rights to download

## 🐛 Troubleshooting

### "aiograpi not installed"

```bash
pip install aiograpi
```

### "moviepy not installed"

```bash
pip install moviepy
```

### Login fails with "2FA Required"

Enter your 6-digit 2FA code in the "2FA Code" field before clicking "Log In".

### "Challenge required" error

Instagram requires you to verify your account through their website. Open Instagram in a browser, complete the challenge, then try logging in again.

### Downloads fail

Make sure you're logged in and have a stable internet connection. Instagram may rate-limit downloads if you download too many items too quickly.

### Video build fails

Ensure you have `ffmpeg` installed on your system:

**macOS**:
```bash
brew install ffmpeg
```

**Linux**:
```bash
sudo apt-get install ffmpeg
```

**Windows**:
Download from https://ffmpeg.org/download.html

## 🎨 Customization

### Modify the Theme

Edit `myhighlights/ui/styles.qss` to customize colors, fonts, and styles.

### Change Video Settings

Edit `myhighlights/core/config.py`:

```python
DEFAULT_IMAGE_DURATION = 5  # 5 seconds per image
DEFAULT_VIDEO_RESOLUTION = (1080, 1080)  # Square format
DEFAULT_FPS = 60  # 60 FPS
```

## 📝 Development

### Running Tests

```bash
python -m pytest tests/
```

### Code Style

```bash
black myhighlights/
flake8 myhighlights/
```

### Building Executable

```bash
pyinstaller --name MyHighlights --windowed main.py
```

## 🤝 Contributing

This is a personal project, but feel free to fork and customize for your own use.

## ⚠️ Disclaimer

This tool is for personal use only. Make sure you have the rights to download any content you access through Instagram. Always respect content creators' rights and Instagram's Terms of Service.

## 📜 License

Educational/Personal use only.

## 🙏 Acknowledgments

- **aiograpi** - Excellent Instagram API client
- **moviepy** - Powerful video editing library
- **Qt** - Cross-platform UI framework

---

**Built with** ❤️ **using Python + Qt**

For questions or issues, please check the troubleshooting section above.
