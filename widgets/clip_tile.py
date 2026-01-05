from qtpy import QtCore, QtGui, QtWidgets

from widgets.status_pill import StatusPill


class ClipTile(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ClipTile")
        self.thumbnail = QtWidgets.QLabel()
        self.thumbnail.setFixedSize(120, 76)
        self.thumbnail.setObjectName("ClipThumb")
        self.thumbnail.setAlignment(QtCore.Qt.AlignCenter)
        self.thumbnail.setPixmap(self._placeholder_pixmap())

        self.title_label = QtWidgets.QLabel("Clip")
        self.title_label.setObjectName("CardTitle")
        self.meta_label = QtWidgets.QLabel("Video")
        self.meta_label.setObjectName("Muted")

        self.status_pill = StatusPill("waiting", "neutral")
        self.duration_label = QtWidgets.QLabel("")
        self.duration_label.setObjectName("Muted")

        title_layout = QtWidgets.QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.meta_label)

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.thumbnail)
        top_layout.addLayout(title_layout)

        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(self.status_pill)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.duration_label)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(top_layout)
        layout.addLayout(bottom_layout)

    def set_data(self, title: str, media_type: str, status: str, tone: str, duration: str) -> None:
        self.title_label.setText(title)
        self.meta_label.setText(media_type)
        self.status_pill.set_text(status, tone)
        self.duration_label.setText(duration)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    @staticmethod
    def _placeholder_pixmap() -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(120, 76)
        pixmap.fill(QtGui.QColor("#E5E9F2"))
        return pixmap
