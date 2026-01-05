"""Inline Progress Bar Widget"""
from qtpy.QtWidgets import QProgressBar
from qtpy.QtCore import Qt


class ProgressInline(QProgressBar):
    """Inline progress bar"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("progress-inline")
        self.setTextVisible(True)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setMaximumHeight(8)

    def set_progress(self, value: float):
        """Set progress (0.0 to 1.0)"""
        self.setValue(int(value * 100))
