# MyHighlights - Complete Implementation Plan

## 🎯 Overview

Building a desktop app that downloads Instagram highlights with:
- **Real Instagram authentication** using aiograpi
- **Exact wireframe design** implementation
- **Full download/export functionality** with pause/resume
- **Clean, modern UI** with Qt

---

## 📊 Wireframe Analysis

### UI Components Identified

**1. Header Section:**
- App branding: "MyHighlights" (left)
- Login form (right):
  - Username input field
  - Password input field
  - 2FA Code input field (6 digits)
  - "Log In" button (primary)
  - "Log Out" button (secondary)
  - Status indicator: "Logged out" / "Logged in"
- Session message: "Your session will be saved so you won't need to log in again"

**2. Tab Navigation:**
- Two tabs: "By Highlight Link" | "By Username"
- Underline indicator for active tab

**3. Input Section (By Highlight Link tab):**
- Large input field: "Paste highlight link..."
- "Add & Download" button (dark)
- Help text: "Download starts automatically after the link is validated"

**4. Jobs List Section:**
- Title: "Highlight Jobs"
- Job cards showing:
  - Cover image thumbnail (left)
  - Job info:
    - Title/name
    - Item count: "Items: 12/18" (downloaded/total)
    - Folder path: "Folder: .../Highlights/name/"
  - Progress bar (for active operations)
  - Progress text: "Building video... 78%"
  - Status badge: "Downloading", "Downloaded", "Building", "Exported"
  - Action buttons (right):
    - "Pause" (during download)
    - "View Downloads" (after download)
    - "Build Video" (after download)
    - "Cancel" (during build)
    - "View Output" (after export)
  - Icons: Folder icon, Delete icon

**5. Empty State:**
- Link icon (centered)
- "No highlights yet"
- "Paste a highlight link and click 'Add & Download'"

**6. Toast Notifications:**
- Bottom-right corner
- "Download completed." with checkmark icon
- Auto-dismiss after 3 seconds

---

## 🏗️ Architecture (Revised)

### Layer Structure

```
┌─────────────────────────────────────────┐
│         Presentation Layer               │
│  ┌──────────┐  ┌──────────┐            │
│  │  Views   │←─│ViewModels│            │
│  │  (Qt UI) │  │          │            │
│  └──────────┘  └──────────┘            │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┴──────────────────────┐
│        Application Layer                 │
│  ┌──────────────────┐                   │
│  │   Use Cases      │                   │
│  │  - Download      │                   │
│  │  - Build Video   │                   │
│  │  - Auth          │                   │
│  └──────────────────┘                   │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┴──────────────────────┐
│       Infrastructure Layer               │
│  ┌─────────────┐  ┌─────────────┐      │
│  │  Instagram  │  │    Video    │      │
│  │  (aiograpi) │  │  (moviepy)  │      │
│  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────┘
```

### Key Differences from Previous Version

1. **Simpler architecture**: Less DDD, more pragmatic
2. **Header login**: Username/password directly in UI
3. **Real Instagram**: aiograpi integration
4. **Real video**: moviepy for actual video composition
5. **Job management**: Pause/resume/cancel operations
6. **Single view**: No user detail page, simplified flow

---

## 📝 Step-by-Step Implementation

### Phase 1: Project Setup & Core Structure

#### Step 1.1: Initialize New Structure
```bash
# Clean up previous structure
rm -rf app/

# Create new simpler structure
mkdir -p myhighlights/{core,services,ui,models}
```

**New Structure:**
```
myhighlights/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── job.py              # HighlightJob model
│   └── auth.py             # Authentication state
├── services/
│   ├── __init__.py
│   ├── instagram.py        # Instagram service (aiograpi)
│   ├── downloader.py       # Download manager
│   └── video_builder.py    # Video composition
├── core/
│   ├── __init__.py
│   ├── state.py           # Application state
│   └── config.py          # Configuration
└── ui/
    ├── __init__.py
    ├── main_window.py     # Main window
    ├── widgets/
    │   ├── __init__.py
    │   ├── header.py      # Login header
    │   ├── job_card.py    # Highlight job card
    │   └── toast.py       # Toast notification
    └── styles.qss         # Stylesheet
```

