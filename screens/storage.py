from qtpy import QtWidgets

from store import AddToast


class StorageScreen(QtWidgets.QWidget):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.store.stateChanged.connect(self.render)

        title = QtWidgets.QLabel("Storage")
        title.setObjectName("Title")

        self.usage_label = QtWidgets.QLabel("Total used: 0.0 GB")
        self.usage_label.setObjectName("Muted")

        clear_button = QtWidgets.QPushButton("Clear Cache")
        clear_button.setObjectName("DestructiveButton")
        clear_button.clicked.connect(lambda: self.store.dispatch(AddToast("Cache cleared", "success")))

        self.auto_delete = QtWidgets.QCheckBox("Auto-delete downloads after export")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(self.usage_label)
        layout.addWidget(clear_button)
        layout.addWidget(self.auto_delete)
        layout.addStretch()

        self.render(self.store.get_state())

    def render(self, state) -> None:
        total = sum(project.storage_used_gb for project in state.projects.values())
        self.usage_label.setText(f"Total used: {total:.2f} GB")
