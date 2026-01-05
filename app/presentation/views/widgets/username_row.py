"""Username Row Widget"""
from qtpy.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QMessageBox
from qtpy.QtCore import Signal, Qt

from ...models_ui import UserRowState


class UsernameRow(QWidget):
    """Row widget for a username"""

    open_clicked = Signal(str)  # username
    remove_clicked = Signal(str)  # user_id

    def __init__(self, state: UserRowState, parent=None):
        super().__init__(parent)
        self.state = state
        self._setup_ui()
        self.update_state(state)

    def _setup_ui(self):
        """Setup UI"""
        self.setObjectName("username-row")
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        # Avatar placeholder
        avatar = QLabel("👤")
        avatar.setObjectName("avatar")
        avatar.setFixedSize(50, 50)
        avatar.setAlignment(Qt.AlignCenter)
        layout.addWidget(avatar)

        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)

        self.username_label = QLabel()
        self.username_label.setObjectName("row-title")
        info_layout.addWidget(self.username_label)

        self.metadata_label = QLabel()
        self.metadata_label.setObjectName("row-subtitle")
        info_layout.addWidget(self.metadata_label)

        layout.addLayout(info_layout, 1)

        # Actions
        self.open_btn = QPushButton("Open")
        self.open_btn.setObjectName("primary")
        self.open_btn.clicked.connect(lambda: self.open_clicked.emit(self.state.username))
        layout.addWidget(self.open_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setObjectName("danger")
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        layout.addWidget(self.remove_btn)

    def _on_remove_clicked(self):
        """Handle remove with confirmation"""
        reply = QMessageBox.question(
            self,
            "Confirm Remove",
            f"Remove user '@{self.state.username}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.remove_clicked.emit(self.state.id)

    def update_state(self, state: UserRowState):
        """Update widget from state"""
        self.state = state
        self.username_label.setText(f"@{state.username}")
        self.metadata_label.setText(state.metadata_text)

    def mousePressEvent(self, event):
        """Handle row click"""
        if event.button() == Qt.LeftButton:
            self.open_clicked.emit(self.state.username)
        super().mousePressEvent(event)