#### Step 1.2: Install Dependencies
```python
# requirements.txt additions
aiograpi>=3.0.0
moviepy>=1.0.3
pillow>=9.0.0
requests>=2.31.0
```

---

### Phase 2: Data Models

#### Step 2.1: Job Model (`models/job.py`)

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from pathlib import Path

class JobStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    DOWNLOADED = "downloaded"
    BUILDING = "building"
    BUILD_CANCELLED = "cancelled"
    EXPORTED = "exported"
    ERROR = "error"

@dataclass
class HighlightItem:
    """Single media item in a highlight"""
    url: str
    type: str  # 'image' or 'video'
    thumbnail_url: str
    local_path: Optional[str] = None
    downloaded: bool = False

@dataclass
class HighlightJob:
    """A highlight download/export job"""
    id: str
    title: str
    source_url: str
    cover_url: str
    folder_path: Path

    # Items
    items: List[HighlightItem]
    total_items: int
    downloaded_items: int = 0

    # Status
    status: JobStatus = JobStatus.PENDING
    download_progress: float = 0.0  # 0-1
    build_progress: float = 0.0     # 0-1
    error_message: Optional[str] = None

    # Paths
    downloads_folder: Optional[Path] = None
    exports_folder: Optional[Path] = None
    output_video_path: Optional[Path] = None

    # Control flags
    should_pause: bool = False
    should_cancel: bool = False
```

#### Step 2.2: Auth Model (`models/auth.py`)

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class AuthState:
    """Authentication state"""
    is_logged_in: bool = False
    username: Optional[str] = None
    session_file: Optional[str] = None
    needs_2fa: bool = False
    error_message: Optional[str] = None
```

---

### Phase 3: Instagram Service (aiograpi)

#### Step 3.1: Instagram Service (`services/instagram.py`)

```python
import asyncio
from pathlib import Path
from typing import Optional, List, Callable
from aiograpi import Client
from aiograpi.exceptions import (
    TwoFactorRequired,
    ChallengeRequired,
    LoginRequired
)

class InstagramService:
    """Instagram API service using aiograpi"""

    def __init__(self, session_dir: Path):
        self.client = Client()
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.session_dir / "session.json"

    async def login(
        self,
        username: str,
        password: str,
        verification_code: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Login to Instagram
        Returns: (success, error_message)
        """
        try:
            # Try to load existing session
            if self.session_file.exists():
                try:
                    self.client.load_settings(self.session_file)
                    self.client.login(username, password)
                    return True, None
                except:
                    pass  # Session invalid, continue with fresh login

            # Fresh login
            if verification_code:
                self.client.login(username, password, verification_code=verification_code)
            else:
                self.client.login(username, password)

            # Save session
            self.client.dump_settings(self.session_file)
            return True, None

        except TwoFactorRequired as e:
            return False, "2FA_REQUIRED"
        except ChallengeRequired as e:
            return False, f"Challenge required: {str(e)}"
        except Exception as e:
            return False, f"Login failed: {str(e)}"

    async def logout(self):
        """Logout and clear session"""
        if self.session_file.exists():
            self.session_file.unlink()

    async def get_highlight_info(self, highlight_url: str) -> dict:
        """
        Get highlight information from URL
        Returns: {
            'id': str,
            'title': str,
            'cover_url': str,
            'items': List[dict]
        }
        """
        # Parse highlight ID from URL
        # URL format: https://www.instagram.com/stories/highlights/<highlight_id>/
        parts = highlight_url.strip('/').split('/')
        highlight_id = parts[-1]

        # Fetch highlight
        highlight = self.client.highlight_info(highlight_id)

        items = []
        for item in highlight.items:
            items.append({
                'url': item.video_url if item.video_url else item.thumbnail_url,
                'type': 'video' if item.video_url else 'image',
                'thumbnail_url': item.thumbnail_url,
            })

        return {
            'id': highlight.pk,
            'title': highlight.title or f"Highlight {highlight_id}",
            'cover_url': highlight.cover_media.thumbnail_url,
            'items': items,
            'total_items': len(items)
        }

    async def download_media(
        self,
        url: str,
        destination: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Path:
        """Download a single media file"""
        import requests

        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))

        # Generate filename
        extension = 'mp4' if 'video' in response.headers.get('content-type', '') else 'jpg'
        filename = f"{hash(url)}_{int(time.time())}.{extension}"
        filepath = destination / filename

        downloaded = 0
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

        return filepath
```

