"""Status Bar - Bottom status bar with connection status, downloads, and version"""
from qtpy.QtWidgets import QWidget, QHBoxLayout, QLabel
from qtpy.QtCore import Qt


class StatusBar(QWidget):
    """Bottom status bar: Online indicator, Active downloads, Version"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI layout"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(20)

        # Online indicator (colored dot)
        self.status_indicator = QLabel("\u25CF")  # Filled circle
        self.status_indicator.setObjectName("status-indicator")
        self.status_indicator.setStyleSheet("color: #86868b; font-size: 12px;")
        layout.addWidget(self.status_indicator)

        # Status text
        self.status_text = QLabel("Offline")
        self.status_text.setObjectName("status-text")
        self.status_text.setStyleSheet("font-size: 12px; color: #3a3a3c;")
        layout.addWidget(self.status_text)

        layout.addSpacing(20)

        # Active downloads count
        self.downloads_icon = QLabel("\U0001F4E5")  # Download icon
        self.downloads_icon.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.downloads_icon)

        self.downloads_label = QLabel("Active Downloads: 0")
        self.downloads_label.setObjectName("status-text")
        self.downloads_label.setStyleSheet("font-size: 12px; color: #3a3a3c;")
        layout.addWidget(self.downloads_label)

        layout.addStretch()

        # Version
        self.version_label = QLabel("v1.0.0")
        self.version_label.setObjectName("status-text")
        self.version_label.setStyleSheet("font-size: 12px; color: #86868b;")
        layout.addWidget(self.version_label)

    def update_status(self, is_online: bool, status_text: str):
        """
        Update online status.

        Args:
            is_online: Whether the connection is online
            status_text: Status text to display
        """
        self.status_text.setText(status_text)

        # Update indicator color
        color = "#34c759" if is_online else "#86868b"
        self.status_indicator.setStyleSheet(f"color: {color}; font-size: 12px;")

    def update_downloads(self, count: int):
        """
        Update active downloads count.

        Args:
            count: Number of active downloads
        """
        self.downloads_label.setText(f"Active Downloads: {count}")

    def set_version(self, version: str):
        """
        Set app version.

        Args:
            version: Version string
        """
        self.version_label.setText(f"v{version}")
