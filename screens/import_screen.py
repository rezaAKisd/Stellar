from qtpy import QtCore, QtGui, QtWidgets

from models import ImportState
from store import FetchHighlight, ImportLinkChanged, StartDownload


class ImportScreen(QtWidgets.QWidget):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.store.stateChanged.connect(self.render)

        self.title_label = QtWidgets.QLabel("Import Highlight")
        self.title_label.setObjectName("Title")

        self.link_input = QtWidgets.QLineEdit()
        self.link_input.setPlaceholderText("Paste a highlight link…")
        self.link_input.setObjectName("Input")
        self.link_input.textChanged.connect(self._on_link_changed)

        paste_button = QtWidgets.QPushButton("Paste")
        paste_button.setObjectName("SecondaryButton")
        paste_button.clicked.connect(self._paste_link)

        fetch_button = QtWidgets.QPushButton("Fetch")
        fetch_button.setObjectName("PrimaryButton")
        fetch_button.clicked.connect(lambda: self.store.dispatch(FetchHighlight()))

        input_layout = QtWidgets.QHBoxLayout()
        input_layout.addWidget(self.link_input)
        input_layout.addWidget(paste_button)
        input_layout.addWidget(fetch_button)

        self.empty_panel = self._build_empty_panel()
        self.loading_panel = self._build_loading_panel()
        self.ready_panel = self._build_ready_panel()
        self.error_panel = self._build_error_panel()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(self.title_label)
        layout.addLayout(input_layout)
        layout.addWidget(self.empty_panel)
        layout.addWidget(self.loading_panel)
        layout.addWidget(self.ready_panel)
        layout.addWidget(self.error_panel)
        layout.addStretch()

        self.render(self.store.get_state())

    def _build_empty_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("Card")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        label = QtWidgets.QLabel(
            "Paste the highlight link to create a new project. Example: https://instagram.com/stories/highlights/..."
        )
        label.setWordWrap(True)
        label.setObjectName("Muted")
        layout.addWidget(label)
        return panel

    def _build_loading_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("Card")
        layout = QtWidgets.QHBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        spinner = QtWidgets.QProgressBar()
        spinner.setRange(0, 0)
        spinner.setFixedWidth(160)
        label = QtWidgets.QLabel("Fetching details…")
        label.setObjectName("Muted")
        layout.addWidget(spinner)
        layout.addWidget(label)
        layout.addStretch()
        return panel

    def _build_ready_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("Card")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        header = QtWidgets.QLabel("Highlight found")
        header.setObjectName("Title")
        self.preview_title = QtWidgets.QLabel("Title")
        self.preview_title.setObjectName("CardTitle")
        self.preview_meta = QtWidgets.QLabel("0 items")
        self.preview_meta.setObjectName("Muted")

        start_button = QtWidgets.QPushButton("Start Download")
        start_button.setObjectName("PrimaryButton")
        start_button.clicked.connect(lambda: self.store.dispatch(StartDownload()))

        layout.addWidget(header)
        layout.addWidget(self.preview_title)
        layout.addWidget(self.preview_meta)
        layout.addWidget(start_button)
        return panel

    def _build_error_panel(self) -> QtWidgets.QFrame:
        panel = QtWidgets.QFrame()
        panel.setObjectName("CardError")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        self.error_label = QtWidgets.QLabel("Error")
        self.error_label.setObjectName("Muted")
        retry_button = QtWidgets.QPushButton("Retry")
        retry_button.setObjectName("SecondaryButton")
        retry_button.clicked.connect(lambda: self.store.dispatch(FetchHighlight()))
        layout.addWidget(self.error_label)
        layout.addWidget(retry_button)
        return panel

    def _paste_link(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.link_input.setText(text)

    def _on_link_changed(self, text: str) -> None:
        self.store.dispatch(ImportLinkChanged(text))

    def render(self, state) -> None:
        project = state.projects.get(state.current_project_id)
        if not project:
            self.empty_panel.setVisible(True)
            self.loading_panel.setVisible(False)
            self.ready_panel.setVisible(False)
            self.error_panel.setVisible(False)
            return

        self.link_input.blockSignals(True)
        self.link_input.setText(project.link)
        self.link_input.blockSignals(False)

        self.empty_panel.setVisible(project.import_state == ImportState.EMPTY)
        self.loading_panel.setVisible(project.import_state == ImportState.LOADING)
        self.ready_panel.setVisible(project.import_state == ImportState.READY)
        self.error_panel.setVisible(project.import_state == ImportState.ERROR)

        if project.import_state == ImportState.READY:
            self.preview_title.setText(project.title)
            self.preview_meta.setText(f"{project.item_count} items")
        if project.import_state == ImportState.ERROR:
            self.error_label.setText(project.last_error or "Something went wrong")