---

### Phase 4: Download Manager

#### Step 4.1: Download Manager (`services/downloader.py`)

```python
import asyncio
from pathlib import Path
from typing import Callable, Optional
from ..models.job import HighlightJob, JobStatus, HighlightItem

class DownloadManager:
    """Manages download operations with pause/resume support"""

    def __init__(self, instagram_service):
        self.instagram = instagram_service
        self.active_downloads = {}  # job_id -> task

    async def start_download(
        self,
        job: HighlightJob,
        progress_callback: Optional[Callable[[HighlightJob], None]] = None
    ):
        """Start or resume downloading a highlight job"""
        job.status = JobStatus.DOWNLOADING
        job.should_pause = False

        # Create folders
        job.downloads_folder = job.folder_path / "downloads"
        job.downloads_folder.mkdir(parents=True, exist_ok=True)

        # Download each item
        for idx, item in enumerate(job.items):
            # Check pause flag
            if job.should_pause:
                job.status = JobStatus.PAUSED
                if progress_callback:
                    progress_callback(job)
                break

            # Skip already downloaded
            if item.downloaded:
                continue

            try:
                # Download item
                def item_progress(downloaded, total):
                    # Update overall progress
                    item_progress = downloaded / total if total > 0 else 0
                    overall = (idx + item_progress) / job.total_items
                    job.download_progress = overall
                    if progress_callback:
                        progress_callback(job)

                local_path = await self.instagram.download_media(
                    item.url,
                    job.downloads_folder,
                    item_progress
                )

                item.local_path = str(local_path)
                item.downloaded = True
                job.downloaded_items += 1

                # Update progress
                job.download_progress = job.downloaded_items / job.total_items
                if progress_callback:
                    progress_callback(job)

            except Exception as e:
                job.status = JobStatus.ERROR
                job.error_message = f"Failed to download item {idx + 1}: {str(e)}"
                if progress_callback:
                    progress_callback(job)
                return

        # Mark as complete if not paused
        if not job.should_pause:
            job.status = JobStatus.DOWNLOADED
            job.download_progress = 1.0
            if progress_callback:
                progress_callback(job)

    def pause_download(self, job: HighlightJob):
        """Pause an ongoing download"""
        job.should_pause = True

    async def resume_download(
        self,
        job: HighlightJob,
        progress_callback: Optional[Callable[[HighlightJob], None]] = None
    ):
        """Resume a paused download"""
        await self.start_download(job, progress_callback)
```

---

### Phase 5: Video Builder

#### Step 5.1: Video Builder (`services/video_builder.py`)

