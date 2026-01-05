"""User Detail Page - Shows highlights for a username"""
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QMessageBox
)
from qtpy.QtCore import Qt, Signal

from ..widgets.status_pill import StatusPill
from ..widgets.progress_inline import ProgressInline
from ...viewmodels.user_detail_vm import UserDetailViewModel
from ...models_ui import UserHighlightCardState


class HighlightCard(QWidget):
    """Card widget for a single highlight"""

    download_clicked = Signal(object)  # UserHighlightCardState
    view_downloads_clicked = Signal(object)
    build_video_clicked = Signal(object)
    view_exports_clicked = Signal(object)

    def __init__(self, state: UserHighlightCardState, parent=None):
        super().__init__(parent)
        self.state = state
        self._setup_ui()
        self.update_state(state)

    def _setup_ui(self):
        """Setup UI"""
        self.setObjectName("highlight-card")
        self.setFixedWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Cover thumbnail
        self.cover_label = QLabel("IMG")
        self.cover_label.setObjectName("card-cover")
        self.cover_label.setFixedHeight(150)
        self.cover_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.cover_label)

        # Name
        self.name_label = QLabel()
        self.name_label.setObjectName("card-title")
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)

        # Item count
        self.count_label = QLabel()
        self.count_label.setObjectName("card-subtitle")
        layout.addWidget(self.count_label)

        # Status
        self.status_pill = StatusPill()
        layout.addWidget(self.status_pill)

        # Progress
        self.progress_bar = ProgressInline()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Actions
        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("primary")
        self.download_btn.clicked.connect(lambda: self.download_clicked.emit(self.state))
        layout.addWidget(self.download_btn)

        self.view_downloads_btn = QPushButton("View Downloads")
        self.view_downloads_btn.setObjectName("secondary")
        self.view_downloads_btn.clicked.connect(lambda: self.view_downloads_clicked.emit(self.state))
        layout.addWidget(self.view_downloads_btn)

        self.build_btn = QPushButton("Build Video")
        self.build_btn.setObjectName("secondary")
        self.build_btn.clicked.connect(lambda: self.build_video_clicked.emit(self.state))
        layout.addWidget(self.build_btn)

        self.view_exports_btn = QPushButton("View Exports")
        self.view_exports_btn.setObjectName("secondary")
        self.view_exports_btn.clicked.connect(lambda: self.view_exports_clicked.emit(self.state))
        layout.addWidget(self.view_exports_btn)

    def update_state(self, state: UserHighlightCardState):
        """Update card from state"""
        self.state = state

        self.name_label.setText(state.name)
        self.count_label.setText(f"{state.item_count} items")

        # Status color
        color_map = {
            "Idle": "gray",
            "Downloading": "blue",
            "Downloaded": "green",
            "Building": "orange",
            "Exported": "purple",
            "Error": "red"
        }
        self.status_pill.set_status(state.status_text, color_map.get(state.status_text, "gray"))

        # Progress
        if state.is_busy:
            self.progress_bar.show()
            progress = state.download_progress if state.status_text == "Downloading" else state.export_progress
            self.progress_bar.set_progress(progress)
        else:
            self.progress_bar.hide()

        # Button states
        self.download_btn.setVisible(state.can_download)
        self.download_btn.setEnabled(not state.is_busy)
        self.view_downloads_btn.setVisible(state.has_downloads)
        self.build_btn.setVisible(state.can_build_video)
        self.build_btn.setEnabled(not state.is_busy)
        self.view_exports_btn.setVisible(state.has_exports)


class UserDetailPage(QWidget):
    """Page showing highlights for a specific user"""

    back_clicked = Signal()

    def __init__(self, viewmodel: UserDetailViewModel, parent=None):
        super().__init__(parent)
        self.vm = viewmodel
        self.cards = []
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        self.back_btn = QPushButton("← Users")
        self.back_btn.setObjectName("secondary")
        self.back_btn.clicked.connect(self.back_clicked.emit)
        header_layout.addWidget(self.back_btn)

        header_layout.addStretch()

        self.username_label = QLabel()
        self.username_label.setObjectName("page-title")
        header_layout.addWidget(self.username_label)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Subtitle
        self.subtitle_label = QLabel("Highlights")
        self.subtitle_label.setObjectName("page-subtitle")
        layout.addWidget(self.subtitle_label)

        # Scroll area for cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(15)

        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area)

        # Loading label
        self.loading_label = QLabel("Loading highlights...")
        self.loading_label.setObjectName("empty-message")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.hide()
        layout.addWidget(self.loading_label)

    def _connect_signals(self):
        """Connect ViewModel signals"""
        self.vm.detail_changed.connect(self._on_detail_changed)

    def _on_detail_changed(self, detail_state):
        """Handle detail state change"""
        self.username_label.setText(f"@{detail_state.username}")

        # Show/hide loading
        if detail_state.is_loading:
            self.loading_label.show()
            self.scroll_area.hide()
        else:
            self.loading_label.hide()
            self.scroll_area.show()

        # Update cards
        self._update_cards(detail_state.highlights)

    def _update_cards(self, highlights):
        """Update highlight cards grid"""
        # Remove old cards
        for card in self.cards:
            self.grid_layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()

        # Create new cards
        columns = 3
        for idx, highlight_state in enumerate(highlights):
            card = HighlightCard(highlight_state)
            card.download_clicked.connect(self._on_download_clicked)
            card.view_downloads_clicked.connect(lambda c: self.vm.view_downloads(c))
            card.build_video_clicked.connect(lambda c: self.vm.build_video(c))
            card.view_exports_clicked.connect(lambda c: self.vm.view_exports(c))

            row = idx // columns
            col = idx % columns
            self.grid_layout.addWidget(card, row, col)
            self.cards.append(card)

    def _on_download_clicked(self, card_state):
        """Handle download button click"""
        username = self.vm.store.state.user_detail.username
        self.vm.download_highlight(username, card_state)

    def show_user(self, username: str):
        """Show highlights for a user"""
        self.vm.load_highlights(username)
