"""Loading spinner widget with rotation animation"""
from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel
from qtpy.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from qtpy.QtGui import QPainter, QColor, QPen


class LoadingSpinner(QWidget):
    """Animated rotating spinner for loading states"""

    def __init__(self, text: str = "Loading...", size: int = 40):
        super().__init__()
        self.setObjectName("loading-spinner")
        self._angle = 0
        self._size = size
        self._setup_ui(text)
        self._setup_animation()

    def _setup_ui(self, text: str):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        # Spinner canvas
        self.spinner_widget = QWidget()
        self.spinner_widget.setFixedSize(self._size, self._size)
        layout.addWidget(self.spinner_widget, 0, Qt.AlignCenter)

        # Text label
        if text:
            self.text_label = QLabel(text)
            self.text_label.setObjectName("spinner-text")
            self.text_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.text_label)

    def _setup_animation(self):
        """Setup rotation animation"""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(50)  # Update every 50ms (20 FPS)

    def _rotate(self):
        """Rotate spinner"""
        self._angle = (self._angle + 10) % 360
        self.spinner_widget.update()

    def paintEvent(self, event):
        """Draw rotating spinner"""
        painter = QPainter(self.spinner_widget)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw spinning arc
        rect = self.spinner_widget.rect().adjusted(4, 4, -4, -4)

        # Spinner color (blue)
        pen = QPen(QColor("#2f81f7"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        # Draw arc (270 degrees)
        painter.drawArc(rect, self._angle * 16, 270 * 16)

    def set_text(self, text: str):
        """Update loading text"""
        if hasattr(self, 'text_label'):
            self.text_label.setText(text)

    def showEvent(self, event):
        """Start animation when shown"""
        super().showEvent(event)
        if hasattr(self, '_timer'):
            self._timer.start(50)

    def hideEvent(self, event):
        """Stop animation when hidden"""
        super().hideEvent(event)
        if hasattr(self, '_timer'):
            self._timer.stop()