```python
import asyncio
from pathlib import Path
from typing import Callable, Optional, List
from moviepy.editor import (
    VideoFileClip, ImageClip, concatenate_videoclips,
    CompositeVideoClip, AudioFileClip
)
from ..models.job import HighlightJob, JobStatus

class VideoBuilder:
    """Build videos from downloaded highlights"""

    def __init__(self):
        self.default_image_duration = 3  # seconds
        self.default_resolution = (1080, 1920)  # Instagram story size

    async def build_video(
        self,
        job: HighlightJob,
        progress_callback: Optional[Callable[[HighlightJob], None]] = None
    ):
        """Build a video from highlight items"""
        job.status = JobStatus.BUILDING
        job.build_progress = 0.0
        job.should_cancel = False

        # Create exports folder
        job.exports_folder = job.folder_path / "exports"
        job.exports_folder.mkdir(parents=True, exist_ok=True)

        try:
            clips = []
            total_items = len([i for i in job.items if i.downloaded])

            for idx, item in enumerate(job.items):
                # Check cancel flag
                if job.should_cancel:
                    job.status = JobStatus.BUILD_CANCELLED
                    if progress_callback:
                        progress_callback(job)
                    return

                if not item.downloaded or not item.local_path:
                    continue

                path = Path(item.local_path)

                if item.type == 'video':
                    clip = VideoFileClip(str(path))
                else:
                    # Image: create video clip
                    clip = ImageClip(str(path)).set_duration(self.default_image_duration)

                # Resize to Instagram story size
                clip = clip.resize(self.default_resolution)
                clips.append(clip)

                # Update progress
                job.build_progress = (idx + 1) / total_items
                if progress_callback:
                    progress_callback(job)

            # Concatenate all clips
            if clips:
                final_clip = concatenate_videoclips(clips, method="compose")

                # Output path
                output_name = f"{job.title.replace(' ', '_')}_merged.mp4"
                output_path = job.exports_folder / output_name

                # Write video file
                final_clip.write_videofile(
                    str(output_path),
                    fps=30,
                    codec='libx264',
                    audio_codec='aac',
                    preset='medium',
                    logger=None  # Suppress moviepy output
                )

                # Clean up
                for clip in clips:
                    clip.close()
                final_clip.close()

                job.output_video_path = output_path
                job.status = JobStatus.EXPORTED
                job.build_progress = 1.0

                if progress_callback:
                    progress_callback(job)

        except Exception as e:
            job.status = JobStatus.ERROR
            job.error_message = f"Video build failed: {str(e)}"
            if progress_callback:
                progress_callback(job)

    def cancel_build(self, job: HighlightJob):
        """Cancel an ongoing build"""
        job.should_cancel = True
```

---

### Phase 6: Application State

#### Step 6.1: State Manager (`core/state.py`)

```python
from qtpy.QtCore import QObject, Signal
from typing import List, Dict
from ..models.job import HighlightJob
from ..models.auth import AuthState

class AppState(QObject):
    """Centralized application state"""

    # Signals
    jobs_changed = Signal()
    auth_changed = Signal()
    toast_message = Signal(str, str)  # message, type

    def __init__(self):
        super().__init__()
        self.auth = AuthState()
        self.jobs: List[HighlightJob] = []
        self._jobs_dict: Dict[str, HighlightJob] = {}

    def add_job(self, job: HighlightJob):
        """Add a new job"""
        self.jobs.append(job)
        self._jobs_dict[job.id] = job
        self.jobs_changed.emit()

    def update_job(self, job: HighlightJob):
        """Update an existing job"""
        if job.id in self._jobs_dict:
            # Job is already in list, just emit change
            self.jobs_changed.emit()

    def remove_job(self, job_id: str):
        """Remove a job"""
        if job_id in self._jobs_dict:
            job = self._jobs_dict[job_id]
            self.jobs.remove(job)
            del self._jobs_dict[job_id]
            self.jobs_changed.emit()

    def get_job(self, job_id: str) -> HighlightJob:
        """Get job by ID"""
        return self._jobs_dict.get(job_id)

    def set_auth(self, auth: AuthState):
        """Update authentication state"""
        self.auth = auth
        self.auth_changed.emit()

    def show_toast(self, message: str, msg_type: str = "info"):
        """Show toast notification"""
        self.toast_message.emit(message, msg_type)
```

---

### Phase 7: UI Components

#### Step 7.1: Login Header (`ui/widgets/header.py`)

