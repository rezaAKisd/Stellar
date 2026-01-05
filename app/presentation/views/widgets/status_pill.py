"""Status Pill Widget"""
from qtpy.QtWidgets import QLabel, QHBoxLayout, QWidget
from qtpy.QtCore import Qt


class StatusPill(QWidget):
    """Colored status pill widget"""

    def __init__(self, text: str = "", color: str = "gray", parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.set_status(text, color)

    def _setup_ui(self):
        """Setup UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel()
        self.label.setObjectName("status-pill")
        layout.addWidget(self.label)

    def set_status(self, text: str, color: str):
        """Update status text and color"""
        self.label.setText(text)
        self.label.setProperty("color", color)
        self.label.style().unpolish(self.label)
        self.label.style().polish(self.label)
