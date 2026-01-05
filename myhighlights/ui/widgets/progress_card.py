"""Progress card widget with progress bar, speed, and ETA"""
from qtpy.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
from qtpy.QtCore import Qt, Signal


class ProgressCard(QFrame):
    """Reusable progress widget with progress bar, speed, ETA, and optional cancel"""

    cancel_clicked = Signal()

    def __init__(self, show_cancel: bool = False):
        super().__init__()
        self.setObjectName("progress-card")
        self._setup_ui(show_cancel)

    def _setup_ui(self, show_cancel: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("download-progress")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        # Info row: stage/status + speed + ETA
        info_layout = QHBoxLayout()
        info_layout.setSpacing(12)

        # Stage text (left)
        self.stage_label = QLabel("Starting...")
        self.stage_label.setObjectName("progress-stage")
        info_layout.addWidget(self.stage_label, 1)

        # Speed text (center)
        self.speed_label = QLabel("")
        self.speed_label.setObjectName("progress-speed")
        self.speed_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.speed_label)

        # ETA text (right)
        self.eta_label = QLabel("")
        self.eta_label.setObjectName("progress-eta")
        self.eta_label.setAlignment(Qt.AlignRight)
        info_layout.addWidget(self.eta_label)

        # Cancel button (optional)
        if show_cancel:
            self.cancel_btn = QPushButton("Cancel")
            self.cancel_btn.setObjectName("progress-cancel-btn")
            self.cancel_btn.clicked.connect(self.cancel_clicked.emit)
            info_layout.addWidget(self.cancel_btn)

        layout.addLayout(info_layout)

    def set_progress(self, percentage: float):
        """Set progress percentage (0-100)"""
        self.progress_bar.setValue(int(percentage * 100))

    def set_stage(self, stage: str):
        """Set stage/status text"""
        self.stage_label.setText(stage)

    def set_speed(self, speed_text: str):
        """Set speed text (e.g., '2.5 MB/s')"""
        self.speed_label.setText(speed_text)

    def set_eta(self, eta_text: str):
        """Set ETA text (e.g., '1m 23s remaining')"""
        self.eta_label.setText(eta_text)

    def update_all(self, percentage: float, stage: str = "", speed: str = "", eta: str = ""):
        """Update all fields at once"""
        self.set_progress(percentage)
        if stage:
            self.set_stage(stage)
        if speed:
            self.set_speed(speed)
        if eta:
            self.set_eta(eta)
