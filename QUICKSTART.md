# MyHighlights - Quick Start Guide

## 🚀 Getting Started

### Step 1: Install Dependencies

Make sure you have Python 3.11+ installed, then run:

```bash
pip install qtpy pyside6 qasync aiograpi moviepy pillow requests
```

**Or use the requirements file:**
```bash
pip install -r requirements.txt
```

### Step 2: Install ffmpeg (Required for Video Export)

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH

### Step 3: Run the Application

**Option 1: Using the launcher script (macOS/Linux)**
```bash
./run.sh
```

**Option 2: Direct Python**
```bash
python main.py
```

---

## 📖 First-Time Usage

### 1. Login to Instagram

When the app launches:

1. Enter your **Instagram username** (without @)
2. Enter your **password**
3. **Optional**: If you have 2FA enabled, enter the **6-digit code** (leave empty if not using 2FA)
4. Click **"Log In"**

✅ **Your session will be saved** - you won't need to log in again!

**Note**: The 2FA field is optional - only fill it in if Instagram prompts you for a code.

### 2. Download Your First Highlight

1. Open Instagram in your browser
2. Navigate to a highlight (stories/highlights/...)
3. Copy the URL from the address bar
   - Example: `https://www.instagram.com/stories/highlights/17901234567890123/`
4. Paste the URL in the input field
5. Click **"Add & Download"**

🎉 The download starts automatically!

### 3. Watch the Progress

You'll see a job card appear with:
- **Cover** - Placeholder for highlight cover
- **Title** - Highlight name
- **Items** - Progress counter (e.g., "Items: 5/12")
- **Status badge** - Current state (Downloading, Downloaded, etc.)
- **Progress bar** - Real-time download progress

### 4. Build a Video

Once download completes:

1. Status changes to **"Downloaded"**
2. Click **"Build Video"** button
3. Wait for video composition (progress shown)
4. Status changes to **"Exported"** when done
5. Click **"View Output"** to see your video!

---

## 🎮 Controls & Features

### Job Card Buttons

| Button | When Available | Action |
|--------|---------------|--------|
| **Pause** | During download | Pause the download |
| **View Downloads** | After download | Open downloads folder |
| **Build Video** | After download | Create merged video |
| **Cancel** | During build | Stop video creation |
| **View Output** | After export | Open exports folder |
| **📁** | Always | Open project folder |
| **🗑** | Always | Delete job (keeps files) |

### Status Badges

- **Downloading** 🔵 - Download in progress
- **Paused** 🟠 - Download paused
- **Downloaded** 🟢 - Ready to build video
- **Building** 🟠 - Creating video
- **Exported** 🟣 - Video ready!
- **Error** 🔴 - Something went wrong

---

## 📁 Where Are My Files?

All downloaded content is saved in:

```
data/
└── Highlights/
    └── <Highlight_Name>/
        ├── downloads/          # Original images and videos
        │   ├── item_1_image.jpg
        │   ├── item_2_video.mp4
        │   └── ...
        └── exports/            # Merged video
            └── <Name>_merged.mp4
```

**Session data:**
```
data/
└── .session/
    └── instagram_session.json  # Your saved login session
```

---

## 💡 Tips & Tricks

### Tip 1: Pause Long Downloads
If you have a large highlight (30+ items), you can:
1. Click **Pause** during download
2. Close the app
3. Reopen and the progress is saved
4. *(Resume button coming soon!)*

### Tip 2: Video Format
Videos are exported in Instagram story format:
- **Resolution**: 1080x1920 (9:16 aspect ratio)
- **FPS**: 30
- **Codec**: H.264 (MP4)
- **Image duration**: 3 seconds each

### Tip 3: Multiple Highlights
You can add multiple highlights at once! Each becomes a separate job card.

### Tip 4: Session Management
- **Logout** clears your session
- **Session file** is saved in `data/.session/`
- **Delete session file** to force fresh login

---

## 🚨 Troubleshooting

### "Please login first" error
**Solution**: Make sure you're logged in before adding highlights.

### "2FA code required"
**Solution**: Get the 6-digit code from your authenticator app and enter it in the "2FA Code" field.

### "Challenge required" error
**Solution**:
1. Open Instagram in your browser
2. Complete any security challenges
3. Try logging in again

### Downloads are slow
**Solution**:
- Instagram may rate-limit downloads
- Try pausing and resuming
- Wait a few minutes between downloads

### Video build fails
**Solution**:
1. Make sure `ffmpeg` is installed: `ffmpeg -version`
2. Check that downloads completed successfully
3. Look for error messages in the console

### App won't start
**Solution**:
```bash
# Reinstall dependencies
pip install --force-reinstall qtpy pyside6 qasync aiograpi moviepy

# Try running with verbose output
python main.py
```

### Font warning in console
**Solution**: Ignore it - it's harmless and doesn't affect functionality.

---

## ⚙️ Advanced Usage

### Change Video Settings

Edit `myhighlights/core/config.py`:

```python
# Make images 5 seconds each
DEFAULT_IMAGE_DURATION = 5

# Square format instead of story
DEFAULT_VIDEO_RESOLUTION = (1080, 1080)

# Higher FPS
DEFAULT_FPS = 60
```

### Custom Styling

Edit `myhighlights/ui/styles.qss` to customize colors and appearance.

### Data Location

To use a different data folder, edit `myhighlights/core/config.py`:

```python
DATA_DIR = Path("/custom/path/data")
```

---

## 🎯 Common Workflows

### Workflow 1: Quick Download & Export

```
1. Paste URL → "Add & Download"
2. Wait for download to complete
3. Click "Build Video"
4. Click "View Output"
5. Done! 🎉
```

### Workflow 2: Download Now, Export Later

```
1. Paste URL → "Add & Download"
2. Wait for download
3. Close app
4. (Later) Reopen app
5. Click "Build Video" on existing job
6. Click "View Output"
```

### Workflow 3: Multiple Highlights

```
1. Paste URL 1 → "Add & Download"
2. Paste URL 2 → "Add & Download"
3. Paste URL 3 → "Add & Download"
4. All download in parallel!
5. Build videos when ready
```

---

## 🔒 Privacy & Security

- ✅ **Passwords not stored** - Only session tokens
- ✅ **Local processing** - Everything happens on your computer
- ✅ **No tracking** - No analytics or telemetry
- ✅ **Open source** - All code is visible

**Important**: Only download content you have permission to access. Respect creators' rights and Instagram's Terms of Service.

---

## 🆘 Getting Help

### Check the logs
The app prints useful info to the console:
```bash
python main.py 2>&1 | tee app.log
```

### Common Error Messages

| Error | Meaning | Fix |
|-------|---------|-----|
| "Invalid username or password" | Login failed | Check credentials |
| "aiograpi not installed" | Missing dependency | `pip install aiograpi` |
| "moviepy not installed" | Missing dependency | `pip install moviepy` |
| "Failed to fetch highlight" | Invalid URL or private | Check URL format |

### Still having issues?

1. Make sure all dependencies are installed
2. Check that you're using Python 3.11+
3. Verify ffmpeg is installed
4. Try deleting the session file and logging in again
5. Check the BUILD_SUMMARY.md for more details

---

## 🎉 You're Ready!

Start downloading highlights and building amazing videos!

```bash
# Launch the app
python main.py

# Or use the launcher
./run.sh
```

**Enjoy MyHighlights!** 🎬
