"""Highlight job card widget"""
from qtpy.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QProgressBar, QMessageBox
)
from qtpy.QtCore import Signal, Qt

from .progress_card import ProgressCard
from .image_loader import AsyncImageLabel
from .error_banner import ErrorBanner
from ...models.job import HighlightJob, JobStatus


class JobCard(QWidget):
    """Highlight job card widget matching wireframe design"""

    pause_clicked = Signal(str)  # job_id
    resume_clicked = Signal(str)
    view_downloads_clicked = Signal(str)
    build_video_clicked = Signal(str)
    cancel_build_clicked = Signal(str)
    view_output_clicked = Signal(str)
    retry_clicked = Signal(str)
    delete_clicked = Signal(str)
    open_folder_clicked = Signal(str)

    def __init__(self, job: HighlightJob):
        super().__init__()
        self.job = job
        self.setObjectName("job-card")
        self._setup_ui()
        self.update_from_job(job)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Cover image (using async loader)
        self.cover_label = AsyncImageLabel(placeholder_text="📷", size=(80, 80))
        self.cover_label.setObjectName("job-cover")
        layout.addWidget(self.cover_label)

        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        self.title_label = QLabel()
        self.title_label.setObjectName("job-title")
        info_layout.addWidget(self.title_label)

        self.items_label = QLabel()
        self.items_label.setObjectName("job-info")
        info_layout.addWidget(self.items_label)

        self.folder_label = QLabel()
        self.folder_label.setObjectName("job-info")
        info_layout.addWidget(self.folder_label)

        # Download progress card
        self.download_progress = ProgressCard(show_cancel=False)
        self.download_progress.hide()
        info_layout.addWidget(self.download_progress)

        # Build progress card
        self.build_progress = ProgressCard(show_cancel=True)
        self.build_progress.cancel_clicked.connect(
            lambda: self.cancel_build_clicked.emit(self.job.id)
        )
        self.build_progress.hide()
        info_layout.addWidget(self.build_progress)

        # Error banner
        self.error_banner = ErrorBanner(show_retry=True)
        self.error_banner.retry_clicked.connect(
            lambda: self.retry_clicked.emit(self.job.id)
        )
        self.error_banner.dismiss_clicked.connect(self.error_banner.hide)
        self.error_banner.hide()
        info_layout.addWidget(self.error_banner)

        layout.addLayout(info_layout, 1)

        # Status badge
        self.status_badge = QLabel()
        self.status_badge.setObjectName("status-badge")
        layout.addWidget(self.status_badge)

        # Action buttons
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setObjectName("action-btn")
        self.pause_btn.clicked.connect(lambda: self.pause_clicked.emit(self.job.id))
        layout.addWidget(self.pause_btn)

        self.view_downloads_btn = QPushButton("View Downloads")
        self.view_downloads_btn.setObjectName("action-btn")
        self.view_downloads_btn.clicked.connect(
            lambda: self.view_downloads_clicked.emit(self.job.id)
        )
        layout.addWidget(self.view_downloads_btn)

        self.build_btn = QPushButton("Build Video")
        self.build_btn.setObjectName("build-btn")
        self.build_btn.clicked.connect(lambda: self.build_video_clicked.emit(self.job.id))
        layout.addWidget(self.build_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("action-btn")
        self.cancel_btn.clicked.connect(lambda: self.cancel_build_clicked.emit(self.job.id))
        layout.addWidget(self.cancel_btn)

        self.view_output_btn = QPushButton("View Output")
        self.view_output_btn.setObjectName("view-output-btn")
        self.view_output_btn.clicked.connect(lambda: self.view_output_clicked.emit(self.job.id))
        layout.addWidget(self.view_output_btn)

        self.retry_btn = QPushButton("Retry")
        self.retry_btn.setObjectName("action-btn")
        self.retry_btn.clicked.connect(lambda: self.retry_clicked.emit(self.job.id))
        layout.addWidget(self.retry_btn)

        # Icon buttons
        self.folder_btn = QPushButton("📁")
        self.folder_btn.setObjectName("icon-btn")
        self.folder_btn.setFixedSize(36, 36)
        self.folder_btn.clicked.connect(lambda: self.open_folder_clicked.emit(self.job.id))
        layout.addWidget(self.folder_btn)

        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setObjectName("icon-btn")
        self.delete_btn.setFixedSize(36, 36)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self.delete_btn)

    def _on_delete_clicked(self):
        """Handle delete with confirmation"""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete job '{self.job.title}'?\n\nDownloaded files will be deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.delete_clicked.emit(self.job.id)

    def update_from_job(self, job: HighlightJob):
        """Update UI from job state"""
        self.job = job

        # Load cover image if available
        if job.cover_url:
            self.cover_label.load_url(job.cover_url)

        # Update labels
        self.title_label.setText(job.title)
        self.items_label.setText(f"Items: {job.downloaded_items}/{job.total_items}")

        if job.folder_path:
            folder_name = job.folder_path.name
            self.folder_label.setText(f"Folder: .../Highlights/{folder_name}/")
        else:
            self.folder_label.setText("Folder: Not set")

        # Update status badge
        status_text_map = {
            JobStatus.PENDING: "Pending",
            JobStatus.DOWNLOADING: "Downloading",
            JobStatus.PAUSED: "Paused",
            JobStatus.DOWNLOADED: "Downloaded",
            JobStatus.BUILDING: "Building",
            JobStatus.BUILD_CANCELLED: "Cancelled",
            JobStatus.EXPORTED: "Exported",
            JobStatus.ERROR: "Error"
        }
        status_text = status_text_map.get(job.status, "Unknown")
        self.status_badge.setText(status_text)
        self.status_badge.setProperty("status", job.status.value)

        # Refresh style
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

        # Hide all progress widgets by default
        self.download_progress.hide()
        self.build_progress.hide()
        self.error_banner.hide()

        # Show/hide and update progress based on status
        if job.status == JobStatus.DOWNLOADING:
            # Show download progress
            self.download_progress.show()
            stage = f"Downloading {job.current_item_index + 1}/{job.total_items}"
            speed_text = self._format_speed(job.download_speed)
            eta_text = self._format_eta(job.estimated_time_remaining)
            self.download_progress.update_all(
                percentage=job.download_progress,
                stage=stage,
                speed=speed_text,
                eta=eta_text
            )

        elif job.status == JobStatus.BUILDING:
            # Show build progress
            self.build_progress.show()
            stage = job.build_stage or "Building video..."
            self.build_progress.update_all(
                percentage=job.build_progress,
                stage=stage
            )

        elif job.status == JobStatus.ERROR:
            # Show error banner
            error_msg = job.error_message or "An error occurred"
            self.error_banner.set_message(error_msg)
            self.error_banner.show()

        # Show/hide buttons based on status
        self.pause_btn.setVisible(job.status == JobStatus.DOWNLOADING)
        self.view_downloads_btn.setVisible(job.status in [
            JobStatus.DOWNLOADED, JobStatus.BUILDING, JobStatus.EXPORTED, JobStatus.BUILD_CANCELLED
        ])
        self.build_btn.setVisible(job.status == JobStatus.DOWNLOADED)
        self.cancel_btn.setVisible(job.status == JobStatus.BUILDING)
        self.view_output_btn.setVisible(job.status == JobStatus.EXPORTED)
        self.retry_btn.setVisible(job.status == JobStatus.ERROR)

    def _format_speed(self, bytes_per_sec: float) -> str:
        """Format download speed for display"""
        if bytes_per_sec == 0:
            return ""

        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"

    def _format_eta(self, seconds: int) -> str:
        """Format estimated time remaining for display"""
        if seconds <= 0:
            return ""

        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
