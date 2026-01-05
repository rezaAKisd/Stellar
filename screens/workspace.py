from qtpy import QtCore, QtGui, QtWidgets

from models import DownloadState, ImportState, Phase
from screens.clips import ClipsScreen
from screens.download import DownloadScreen
from screens.export import ExportScreen
from screens.import_screen import ImportScreen
from screens.settings_screen import SettingsScreen
from store import AddToast, NavigatePhase, OpenProjectFolder
from widgets.stepper import Stepper


class WorkspaceScreen(QtWidgets.QWidget):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.store.stateChanged.connect(self.render)

        self.title_label = QtWidgets.QLabel("Project")
        self.title_label.setObjectName("Title")
        self.cover = QtWidgets.QLabel()
        self.cover.setFixedSize(56, 56)
        self.cover.setObjectName("ProjectCover")
        self.cover.setPixmap(self._placeholder_pixmap())

        self.menu_button = QtWidgets.QToolButton()
        self.menu_button.setText("Project menu")
        self.menu_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        menu = QtWidgets.QMenu(self)
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(lambda: self.store.dispatch(AddToast("Rename not implemented", "info")))
        menu.addAction("Open folder").triggered.connect(lambda: self.store.dispatch(OpenProjectFolder()))
        menu.addAction("Delete project").triggered.connect(self._delete_project)
        self.menu_button.setMenu(menu)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(self.cover)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.menu_button)

        self.stepper = Stepper([Phase.IMPORT, Phase.DOWNLOAD, Phase.ARRANGE, Phase.SETTINGS, Phase.EXPORT])
        self.stepper.stepClicked.connect(self._on_step_clicked)

        self.sidebar = QtWidgets.QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.addItem("Clips")
        self.sidebar.addItem("Settings")
        self.sidebar.addItem("Export")
        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)

        self.stack = QtWidgets.QStackedWidget()
        self.import_screen = ImportScreen(store)
        self.download_screen = DownloadScreen(store)
        self.clips_screen = ClipsScreen(store)
        self.settings_screen = SettingsScreen(store)
        self.export_screen = ExportScreen(store)

        self.stack.addWidget(self.import_screen)
        self.stack.addWidget(self.download_screen)
        self.stack.addWidget(self.clips_screen)
        self.stack.addWidget(self.settings_screen)
        self.stack.addWidget(self.export_screen)

        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.stack, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addLayout(header_layout)
        layout.addWidget(self.stepper)
        layout.addLayout(content_layout)

        self.render(self.store.get_state())

    def _on_step_clicked(self, phase: Phase) -> None:
        self.store.dispatch(NavigatePhase(phase))

    def _on_sidebar_changed(self, index: int) -> None:
        phase_map = [Phase.ARRANGE, Phase.SETTINGS, Phase.EXPORT]
        if 0 <= index < len(phase_map):
            self.store.dispatch(NavigatePhase(phase_map[index]))

    def _delete_project(self) -> None:
        from store import DeleteProject
        self.store.dispatch(DeleteProject())

    def render(self, state) -> None:
        project = state.projects.get(state.current_project_id)
        if not project:
            return

        self.title_label.setText(project.title)
        enabled_steps = [Phase.IMPORT]
        if project.import_state in (ImportState.READY, ImportState.ERROR):
            enabled_steps.append(Phase.DOWNLOAD)
        if project.download_state in (DownloadState.DOWNLOADING, DownloadState.COMPLETED, DownloadState.PARTIAL_FAILED):
            enabled_steps.append(Phase.ARRANGE)
        if project.clips:
            enabled_steps.append(Phase.SETTINGS)
        if project.download_done:
            enabled_steps.append(Phase.EXPORT)

        self.stepper.set_state(state.phase, enabled_steps)

        phase_index = {
            Phase.IMPORT: 0,
            Phase.DOWNLOAD: 1,
            Phase.ARRANGE: 2,
            Phase.SETTINGS: 3,
            Phase.EXPORT: 4,
        }.get(state.phase, 0)
        self.stack.setCurrentIndex(phase_index)

        if state.phase == Phase.ARRANGE:
            self.sidebar.setCurrentRow(0)
        elif state.phase == Phase.SETTINGS:
            self.sidebar.setCurrentRow(1)
        elif state.phase == Phase.EXPORT:
            self.sidebar.setCurrentRow(2)

    @staticmethod
    def _placeholder_pixmap() -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(56, 56)
        pixmap.fill(QtGui.QColor("#E9ECF2"))
        return pixmap
