"""By Username tab widget"""
import asyncio
import logging
from typing import Optional

from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QScrollArea, QFrame
)
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QPixmap

from .image_loader import AsyncImageLabel
from .loading_spinner import LoadingSpinner
from .error_banner import ErrorBanner
from .progress_card import ProgressCard
from ...models.job import JobStatus

logger = logging.getLogger(__name__)


class HighlightCard(QFrame):
    """Card widget for a single highlight"""

    download_clicked = Signal(str, str, str)  # highlight_id, title, cover_url
    build_clicked = Signal(str)  # highlight_id
    view_output_clicked = Signal(str)  # highlight_id

    def __init__(self, highlight_data: dict):
        super().__init__()
        self.highlight_data = highlight_data
        self.highlight_id = highlight_data.get('id', '')
        self._current_status = None
        self.setObjectName("highlight-card")
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Cover image (using async loader)
        self.cover_label = AsyncImageLabel(placeholder_text="...", size=(80, 80))
        self.cover_label.setObjectName("highlight-cover")
        layout.addWidget(self.cover_label)

        # Load cover image
        cover_url = self.highlight_data.get('cover_url', '')
        if cover_url:
            self.cover_label.load_url(cover_url)

        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        title = QLabel(self.highlight_data.get('title', 'Untitled'))
        title.setObjectName("highlight-title")
        title.setWordWrap(True)
        info_layout.addWidget(title)

        count = QLabel(f"{self.highlight_data.get('item_count', 0)} items")
        count.setObjectName("highlight-count")
        info_layout.addWidget(count)

        self.status_label = QLabel("")
        self.status_label.setObjectName("highlight-status")
        self.status_label.hide()
        info_layout.addWidget(self.status_label)

        self.progress_card = ProgressCard(show_cancel=False)
        self.progress_card.hide()
        info_layout.addWidget(self.progress_card)

        info_layout.addStretch()
        layout.addLayout(info_layout, 1)

        # Action buttons
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)

        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("highlight-download-btn")
        self.download_btn.clicked.connect(self._on_download_clicked)
        actions_layout.addWidget(self.download_btn)

        self.build_btn = QPushButton("Build Video")
        self.build_btn.setObjectName("action-btn")
        self.build_btn.clicked.connect(self._on_build_clicked)
        self.build_btn.hide()
        actions_layout.addWidget(self.build_btn)

        self.view_output_btn = QPushButton("View Output")
        self.view_output_btn.setObjectName("view-output-btn")
        self.view_output_btn.clicked.connect(self._on_view_output_clicked)
        self.view_output_btn.hide()
        actions_layout.addWidget(self.view_output_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

    def _on_download_clicked(self):
        """Emit download signal"""
        self.download_clicked.emit(
            self.highlight_id,
            self.highlight_data.get('title', 'Untitled'),
            self.highlight_data.get('cover_url', '')
        )

    def _on_build_clicked(self):
        """Emit build signal"""
        self.build_clicked.emit(self.highlight_id)

    def _on_view_output_clicked(self):
        """Emit view output signal"""
        self.view_output_clicked.emit(self.highlight_id)

    def set_job_state(
        self,
        status: Optional[JobStatus],
        download_progress: float,
        build_progress: float,
        build_stage: str = ""
    ):
        """Update UI based on job status."""
        self._current_status = status

        if status is None:
            self.status_label.hide()
            self.progress_card.hide()
            self.download_btn.setText("Download")
            self.download_btn.setEnabled(True)
            self.build_btn.hide()
            self.view_output_btn.hide()
            return

        status_text_map = {
            JobStatus.PENDING: "Pending",
            JobStatus.DOWNLOADING: "Downloading",
            JobStatus.PAUSED: "Paused",
            JobStatus.DOWNLOADED: "Downloaded",
            JobStatus.BUILDING: "Building",
            JobStatus.BUILD_CANCELLED: "Cancelled",
            JobStatus.EXPORTED: "Exported",
            JobStatus.ERROR: "Error",
        }

        status_text = status_text_map.get(status, "Unknown")
        self.status_label.setText(status_text)
        self.status_label.show()

        self.download_btn.setEnabled(False)
        self.build_btn.hide()
        self.view_output_btn.hide()

        if status == JobStatus.DOWNLOADING:
            self.progress_card.update_all(download_progress, stage="Downloading...")
            self.progress_card.show()
            self.download_btn.setText("Downloading...")
        elif status == JobStatus.BUILDING:
            stage_text = build_stage or "Building video..."
            self.progress_card.update_all(build_progress, stage=stage_text)
            self.progress_card.show()
            self.download_btn.setText("Building...")
        elif status == JobStatus.DOWNLOADED:
            self.progress_card.hide()
            self.download_btn.setText("Downloaded")
            self.build_btn.show()
        elif status == JobStatus.EXPORTED:
            self.progress_card.hide()
            self.download_btn.setText("Exported")
            self.view_output_btn.show()
        elif status == JobStatus.ERROR:
            self.progress_card.hide()
            self.download_btn.setText("Retry Download")
            self.download_btn.setEnabled(True)
        else:
            self.progress_card.hide()
            self.download_btn.setText(status_text)


class ByUsernameTab(QWidget):
    """Tab for downloading highlights by Instagram username"""

    download_highlight = Signal(str, str, str)  # highlight_id, title, cover_url
    build_highlight = Signal(str)  # highlight_id
    view_output = Signal(str)  # highlight_id
    fetch_highlights = Signal(str)  # username

    def __init__(self):
        super().__init__()
        self.cards_by_id = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
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
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter Instagram username...")
        self.username_input.setObjectName("link-input")
        self.username_input.returnPressed.connect(self._on_fetch_clicked)
        input_row.addWidget(self.username_input)

        self.fetch_btn = QPushButton("Fetch Highlights")
        self.fetch_btn.setObjectName("add-download-btn")
        self.fetch_btn.clicked.connect(self._on_fetch_clicked)
        input_row.addWidget(self.fetch_btn)

        input_layout.addLayout(input_row)

        # Help text
        help_text = QLabel("Enter a username to view all their highlights.")
        help_text.setObjectName("help-text")
        input_layout.addWidget(help_text)

        layout.addWidget(input_card)

        # Highlights list section
        highlights_header = QLabel("Highlights")
        highlights_header.setObjectName("section-header")
        layout.addWidget(highlights_header)

        # Scroll area for highlights
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("jobs-scroll")

        self.highlights_container = QWidget()
        self.highlights_layout = QVBoxLayout(self.highlights_container)
        self.highlights_layout.setContentsMargins(0, 0, 0, 0)
        self.highlights_layout.setSpacing(15)
        self.highlights_layout.addStretch()

        scroll.setWidget(self.highlights_container)
        layout.addWidget(scroll)

        # Empty state
        self.empty_state = self._create_empty_state()
        self.highlights_layout.insertWidget(0, self.empty_state)

        # Loading spinner
        self.loading_spinner = LoadingSpinner("Fetching highlights...")
        self.loading_spinner.hide()
        self.highlights_layout.insertWidget(0, self.loading_spinner)

        # Error banner
        self.error_banner = ErrorBanner(show_retry=True)
        self.error_banner.retry_clicked.connect(self._on_retry_fetch)
        self.error_banner.hide()
        self.highlights_layout.insertWidget(0, self.error_banner)

    def _create_empty_state(self):
        """Create empty state widget"""
        empty = QWidget()
        empty.setObjectName("empty-state")
        layout = QVBoxLayout(empty)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        icon = QLabel("👤")
        icon.setObjectName("empty-icon")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("No highlights fetched yet")
        title.setObjectName("empty-title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        message = QLabel("Enter a username and click 'Fetch Highlights'.")
        message.setObjectName("empty-message")
        message.setAlignment(Qt.AlignCenter)
        layout.addWidget(message)

        return empty

    def _on_fetch_clicked(self):
        """Handle fetch button click"""
        username = self.username_input.text().strip()
        if not username:
            return

        # Store username for retry
        self.last_username = username

        # Emit signal to main window
        self.fetch_highlights.emit(username)

    def _on_retry_fetch(self):
        """Retry fetching highlights"""
        if hasattr(self, 'last_username') and self.last_username:
            self.fetch_highlights.emit(self.last_username)

    def set_loading(self, loading: bool):
        """Show/hide loading indicator"""
        if loading:
            self.loading_spinner.show()
            self.empty_state.hide()
            self.error_banner.hide()
            self.fetch_btn.setEnabled(False)
        else:
            self.loading_spinner.hide()
            self.fetch_btn.setEnabled(True)

    def set_error(self, error_message: str):
        """Show error banner"""
        self.error_banner.set_message(error_message)
        self.error_banner.show()
        self.empty_state.hide()
        self.loading_spinner.hide()
        self.fetch_btn.setEnabled(True)

    def set_highlights(self, highlights: list):
        """Display list of highlights"""
        # Hide error banner
        self.error_banner.hide()

        self.cards_by_id.clear()

        # Clear existing highlight cards
        while self.highlights_layout.count() > 1:  # Keep stretch
            item = self.highlights_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not highlights:
            self.empty_state.show()
            return

        self.empty_state.hide()

        # Add highlight cards
        for highlight_data in highlights:
            card = HighlightCard(highlight_data)
            card.download_clicked.connect(self.download_highlight.emit)
            card.build_clicked.connect(self.build_highlight.emit)
            card.view_output_clicked.connect(self.view_output.emit)
            self.cards_by_id[highlight_data.get("id", "")] = card
            self.highlights_layout.insertWidget(
                self.highlights_layout.count() - 1,  # Before stretch
                card
            )

    def update_highlight_job(self, highlight_id: str, job):
        """Update a highlight card with job progress/state."""
        card = self.cards_by_id.get(highlight_id)
        if not card:
            return
        card.set_job_state(job.status, job.download_progress, job.build_progress, job.build_stage)

    def clear_highlight_job(self, highlight_id: str):
        """Reset a highlight card to idle state."""
        card = self.cards_by_id.get(highlight_id)
        if not card:
            return
        card.set_job_state(None, 0.0, 0.0, "")
