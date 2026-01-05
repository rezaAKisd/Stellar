"""Toast notification widget"""
from qtpy.QtWidgets import QLabel, QGraphicsOpacityEffect
from qtpy.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve


class ToastNotification(QLabel):
    """Toast notification matching wireframe design"""

    def __init__(self, message: str, msg_type: str = "info", parent=None):
        super().__init__(message, parent)
        self.setObjectName("toast")
        self.setProperty("type", msg_type)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(300)
        self.setMaximumWidth(500)
        self.setWordWrap(True)

        # Add checkmark for success
        if msg_type == "success":
            self.setText(f"✓ {message}")

        # Setup fade animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        # Auto-hide after 3 seconds with fade out
        QTimer.singleShot(2700, self._fade_out)

    def _fade_out(self):
        """Fade out animation"""
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()
