"""Empty State Widget"""
from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel
from qtpy.QtCore import Qt


class EmptyState(QWidget):
    """Empty state placeholder"""

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self._setup_ui(title, message)

    def _setup_ui(self, title: str, message: str):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("empty-title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        message_label = QLabel(message)
        message_label.setObjectName("empty-message")
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
