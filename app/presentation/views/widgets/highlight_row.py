"""Highlight Row Widget for link tab"""
from qtpy.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QMessageBox
)
from qtpy.QtCore import Signal, Qt

from .status_pill import StatusPill
from .progress_inline import ProgressInline
from ...models_ui import HighlightRowState


class HighlightRow(QWidget):
    """Row widget for a highlight project"""

    build_video_clicked = Signal(str)  # project_id
    view_exports_clicked = Signal(str)
    view_downloads_clicked = Signal(str)
    open_folder_clicked = Signal(str)
    remove_clicked = Signal(str)
    retry_clicked = Signal(str)

    def __init__(self, state: HighlightRowState, parent=None):
        super().__init__(parent)
        self.state = state
        self._setup_ui()
        self.update_state(state)

    def _setup_ui(self):
        """Setup UI"""
        self.setObjectName("highlight-row")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        # Thumbnail placeholder
        thumb = QLabel("IMG")
        thumb.setObjectName("thumbnail")
        thumb.setFixedSize(60, 60)
        thumb.setAlignment(Qt.AlignCenter)
        layout.addWidget(thumb)

        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        self.title_label = QLabel()
        self.title_label.setObjectName("row-title")
        info_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("row-subtitle")
        info_layout.addWidget(self.subtitle_label)

        layout.addLayout(info_layout, 1)

        # Status section
        status_layout = QVBoxLayout()
        status_layout.setSpacing(5)

        self.status_pill = StatusPill()
        status_layout.addWidget(self.status_pill)

        self.progress_bar = ProgressInline()
        self.progress_bar.hide()
        status_layout.addWidget(self.progress_bar)

        layout.addLayout(status_layout)

        # Actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        self.build_btn = QPushButton("Build Video")
        self.build_btn.setObjectName("secondary")
        self.build_btn.clicked.connect(lambda: self.build_video_clicked.emit(self.state.id))
        actions_layout.addWidget(self.build_btn)

        self.view_exports_btn = QPushButton("View Exports")
        self.view_exports_btn.setObjectName("secondary")
        self.view_exports_btn.clicked.connect(lambda: self.view_exports_clicked.emit(self.state.id))
        actions_layout.addWidget(self.view_exports_btn)

        self.view_downloads_btn = QPushButton("Open Folder")
        self.view_downloads_btn.setObjectName("secondary")
        self.view_downloads_btn.clicked.connect(lambda: self.view_downloads_clicked.emit(self.state.id))
        actions_layout.addWidget(self.view_downloads_btn)

        self.retry_btn = QPushButton("Retry")
        self.retry_btn.setObjectName("secondary")
        self.retry_btn.clicked.connect(lambda: self.retry_clicked.emit(self.state.id))
        self.retry_btn.hide()
        actions_layout.addWidget(self.retry_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setObjectName("danger")
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        actions_layout.addWidget(self.remove_btn)

        layout.addLayout(actions_layout)

    def _on_remove_clicked(self):
        """Handle remove with confirmation"""
        reply = QMessageBox.question(
            self,
            "Confirm Remove",
            f"Remove '{self.state.title}'?\n\nFiles will not be deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.remove_clicked.emit(self.state.id)

    def update_state(self, state: HighlightRowState):
        """Update widget from state"""
        self.state = state

        self.title_label.setText(state.title)
        self.subtitle_label.setText(f"Items: {state.item_count}")

        # Status color mapping
        color_map = {
            "Idle": "gray",
            "Downloading": "blue",
            "Downloaded": "green",
            "Building": "orange",
            "Exported": "purple",
            "Error": "red"
        }
        self.status_pill.set_status(state.status_text, color_map.get(state.status_text, "gray"))

        # Progress visibility
        if state.is_busy:
            self.progress_bar.show()
            progress = state.download_progress if state.status_text == "Downloading" else state.export_progress
            self.progress_bar.set_progress(progress)
        else:
            self.progress_bar.hide()

        # Button states
        self.build_btn.setEnabled(state.can_build_video and not state.is_busy)
        self.view_exports_btn.setEnabled(state.has_exports)
        self.view_downloads_btn.setEnabled(state.has_downloads)

        if state.can_retry:
            self.retry_btn.show()
            self.build_btn.hide()
        else:
            self.retry_btn.hide()
            self.build_btn.show()