```python
from qtpy.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton
)
from qtpy.QtCore import Signal

class LoginHeader(QWidget):
    """Header with login form"""

    login_clicked = Signal(str, str, str)  # username, password, 2fa
    logout_clicked = Signal()

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)

        # Brand
        brand = QLabel("MyHighlights")
        brand.setObjectName("brand")
        layout.addWidget(brand)

        layout.addStretch()

        # Login form
        username_label = QLabel("Username")
        username_label.setObjectName("field-label")
        layout.addWidget(username_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setFixedWidth(150)
        layout.addWidget(self.username_input)

        password_label = QLabel("Password")
        password_label.setObjectName("field-label")
        layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedWidth(150)
        layout.addWidget(self.password_input)

        twofa_label = QLabel("2FA Code")
        twofa_label.setObjectName("field-label")
        layout.addWidget(twofa_label)

        self.twofa_input = QLineEdit()
        self.twofa_input.setPlaceholderText("000000")
        self.twofa_input.setFixedWidth(80)
        self.twofa_input.setMaxLength(6)
        layout.addWidget(self.twofa_input)

        # Buttons
        self.login_btn = QPushButton("Log In")
        self.login_btn.setObjectName("primary")
        self.login_btn.clicked.connect(self._on_login_clicked)
        layout.addWidget(self.login_btn)

        self.logout_btn = QPushButton("Log Out")
        self.logout_btn.setObjectName("secondary")
        self.logout_btn.clicked.connect(self.logout_clicked.emit)
        self.logout_btn.hide()
        layout.addWidget(self.logout_btn)

        # Status
        self.status_label = QLabel("Logged out")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

    def _on_login_clicked(self):
        username = self.username_input.text()
        password = self.password_input.text()
        twofa = self.twofa_input.text()

        if username and password:
            self.login_clicked.emit(username, password, twofa)

    def set_logged_in(self, logged_in: bool, username: str = ""):
        """Update UI for login state"""
        if logged_in:
            self.status_label.setText(f"Logged in as {username}")
            self.login_btn.hide()
            self.logout_btn.show()
            self.username_input.setEnabled(False)
            self.password_input.setEnabled(False)
            self.twofa_input.setEnabled(False)
        else:
            self.status_label.setText("Logged out")
            self.login_btn.show()
            self.logout_btn.hide()
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)
            self.twofa_input.setEnabled(True)
```

#### Step 7.2: Job Card (`ui/widgets/job_card.py`)

