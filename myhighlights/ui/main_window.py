"""Main application window"""
import asyncio
import json
import logging
from pathlib import Path
import subprocess
import platform
import shutil

logger = logging.getLogger(__name__)

from qtpy.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QTabWidget, QScrollArea, QFrame
)
from qtpy.QtCore import Qt, QTimer

from .widgets.header import LoginHeader, LoginState
from .widgets.job_card import JobCard
from .widgets.toast import ToastNotification
from .widgets.by_username_tab import ByUsernameTab
from ..core.state import AppState
from ..core.config import Config
from ..services.instagram import InstagramService
from ..services.downloader import DownloadManager
from ..services.video_builder import VideoBuilder
from ..models.job import HighlightJob, HighlightItem, JobStatus
from ..models.auth import AuthState


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyHighlights")
        self.setMinimumSize(1300, 800)

        # Ensure directories exist
        Config.ensure_dirs()

        # Initialize state and services
        self.state = AppState()
        self.instagram = InstagramService(Config.SESSION_DIR)
        self.downloader = DownloadManager(self.instagram)
        self.video_builder = VideoBuilder()

        # Job cards cache
        self.job_cards = {}  # job_id -> JobCard widget
        self.username_job_map = {}  # highlight_id -> job_id

        # Setup UI
        self._setup_ui()
        self._connect_signals()
        self._load_stylesheet()

        # Debounced job persistence
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_jobs_to_disk)

        self._load_jobs_from_disk()

        # Schedule session restore after event loop starts
        QTimer.singleShot(100, lambda: asyncio.create_task(self._try_restore_session()))

    def _setup_ui(self):
        """Setup user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header = LoginHeader()
        layout.addWidget(self.header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("main-tabs")

        # Tab 1: By Highlight Link
        self.link_tab = self._create_link_tab()
        self.tabs.addTab(self.link_tab, "By Highlight Link")

        # Tab 2: By Username
        self.username_tab = ByUsernameTab()
        self.username_tab.download_highlight.connect(self._on_download_from_username)
        self.username_tab.build_highlight.connect(self._on_build_from_username)
        self.username_tab.view_output.connect(self._on_view_output_from_username)
        self.username_tab.fetch_highlights.connect(self._on_fetch_highlights)
        self.tabs.addTab(self.username_tab, "By Username")

        layout.addWidget(self.tabs)

        # Toast container (overlay)
        self.toast_container = QWidget(central_widget)
        self.toast_container.setObjectName("toast-container")
        self.toast_container.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.toast_layout = QVBoxLayout(self.toast_container)
        self.toast_layout.setContentsMargins(20, 20, 20, 20)
        self.toast_layout.setSpacing(10)
        self.toast_layout.addStretch()

        # Position toast container
        self.toast_container.setGeometry(
            self.width() - 350, 0, 330, self.height()
        )
        self.toast_container.raise_()

    def _create_link_tab(self):
        """Create the 'By Highlight Link' tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Input section
        input_card = QFrame()
        input_card.setObjectName("input-card")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(20, 20, 20, 20)
        input_layout.setSpacing(10)

        # Input row
        input_row = QHBoxLayout()
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Paste highlight link...")
        self.link_input.setObjectName("link-input")
        self.link_input.returnPressed.connect(self._on_add_download_clicked)
        input_row.addWidget(self.link_input)

        self.add_download_btn = QPushButton("Add & Download")
        self.add_download_btn.setObjectName("add-download-btn")
        self.add_download_btn.clicked.connect(self._on_add_download_clicked)
        input_row.addWidget(self.add_download_btn)

        input_layout.addLayout(input_row)

        # Help text
        help_text = QLabel("Download starts automatically after the link is validated.")
        help_text.setObjectName("help-text")
        input_layout.addWidget(help_text)

        layout.addWidget(input_card)

        # Jobs list section
        jobs_header = QLabel("Highlight Jobs")
        jobs_header.setObjectName("section-header")
        layout.addWidget(jobs_header)

        # Scroll area for jobs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("jobs-scroll")

        self.jobs_container = QWidget()
        self.jobs_layout = QVBoxLayout(self.jobs_container)
        self.jobs_layout.setContentsMargins(0, 0, 0, 0)
        self.jobs_layout.setSpacing(15)
        self.jobs_layout.addStretch()

        scroll.setWidget(self.jobs_container)
        layout.addWidget(scroll)

        # Empty state
        self.empty_state = self._create_empty_state()
        self.jobs_layout.insertWidget(0, self.empty_state)

        return tab

    def _create_empty_state(self):
        """Create empty state widget"""
        empty = QWidget()
        empty.setObjectName("empty-state")
        layout = QVBoxLayout(empty)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        icon = QLabel("🔗")
        icon.setObjectName("empty-icon")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("No highlights yet")
        title.setObjectName("empty-title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        message = QLabel("Paste a highlight link and click 'Add & Download'.")
        message.setObjectName("empty-message")
        message.setAlignment(Qt.AlignCenter)
        layout.addWidget(message)

        return empty

    def _connect_signals(self):
        """Connect signals"""
        import sys
        print("Connecting signals...", file=sys.stderr)
        logger.info("Connecting signals...")

        # Header signals
        self.header.login_clicked.connect(self._on_login)
        print("✓ login_clicked signal connected", file=sys.stderr)
        logger.info("✓ login_clicked signal connected")

        self.header.logout_clicked.connect(self._on_logout)
        print("✓ logout_clicked signal connected", file=sys.stderr)
        logger.info("✓ logout_clicked signal connected")

        # State signals
        self.state.jobs_changed.connect(self._on_jobs_changed)
        self.state.auth_changed.connect(self._on_auth_changed)
        self.state.toast_message.connect(self._show_toast)

        print("✓ All signals connected", file=sys.stderr)
        logger.info("✓ All signals connected")

    def _on_login(self, username: str, password: str, twofa: str):
        """Handle login"""
        import sys
        print("\n" + "=" * 60, file=sys.stderr)
        print("MAIN WINDOW: Login signal received", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        logger.info("-" * 60)
        logger.info("MAIN WINDOW: Login signal received")
        logger.info(f"Username: {username}")
        logger.info(f"Password length: {len(password)}")
        logger.info(f"2FA: {twofa if twofa else '(empty)'}")

        print(f"Username: {username}", file=sys.stderr)
        print(f"Password length: {len(password)}", file=sys.stderr)
        print(f"2FA: {twofa if twofa else '(empty)'}", file=sys.stderr)
        print("Creating async login task...", file=sys.stderr)

        logger.info("Creating async login task...")

        try:
            task = asyncio.create_task(self._login_async(username, password, twofa))
            print(f"✓ Async task created: {task}", file=sys.stderr)
            logger.info(f"✓ Async task created: {task}")
        except Exception as e:
            print(f"✗ Failed to create async task: {e}", file=sys.stderr)
            logger.error(f"✗ Failed to create async task: {e}", exc_info=True)
            import traceback
            traceback.print_exc()

    async def _login_async(self, username: str, password: str, twofa: str):
        """Async login"""
        import sys
        print("\n" + "=" * 60, file=sys.stderr)
        print("ASYNC LOGIN STARTED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        logger.info("=" * 60)
        logger.info("ASYNC LOGIN STARTED")
        logger.info("=" * 60)

        # Set loading state
        self.header.set_state(LoginState.LOGGING_IN)

        try:
            # Pass None if 2FA is empty
            twofa_code = twofa.strip() if twofa else None
            print(f"Prepared 2FA code: {twofa_code if twofa_code else '(None)'}", file=sys.stderr)
            logger.info(f"Prepared 2FA code: {twofa_code if twofa_code else '(None)'}")

            print("Calling Instagram service login...", file=sys.stderr)
            logger.info("Calling Instagram service login...")
            success, error = await self.instagram.login(username, password, twofa_code)
            print(f"Instagram login returned: success={success}, error={error}", file=sys.stderr)
            logger.info(f"Instagram login returned: success={success}, error={error}")

            if success:
                print("✓ Login successful!", file=sys.stderr)
                logger.info("✓ Login successful!")
                auth = AuthState(is_logged_in=True, username=username)
                self.state.set_auth(auth)
                self.header.set_state(LoginState.LOGGED_IN, username=username)
                self.state.show_toast("Login successful", "success")
                logger.info("UI updated with logged-in state")
            else:
                print(f"✗ Login failed: {error}", file=sys.stderr)
                logger.warning(f"✗ Login failed: {error}")
                if error == "2FA_REQUIRED":
                    logger.info("2FA required - prompting user")
                    self.header.set_state(LoginState.ERROR, error="2FA code required")
                    self.state.show_toast("Please enter 2FA code", "error")
                else:
                    logger.error(f"Login error: {error}")
                    self.header.set_state(LoginState.ERROR, error=error or "Login failed")
                    self.state.show_toast(error or "Login failed", "error")
        except Exception as e:
            print(f"✗ Exception during login: {e}", file=sys.stderr)
            logger.error(f"✗ Exception during login: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            self.header.set_state(LoginState.ERROR, error=f"Error: {str(e)}")
            self.state.show_toast(f"Login error: {str(e)}", "error")

    def _on_logout(self):
        """Handle logout"""
        asyncio.create_task(self._logout_async())

    async def _logout_async(self):
        """Async logout"""
        await self.instagram.logout()
        auth = AuthState(is_logged_in=False)
        self.state.set_auth(auth)
        self.header.set_state(LoginState.LOGGED_OUT)
        self.state.show_toast("Logged out", "info")

    async def _try_restore_session(self):
        """Try to restore previous session"""
        # Check if session file exists
        if Config.INSTAGRAM_SESSION_FILE.exists():
            success, data = await self.instagram.restore_session()
            if success:
                username = data or ""
                auth = AuthState(is_logged_in=True, username=username)
                self.state.set_auth(auth)
                self.header.set_state(LoginState.LOGGED_IN, username=username)
                self.state.show_toast("Session restored", "success")
            else:
                self.header.set_state(LoginState.LOGGED_OUT)

    def _on_add_download_clicked(self):
        """Handle Add & Download button"""
        url = self.link_input.text().strip()

        if not url:
            self.state.show_toast("Please enter a highlight link", "error")
            return

        if not self.instagram.is_logged_in():
            self.state.show_toast("Please login first", "error")
            return

        self.link_input.clear()
        self.add_download_btn.setEnabled(False)
        asyncio.create_task(self._add_and_download_async(url))

    async def _add_and_download_async(self, url: str):
        """Async add and download"""
        try:
            # Fetch highlight info
            info = await self.instagram.get_highlight_info(url)

            # Create job
            job_folder = self._build_job_folder(info['title'], info.get('id', ''))
            job = HighlightJob(
                title=info['title'],
                source_url=url,
                cover_url=info['cover_url'],
                folder_path=job_folder,
                items=[
                    HighlightItem(
                        url=item['url'],
                        type=item['type'],
                        thumbnail_url=item['thumbnail_url']
                    )
                    for item in info['items']
                ],
                total_items=info['total_items']
            )

            # Add to state
            self.state.add_job(job)
            self.state.show_toast("Download started", "info")

            # Start download
            await self.downloader.start_download(job, self._on_job_progress)

            if job.status == JobStatus.DOWNLOADED:
                self.state.show_toast("Download completed", "success")

        except Exception as e:
            self.state.show_toast(f"Error: {str(e)}", "error")
        finally:
            self.add_download_btn.setEnabled(True)

    def _on_job_progress(self, job: HighlightJob):
        """Handle job progress update"""
        self.state.update_job(job)
        self._update_username_tab_for_job(job)

    def _on_jobs_changed(self):
        """Handle jobs list change"""
        # Remove old cards
        for job_id, card in list(self.job_cards.items()):
            if job_id not in [j.id for j in self.state.jobs]:
                self.jobs_layout.removeWidget(card)
                card.deleteLater()
                del self.job_cards[job_id]

        # Show/hide empty state
        if self.state.jobs:
            self.empty_state.hide()
        else:
            self.empty_state.show()

        # Add or update cards
        for idx, job in enumerate(self.state.jobs):
            if job.id in self.job_cards:
                # Update existing card
                self.job_cards[job.id].update_from_job(job)
            else:
                # Create new card
                card = JobCard(job)
                card.pause_clicked.connect(self._on_pause_download)
                card.view_downloads_clicked.connect(self._on_view_downloads)
                card.build_video_clicked.connect(self._on_build_video)
                card.cancel_build_clicked.connect(self._on_cancel_build)
                card.view_output_clicked.connect(self._on_view_output)
                card.retry_clicked.connect(self._on_retry_download)
                card.delete_clicked.connect(self._on_delete_job)
                card.open_folder_clicked.connect(self._on_open_folder)

                self.jobs_layout.insertWidget(idx, card)
                self.job_cards[job.id] = card

        self._sync_username_tab_jobs()
        self._queue_save_jobs()

    def _get_username_highlight_id(self, job: HighlightJob) -> str | None:
        """Extract highlight id from username-tab jobs."""
        if not job.source_url:
            return None
        prefix = "username_tab_"
        if job.source_url.startswith(prefix):
            return job.source_url[len(prefix):]
        return None

    def _update_username_tab_for_job(self, job: HighlightJob):
        """Update username tab card for a job if it originated there."""
        if not hasattr(self, "username_tab"):
            return
        highlight_id = self._get_username_highlight_id(job)
        if not highlight_id:
            return
        self.username_job_map[highlight_id] = job.id
        self.username_tab.update_highlight_job(highlight_id, job)

    def _sync_username_tab_jobs(self):
        """Sync username tab cards with current jobs."""
        if not hasattr(self, "username_tab"):
            return
        self.username_job_map = {}
        for highlight_id in list(self.username_tab.cards_by_id.keys()):
            self.username_tab.clear_highlight_job(highlight_id)
        for job in self.state.jobs:
            highlight_id = self._get_username_highlight_id(job)
            if not highlight_id:
                continue
            self.username_job_map[highlight_id] = job.id
            self.username_tab.update_highlight_job(highlight_id, job)

    def _on_auth_changed(self):
        """Handle auth state change"""
        pass  # Already handled in login/logout

    def _on_pause_download(self, job_id: str):
        """Pause download"""
        job = self.state.get_job(job_id)
        if job:
            self.downloader.pause_download(job)
            self.state.show_toast("Download paused", "info")

    def _on_view_downloads(self, job_id: str):
        """Open downloads folder"""
        job = self.state.get_job(job_id)
        if job and job.downloads_folder:
            self._open_folder(job.downloads_folder)

    def _on_build_video(self, job_id: str):
        """Build video"""
        job = self.state.get_job(job_id)
        if job:
            asyncio.create_task(self._build_video_async(job))

    async def _build_video_async(self, job: HighlightJob):
        """Async build video"""
        self.state.show_toast("Building video...", "info")
        await self.video_builder.build_video(job, self._on_job_progress)

        if job.status == JobStatus.EXPORTED:
            self.state.show_toast("Video exported successfully", "success")
        elif job.status == JobStatus.ERROR:
            self.state.show_toast(f"Export failed: {job.error_message}", "error")

    def _on_cancel_build(self, job_id: str):
        """Cancel video build"""
        job = self.state.get_job(job_id)
        if job:
            self.video_builder.cancel_build(job)
            self.state.show_toast("Build cancelled", "info")

    def _on_view_output(self, job_id: str):
        """Open exports folder"""
        job = self.state.get_job(job_id)
        if job and job.exports_folder:
            self._open_folder(job.exports_folder)

    def _on_retry_download(self, job_id: str):
        """Retry a failed download"""
        job = self.state.get_job(job_id)
        if not job:
            return
        if not job.items:
            self.state.show_toast("No items to retry", "error")
            return
        job.should_pause = False
        job.should_cancel = False
        job.error_message = None
        asyncio.create_task(self.downloader.start_download(job, self._on_job_progress))

    def _on_build_from_username(self, highlight_id: str):
        """Build video for a username highlight."""
        job_id = self.username_job_map.get(highlight_id)
        if not job_id:
            self.state.show_toast("No downloaded highlight to build", "error")
            return
        self._on_build_video(job_id)

    def _on_view_output_from_username(self, highlight_id: str):
        """Open output folder for a username highlight."""
        job_id = self.username_job_map.get(highlight_id)
        if not job_id:
            self.state.show_toast("No exported video found", "error")
            return
        self._on_view_output(job_id)

    def _on_delete_job(self, job_id: str):
        """Delete job"""
        job = self.state.get_job(job_id)
        if not job:
            return

        job.should_pause = True
        job.should_cancel = True

        folder_path = job.folder_path
        if folder_path and folder_path.exists():
            try:
                base_dir = Config.HIGHLIGHTS_DIR.resolve()
                target_dir = folder_path.resolve()
                if base_dir in target_dir.parents:
                    shutil.rmtree(target_dir)
                else:
                    self.state.show_toast("Refusing to delete unknown folder", "error")
            except Exception as e:
                self.state.show_toast(f"Failed to delete files: {e}", "error")

        self.state.remove_job(job_id)
        self.state.show_toast("Job and files deleted", "info")

    def _build_job_folder(self, title: str, highlight_id: str) -> Path:
        """Create a per-highlight folder path based on the title."""
        safe_title = "".join(
            c for c in (title or "") if c.isalnum() or c in (' ', '_')
        ).strip()
        safe_title = safe_title.replace(' ', '_') if safe_title else "highlight"

        base_path = Config.HIGHLIGHTS_DIR / safe_title
        if not base_path.exists():
            return base_path

        id_suffix = "".join(c for c in str(highlight_id) if c.isdigit())
        if id_suffix:
            candidate = Config.HIGHLIGHTS_DIR / f"{safe_title}_{id_suffix}"
            if not candidate.exists():
                return candidate

        for idx in range(2, 1000):
            candidate = Config.HIGHLIGHTS_DIR / f"{safe_title}_{idx}"
            if not candidate.exists():
                return candidate

        return base_path

    def _on_open_folder(self, job_id: str):
        """Open job folder"""
        job = self.state.get_job(job_id)
        if job and job.folder_path:
            self._open_folder(job.folder_path)

    def _open_folder(self, path: Path):
        """Open folder in file explorer"""
        try:
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(path)])
            elif system == "Windows":
                subprocess.run(["explorer", str(path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(path)])
        except Exception as e:
            self.state.show_toast(f"Failed to open folder: {e}", "error")

    def _show_toast(self, message: str, msg_type: str):
        """Show toast notification"""
        toast = ToastNotification(message, msg_type, self)
        self.toast_layout.insertWidget(self.toast_layout.count() - 1, toast)

    def _load_stylesheet(self):
        """Load QSS stylesheet"""
        try:
            qss_path = Path(__file__).parent / "styles.qss"
            if qss_path.exists():
                with open(qss_path, 'r') as f:
                    self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Failed to load stylesheet: {e}")

    def _queue_save_jobs(self):
        """Debounce job persistence to disk."""
        if self._save_timer.isActive():
            self._save_timer.stop()
        self._save_timer.start(800)

    def _save_jobs_to_disk(self):
        """Persist jobs to disk for restore on next launch."""
        try:
            if not self.state.jobs:
                if Config.JOBS_FILE.exists():
                    Config.JOBS_FILE.unlink()
                return
            data = [job.to_dict() for job in self.state.jobs]
            Config.JOBS_FILE.write_text(
                json.dumps(data, ensure_ascii=True, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Failed to save jobs: {e}")

    def _load_jobs_from_disk(self):
        """Restore jobs from disk on startup."""
        if not Config.JOBS_FILE.exists():
            return
        try:
            raw = json.loads(Config.JOBS_FILE.read_text(encoding="utf-8"))
            jobs = []
            for item in raw:
                job = HighlightJob.from_dict(item)
                self._rehydrate_job(job)
                jobs.append(job)
            self.state.set_jobs(jobs)
        except Exception as e:
            logger.warning(f"Failed to load jobs: {e}")

    def _rehydrate_job(self, job: HighlightJob):
        """Fix paths and status for restored jobs."""
        if job.folder_path:
            job.downloads_folder = job.folder_path / "downloads"
            job.exports_folder = job.folder_path
        else:
            job.status = JobStatus.ERROR
            job.error_message = "Job folder missing"
            return

        downloaded_items = 0
        for item in job.items:
            if item.local_path and Path(item.local_path).exists():
                item.downloaded = True
                downloaded_items += 1
            else:
                item.downloaded = False

        total_items = len(job.items) or job.total_items
        job.total_items = total_items
        job.downloaded_items = downloaded_items
        job.download_progress = (downloaded_items / total_items) if total_items else 0.0

        output_path = job.folder_path / "final_video.mp4"
        if output_path.exists():
            job.output_video_path = output_path
            job.status = JobStatus.EXPORTED
            job.build_progress = 1.0
            return

        if total_items > 0 and downloaded_items == total_items:
            job.status = JobStatus.DOWNLOADED
            job.error_message = None
        elif downloaded_items > 0:
            job.status = JobStatus.ERROR
            job.error_message = job.error_message or "Incomplete download, please retry"
        else:
            job.status = JobStatus.PENDING

    def _on_fetch_highlights(self, username: str):
        """Handle fetch highlights request"""
        if not self.instagram.is_logged_in():
            self.state.show_toast("Please login first", "error")
            return

        asyncio.create_task(self._fetch_highlights_async(username))

    async def _fetch_highlights_async(self, username: str):
        """Async fetch highlights for username"""
        try:
            self.username_tab.set_loading(True)

            # Fetch highlights from Instagram
            highlights = await self.instagram.get_user_highlights(username)

            # Display highlights in tab
            self.username_tab.set_highlights(highlights)
            self.username_tab.set_loading(False)
            self._sync_username_tab_jobs()

            if highlights:
                self.state.show_toast(f"Found {len(highlights)} highlights", "success")
            else:
                self.state.show_toast(f"No highlights found for @{username}", "info")

        except Exception as e:
            # Show error in tab with retry button
            error_msg = str(e)
            self.username_tab.set_error(error_msg)
            self.state.show_toast(f"Error: {error_msg}", "error")
            logger.error(f"Failed to fetch highlights: {e}", exc_info=True)

    def _on_download_from_username(self, highlight_id: str, title: str, cover_url: str):
        """Handle download request from By Username tab"""
        if not self.instagram.is_logged_in():
            self.state.show_toast("Please login first", "error")
            return

        existing_job_id = self.username_job_map.get(highlight_id)
        existing_job = self.state.get_job(existing_job_id) if existing_job_id else None
        if existing_job_id and not existing_job:
            self.username_job_map.pop(highlight_id, None)

        if not existing_job:
            for job in self.state.jobs:
                if self._get_username_highlight_id(job) == highlight_id:
                    existing_job = job
                    self.username_job_map[highlight_id] = job.id
                    break

        if existing_job:
            if existing_job.status == JobStatus.ERROR:
                self._on_retry_download(existing_job.id)
                return
            if existing_job.status in (JobStatus.DOWNLOADING, JobStatus.BUILDING):
                self.state.show_toast("Job already in progress", "info")
                return
            if existing_job.status in (JobStatus.DOWNLOADED, JobStatus.EXPORTED):
                self.state.show_toast("Highlight already downloaded", "info")
                return
            self._on_retry_download(existing_job.id)
            return

        asyncio.create_task(self._download_from_username_async(highlight_id, title, cover_url))

    async def _download_from_username_async(self, highlight_id: str, title: str, cover_url: str):
        """Async download from username tab"""
        try:
            # Fetch full highlight info by ID
            info = await self.instagram.get_highlight_info_by_id(highlight_id)

            # Create job (reuse existing pipeline)
            job_folder = self._build_job_folder(info['title'], info.get('id', ''))
            job = HighlightJob(
                title=info['title'],
                source_url=f"username_tab_{highlight_id}",  # Placeholder URL
                cover_url=info['cover_url'],
                folder_path=job_folder,
                items=[
                    HighlightItem(
                        url=item['url'],
                        type=item['type'],
                        thumbnail_url=item['thumbnail_url']
                    )
                    for item in info['items']
                ],
                total_items=info['total_items']
            )

            # Add to state
            self.state.add_job(job)
            self.username_job_map[highlight_id] = job.id
            self._update_username_tab_for_job(job)
            self.state.show_toast(f"Downloading '{info['title']}'", "info")

            # Start download (reuse existing downloader)
            await self.downloader.start_download(job, self._on_job_progress)

            if job.status == JobStatus.DOWNLOADED:
                self.state.show_toast(f"'{info['title']}' downloaded", "success")

        except Exception as e:
            self.state.show_toast(f"Error: {str(e)}", "error")
            logger.error(f"Failed to download from username tab: {e}", exc_info=True)

    def resizeEvent(self, event):
        """Handle resize to reposition toast container"""
        super().resizeEvent(event)
        if hasattr(self, 'toast_container'):
            self.toast_container.setGeometry(
                self.width() - 350, 0, 330, self.height()
            )
