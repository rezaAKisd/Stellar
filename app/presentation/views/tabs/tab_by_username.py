"""By Username Tab"""
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QScrollArea, QFrame
)
from qtpy.QtCore import Qt

from ..widgets.empty_state import EmptyState
from ..widgets.username_row import UsernameRow
from ...viewmodels.username_tab_vm import UsernameTabViewModel


class TabByUsername(QWidget):
    """Tab for adding users by username"""

    def __init__(self, viewmodel: UsernameTabViewModel, parent=None):
        super().__init__(parent)
        self.vm = viewmodel
        self.rows = []
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Input row
        input_layout = QHBoxLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter a username...")
        self.username_input.setObjectName("main-input")
        self.username_input.returnPressed.connect(self._on_add_clicked)
        input_layout.addWidget(self.username_input, 1)

        self.add_btn = QPushButton("Add User")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self._on_add_clicked)
        input_layout.addWidget(self.add_btn)

        layout.addLayout(input_layout)

        # Users list container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area)

        # Empty state
        self.empty_state = EmptyState(
            "No users yet",
            "Enter a username and click 'Add User'."
        )
        self.list_layout.insertWidget(0, self.empty_state)

    def _connect_signals(self):
        """Connect ViewModel signals"""
        self.vm.users_changed.connect(self._on_users_changed)

    def _on_add_clicked(self):
        """Handle add button click"""
        username = self.username_input.text().strip()
        if username:
            self.vm.add_user(username)
            self.username_input.clear()

    def _on_users_changed(self, users):
        """Handle users state change"""
        # Remove old rows
        for row in self.rows:
            self.list_layout.removeWidget(row)
            row.deleteLater()
        self.rows.clear()

        # Show/hide empty state
        if not users:
            self.empty_state.show()
        else:
            self.empty_state.hide()

            # Create new rows
            for user_state in users:
                row = UsernameRow(user_state)
                row.open_clicked.connect(self.vm.open_user)
                row.remove_clicked.connect(self.vm.remove_user)

                self.list_layout.insertWidget(len(self.rows), row)
                self.rows.append(row)