```python
from qtpy.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QProgressBar
)
from qtpy.QtCore import Signal
from ...models.job import HighlightJob, JobStatus

class JobCard(QWidget):
    """Highlight job card widget"""

    pause_clicked = Signal(str)
    resume_clicked = Signal(str)
    view_downloads_clicked = Signal(str)
    build_video_clicked = Signal(str)
    cancel_build_clicked = Signal(str)
    view_output_clicked = Signal(str)
    delete_clicked = Signal(str)
    open_folder_clicked = Signal(str)

    def __init__(self, job: HighlightJob):
        super().__init__()
        self.job = job
        self._setup_ui()
        self.update_from_job(job)

    def _setup_ui(self):
        self.setObjectName("job-card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Cover image
        self.cover_label = QLabel("Cover")
        self.cover_label.setObjectName("cover")
        self.cover_label.setFixedSize(80, 80)
        layout.addWidget(self.cover_label)

        # Info section
        info_layout = QVBoxLayout()

        self.title_label = QLabel()
        self.title_label.setObjectName("job-title")
        info_layout.addWidget(self.title_label)

        self.items_label = QLabel()
        self.items_label.setObjectName("job-subtitle")
        info_layout.addWidget(self.items_label)

        self.folder_label = QLabel()
        self.folder_label.setObjectName("job-subtitle")
        info_layout.addWidget(self.folder_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(4)
        self.progress_bar.hide()
        info_layout.addWidget(self.progress_bar)

        self.progress_text = QLabel()
        self.progress_text.setObjectName("progress-text")
        self.progress_text.hide()
        info_layout.addWidget(self.progress_text)

        layout.addLayout(info_layout, 1)

        # Status badge
        self.status_badge = QLabel()
        self.status_badge.setObjectName("status-badge")
        layout.addWidget(self.status_badge)

        # Actions
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setObjectName("action-btn")
        self.pause_btn.clicked.connect(lambda: self.pause_clicked.emit(self.job.id))
        layout.addWidget(self.pause_btn)

        self.resume_btn = QPushButton("Resume")
        self.resume_btn.setObjectName("action-btn")
        self.resume_btn.clicked.connect(lambda: self.resume_clicked.emit(self.job.id))
        layout.addWidget(self.resume_btn)

        self.view_downloads_btn = QPushButton("View Downloads")
        self.view_downloads_btn.setObjectName("action-btn")
        self.view_downloads_btn.clicked.connect(
            lambda: self.view_downloads_clicked.emit(self.job.id)
        )
        layout.addWidget(self.view_downloads_btn)

        self.build_btn = QPushButton("Build Video")
        self.build_btn.setObjectName("primary-btn")
        self.build_btn.clicked.connect(lambda: self.build_video_clicked.emit(self.job.id))
        layout.addWidget(self.build_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("action-btn")
        self.cancel_btn.clicked.connect(lambda: self.cancel_build_clicked.emit(self.job.id))
        layout.addWidget(self.cancel_btn)

        self.view_output_btn = QPushButton("View Output")
        self.view_output_btn.setObjectName("primary-btn")
        self.view_output_btn.clicked.connect(lambda: self.view_output_clicked.emit(self.job.id))
        layout.addWidget(self.view_output_btn)

        # Icons
        self.folder_btn = QPushButton("📁")
        self.folder_btn.setFixedSize(32, 32)
        self.folder_btn.clicked.connect(lambda: self.open_folder_clicked.emit(self.job.id))
        layout.addWidget(self.folder_btn)

        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setFixedSize(32, 32)
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.job.id))
        layout.addWidget(self.delete_btn)

    def update_from_job(self, job: HighlightJob):
        """Update UI from job state"""
        self.job = job

        self.title_label.setText(job.title)
        self.items_label.setText(f"Items: {job.downloaded_items}/{job.total_items}")
        self.folder_label.setText(f"Folder: .../{job.folder_path.name}/")

        # Update status badge
        status_map = {
            JobStatus.DOWNLOADING: "Downloading",
            JobStatus.PAUSED: "Paused",
            JobStatus.DOWNLOADED: "Downloaded",
            JobStatus.BUILDING: "Building",
            JobStatus.EXPORTED: "Exported",
            JobStatus.ERROR: "Error"
        }
        self.status_badge.setText(status_map.get(job.status, "Unknown"))

        # Show/hide progress
        if job.status == JobStatus.DOWNLOADING:
            self.progress_bar.show()
            self.progress_bar.setValue(int(job.download_progress * 100))
            self.progress_text.hide()
        elif job.status == JobStatus.BUILDING:
            self.progress_bar.show()
            self.progress_bar.setValue(int(job.build_progress * 100))
            self.progress_text.show()
            self.progress_text.setText(f"Building video... {int(job.build_progress * 100)}%")
        else:
            self.progress_bar.hide()
            self.progress_text.hide()

        # Show/hide buttons based on status
        self.pause_btn.setVisible(job.status == JobStatus.DOWNLOADING)
        self.resume_btn.setVisible(job.status == JobStatus.PAUSED)
        self.view_downloads_btn.setVisible(job.status in [
            JobStatus.DOWNLOADED, JobStatus.BUILDING, JobStatus.EXPORTED
        ])
        self.build_btn.setVisible(job.status == JobStatus.DOWNLOADED)
        self.cancel_btn.setVisible(job.status == JobStatus.BUILDING)
        self.view_output_btn.setVisible(job.status == JobStatus.EXPORTED)
```

---

## ⏭️ Continued in Next Steps...

This plan continues with:
- Phase 8: Main Window Implementation
- Phase 9: Styling (QSS)
- Phase 10: Integration & Testing
- Phase 11: Error Handling
- Phase 12: Session Persistence

Would you like me to:
1. **Continue with the remaining phases** of the plan?
2. **Start implementing** the code right away?
3. **Create a specific component** first (e.g., Instagram service)?
