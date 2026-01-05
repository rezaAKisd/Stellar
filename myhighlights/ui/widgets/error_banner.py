"""Error banner widget with message and retry button"""
from qtpy.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from qtpy.QtCore import Qt, Signal


class ErrorBanner(QFrame):
    """Error banner with icon, message, and action buttons"""

    retry_clicked = Signal()
    dismiss_clicked = Signal()

    def __init__(self, message: str = "", show_retry: bool = True, show_dismiss: bool = False):
        super().__init__()
        self.setObjectName("error-banner")
        self._setup_ui(message, show_retry, show_dismiss)

    def _setup_ui(self, message: str, show_retry: bool, show_dismiss: bool):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(12)

        # Error icon
        icon_label = QLabel("⚠️")
        icon_label.setObjectName("error-icon")
        layout.addWidget(icon_label)

        # Error message
        self.message_label = QLabel(message)
        self.message_label.setObjectName("error-message")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label, 1)

        # Retry button
        if show_retry:
            self.retry_btn = QPushButton("Retry")
            self.retry_btn.setObjectName("error-retry-btn")
            self.retry_btn.clicked.connect(self.retry_clicked.emit)
            layout.addWidget(self.retry_btn)

        # Dismiss button
        if show_dismiss:
            self.dismiss_btn = QPushButton("✕")
            self.dismiss_btn.setObjectName("error-dismiss-btn")
            self.dismiss_btn.setFixedSize(24, 24)
            self.dismiss_btn.clicked.connect(self.dismiss_clicked.emit)
            layout.addWidget(self.dismiss_btn)

    def set_message(self, message: str):
        """Update error message"""
        self.message_label.setText(message)
