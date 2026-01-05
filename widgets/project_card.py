from qtpy import QtCore, QtGui, QtWidgets

from widgets.status_pill import StatusPill


class ProjectCard(QtWidgets.QFrame):
    clicked = QtCore.Signal(str)

    def __init__(self, project_id: str, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setObjectName("ProjectCard")
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.cover = QtWidgets.QLabel()
        self.cover.setFixedSize(72, 72)
        self.cover.setObjectName("ProjectCover")
        self.cover.setAlignment(QtCore.Qt.AlignCenter)
        self.cover.setPixmap(self._placeholder_pixmap())

        self.title_label = QtWidgets.QLabel("Untitled Project")
        self.title_label.setObjectName("CardTitle")
        self.meta_label = QtWidgets.QLabel("0 items")
        self.meta_label.setObjectName("Muted")

        self.status_pill = StatusPill("Draft", "neutral")
        self.updated_label = QtWidgets.QLabel("Just now")
        self.updated_label.setObjectName("Muted")

        info_layout = QtWidgets.QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.meta_label)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.status_pill)
        right_layout.addStretch()
        right_layout.addWidget(self.updated_label)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(self.cover)
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addLayout(right_layout)

    def set_data(self, title: str, item_count: int, status: str, status_tone: str, updated: str) -> None:
        self.title_label.setText(title)
        self.meta_label.setText(f"{item_count} items")
        self.status_pill.set_text(status, status_tone)
        self.updated_label.setText(updated)

    def mousePressEvent(self, event):
        self.clicked.emit(self.project_id)
        super().mousePressEvent(event)

    @staticmethod
    def _placeholder_pixmap() -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(72, 72)
        pixmap.fill(QtGui.QColor("#E9ECF2"))
        return pixmap
