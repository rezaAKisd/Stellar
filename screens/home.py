from qtpy import QtWidgets

from models import AuthState, ProjectStatus
from store import (
    AddToast,
    ConnectWithSessionToken,
    CreateProject,
    DisconnectSession,
    SelectProject,
)
from widgets.project_card import ProjectCard
from widgets.status_pill import StatusPill


class HomeScreen(QtWidgets.QWidget):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.store.stateChanged.connect(self.render)
        self._project_cards = {}

        self.title_label = QtWidgets.QLabel("Projects")
        self.title_label.setObjectName("Title")

        self.new_project_button = QtWidgets.QPushButton("New Project")
        self.new_project_button.setObjectName("PrimaryButton")
        self.new_project_button.clicked.connect(self._create_project)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.new_project_button)

        self.auth_card = self._build_auth_card()

        self.projects_container = QtWidgets.QWidget()
        self.projects_layout = QtWidgets.QVBoxLayout(self.projects_container)
        self.projects_layout.setContentsMargins(0, 0, 0, 0)
        self.projects_layout.setSpacing(12)
        self.projects_layout.addStretch()

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidget(self.projects_container)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addLayout(header_layout)
        layout.addWidget(self.auth_card)
        layout.addWidget(scroll)

        self.render(self.store.get_state())

    def _build_auth_card(self) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Stellar")
        title.setObjectName("Title")
        self.status_pill = StatusPill("Disconnected", "neutral")
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.status_pill)

        connect_button = QtWidgets.QPushButton("Connect via Browser")
        connect_button.setObjectName("PrimaryButton")
        connect_button.clicked.connect(
            lambda: self.store.dispatch(AddToast("Browser connection started", "info"))
        )

        token_button = QtWidgets.QPushButton("Use existing session token")
        token_button.setObjectName("SecondaryButton")
        token_button.clicked.connect(self._use_token)

        self.token_input = QtWidgets.QLineEdit()
        self.token_input.setPlaceholderText("Paste session token")
        self.token_input.setObjectName("Input")
        self.token_input.setVisible(False)

        self.token_connect = QtWidgets.QPushButton("Connect")
        self.token_connect.setObjectName("SecondaryButton")
        self.token_connect.setVisible(False)
        self.token_connect.clicked.connect(self._submit_token)

        self.disconnect_button = QtWidgets.QPushButton("Disconnect")
        self.disconnect_button.setObjectName("SecondaryButton")
        self.disconnect_button.clicked.connect(lambda: self.store.dispatch(DisconnectSession()))

        self.session_label = QtWidgets.QLabel("Session ID: —")
        self.session_label.setObjectName("Muted")
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setObjectName("Muted")

        disclaimer = QtWidgets.QLabel("Only download content you have rights to access.")
        disclaimer.setObjectName("Muted")

        layout.addLayout(header_layout)
        layout.addWidget(connect_button)
        layout.addWidget(token_button)
        layout.addWidget(self.token_input)
        layout.addWidget(self.token_connect)
        layout.addWidget(self.disconnect_button)
        layout.addWidget(self.session_label)
        layout.addWidget(self.error_label)
        layout.addWidget(disclaimer)
        return card

    def _use_token(self) -> None:
        is_visible = not self.token_input.isVisible()
        self.token_input.setVisible(is_visible)
        self.token_connect.setVisible(is_visible)

    def _submit_token(self) -> None:
        self.store.dispatch(ConnectWithSessionToken(self.token_input.text()))

    def _create_project(self) -> None:
        self.store.dispatch(CreateProject("New Project"))

    def render(self, state) -> None:
        projects = list(state.projects.values())

        for card in self._project_cards.values():
            card.setParent(None)
        self._project_cards.clear()

        for project in projects:
            card = ProjectCard(project.id)
            status_text, status_tone = self._status_label(project.status)
            card.set_data(project.title, project.item_count, status_text, status_tone, project.last_updated)
            card.clicked.connect(self._open_project)
            self.projects_layout.insertWidget(self.projects_layout.count() - 1, card)
            self._project_cards[project.id] = card

        auth_state = state.auth_state
        if auth_state == AuthState.CONNECTED:
            self.status_pill.set_text("Connected", "success")
        elif auth_state == AuthState.CONNECTING:
            self.status_pill.set_text("Connecting", "info")
        elif auth_state == AuthState.ERROR:
            self.status_pill.set_text("Error", "danger")
        else:
            self.status_pill.set_text("Disconnected", "neutral")

        session_id = state.session_id or "—"
        masked = session_id if session_id == "—" else f"{session_id[:6]}...{session_id[-4:]}"
        self.session_label.setText(f"Session ID: {masked}")
        self.error_label.setText(state.auth_error)
        self.error_label.setVisible(bool(state.auth_error))

        connecting = auth_state == AuthState.CONNECTING
        self.token_input.setEnabled(not connecting)
        self.token_connect.setEnabled(not connecting)
        self.disconnect_button.setEnabled(auth_state == AuthState.CONNECTED)

    def _open_project(self, project_id: str) -> None:
        self.store.dispatch(SelectProject(project_id))

    @staticmethod
    def _status_label(status: ProjectStatus) -> tuple[str, str]:
        mapping = {
            ProjectStatus.DRAFT: ("Draft", "neutral"),
            ProjectStatus.DOWNLOADING: ("Downloading", "info"),
            ProjectStatus.READY: ("Ready to Export", "success"),
            ProjectStatus.EXPORTED: ("Exported", "success"),
            ProjectStatus.ERROR: ("Error", "danger"),
        }
        return mapping.get(status, ("Draft", "neutral"))
