# MyHighlights - Changelog

## Version 1.0.0 - Initial Release (2026-01-04)

### ✨ Features

- **Instagram Authentication**
  - Login with username, password, and 2FA
  - Session persistence (auto-login on restart)
  - Secure session storage
  - Logout functionality

- **Highlight Download**
  - Paste Instagram highlight URLs
  - Auto-download on add
  - Real-time progress tracking
  - Pause functionality (resume coming soon)
  - Download images and videos

- **Video Export**
  - Merge downloaded items into single video
  - Instagram story format (1080x1920, 9:16)
  - Images shown for 3 seconds each
  - Videos included at original duration
  - Real-time build progress
  - Cancel build option
  - H.264 MP4 output

- **Job Management**
  - Multiple concurrent downloads
  - Job cards with status badges
  - Progress bars (download and build)
  - Open folders (downloads, exports, project)
  - Delete jobs (files remain)

- **User Interface**
  - Modern, clean design matching wireframes
  - Login header with status indicator
  - Two-tab layout (By Link / By Username)
  - Job cards with cover, title, info
  - Contextual action buttons
  - Toast notifications (success, error, info)
  - Empty state placeholders
  - Responsive layout

- **File Organization**
  - Organized folder structure
  - Downloads and exports separated
  - Named folders per highlight
  - Session data stored securely

### 🏗️ Architecture

- **Models**: Job, Auth state models
- **Services**: Instagram (aiograpi), Downloader, VideoBuilder (moviepy)
- **Core**: AppState (centralized state), Config
- **UI**: MainWindow, Widgets (Header, JobCard, Toast), Styles (QSS)

### 🔧 Technical Stack

- Python 3.11+
- QtPy (PySide6)
- aiograpi (Instagram API)
- moviepy (video composition)
- qasync (async/await support)
- Pillow (image handling)
- requests (HTTP downloads)

### 📁 Project Structure

```
myhighlights/
├── models/          # Data models
├── services/        # Business logic
├── core/            # State & config
└── ui/              # User interface
    ├── main_window.py
    ├── widgets/
    └── styles.qss
```

### 🐛 Bug Fixes

**v1.0.0 Hotfix 1:**
- Fixed `RuntimeError: no running event loop` on startup
- Fixed font family warning for "-apple-system"
- Removed unsupported CSS property "pointer-events"
- Added QTimer delay for async task initialization

**Changes:**
- Added `QTimer.singleShot()` to delay session restore
- Changed font to "Segoe UI" (cross-platform)
- Removed invalid CSS properties

---

## Known Issues

### Current Limitations

1. **"By Username" tab** - Not implemented yet (placeholder shown)
2. **Cover images** - Show placeholder text instead of actual thumbnails
3. **Resume button** - Pause works, but no explicit resume button
4. **Batch operations** - Can't select multiple jobs at once
5. **Search/filter** - No search functionality for jobs
6. **Settings UI** - Video settings require code editing

### Workarounds

- **Resume downloads**: Downloads resume automatically when started again (progress saved)
- **Cover images**: Will be added in v1.1
- **Batch delete**: Delete jobs one at a time for now
- **Settings**: Edit `myhighlights/core/config.py` manually

---

## Planned Features

### v1.1 (Next Release)

- [ ] Implement "By Username" tab
- [ ] Show actual cover thumbnails
- [ ] Add explicit Resume button
- [ ] Batch job operations (select multiple)
- [ ] Search and filter jobs
- [ ] Settings panel UI
- [ ] Dark theme option
- [ ] Export to different formats (GIF, WebM)

### v1.2 (Future)

- [ ] Job history (load previous downloads)
- [ ] Custom video templates
- [ ] Transitions between clips
- [ ] Background music
- [ ] Text overlays
- [ ] Export presets
- [ ] Cloud storage integration
- [ ] Multi-language support

### v2.0 (Long-term)

- [ ] Batch download from multiple users
- [ ] Scheduled downloads
- [ ] Watch highlights for new content
- [ ] Auto-export on download
- [ ] Advanced video editing
- [ ] Plugin system

---

## Breaking Changes

None - this is the initial release.

---

## Migration Guide

N/A - Initial release.

---

## Deprecations

None.

---

## Security Updates

- Session tokens stored in `data/.session/instagram_session.json`
- Passwords never stored, only session tokens
- All processing happens locally
- No external analytics or tracking

---

## Performance Improvements

- Async downloads for non-blocking UI
- Real-time progress updates
- Efficient state management
- Lazy loading of job cards

---

## Dependencies

### Required

```
qtpy>=2.4.0
qasync>=0.24.0
aiograpi>=3.0.0
moviepy>=1.0.3
pillow>=9.0.0
requests>=2.31.0
PySide6>=6.9.0  (or PyQt6)
```

### System Requirements

- Python 3.11 or higher
- ffmpeg (for video processing)
- 500MB+ free disk space
- Internet connection (for downloads)

---

## Contributors

- Initial development and release

---

## License

Educational/Personal use only.

---

## Support

See:
- README.md - Full documentation
- QUICKSTART.md - Getting started guide
- BUILD_SUMMARY.md - Technical details

---

**Thank you for using MyHighlights!** 🎉

Report issues or request features in the project repository.
