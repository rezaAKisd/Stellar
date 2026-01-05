from qtpy import QtWidgets

from models import ExportMode, RenderState
from store import Export


class ExportScreen(QtWidgets.QWidget):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.store.stateChanged.connect(self.render)

        title = QtWidgets.QLabel("Export")
        title.setObjectName("Title")

        self.summary_card = QtWidgets.QFrame()
        self.summary_card.setObjectName("Card")
        summary_layout = QtWidgets.QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(16, 16, 16, 16)
        self.summary_label = QtWidgets.QLabel("Estimated output")
        self.summary_label.setObjectName("Muted")
        self.items_label = QtWidgets.QLabel("Items: 0")
        self.items_label.setObjectName("Muted")
        self.mode_label = QtWidgets.QLabel("Mode: Merged")
        self.mode_label.setObjectName("Muted")
        summary_layout.addWidget(self.summary_label)
        summary_layout.addWidget(self.items_label)
        summary_layout.addWidget(self.mode_label)

        self.export_button = QtWidgets.QPushButton("Export")
        self.export_button.setObjectName("PrimaryButton")
        self.export_button.clicked.connect(lambda: self.store.dispatch(Export()))

        self.error_card = QtWidgets.QFrame()
        self.error_card.setObjectName("CardError")
        error_layout = QtWidgets.QVBoxLayout(self.error_card)
        error_layout.setContentsMargins(16, 16, 16, 16)
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setObjectName("Muted")
        error_layout.addWidget(self.error_label)

        self.progress_card = QtWidgets.QFrame()
        self.progress_card.setObjectName("Card")
        progress_layout = QtWidgets.QVBoxLayout(self.progress_card)
        progress_layout.setContentsMargins(16, 16, 16, 16)
        self.progress_label = QtWidgets.QLabel("Rendering… 0%")
        self.progress_label.setObjectName("Muted")
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.setObjectName("SecondaryButton")
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.cancel_button)

        self.done_card = QtWidgets.QFrame()
        self.done_card.setObjectName("Card")
        done_layout = QtWidgets.QVBoxLayout(self.done_card)
        done_layout.setContentsMargins(16, 16, 16, 16)
        self.done_label = QtWidgets.QLabel("Video ready")
        self.done_label.setObjectName("Title")
        self.open_folder_button = QtWidgets.QPushButton("Open Folder")
        self.open_folder_button.setObjectName("SecondaryButton")
        self.open_clips_button = QtWidgets.QPushButton("Open Clips Folder")
        self.open_clips_button.setObjectName("SecondaryButton")
        done_layout.addWidget(self.done_label)
        done_layout.addWidget(self.open_folder_button)
        done_layout.addWidget(self.open_clips_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(self.summary_card)
        layout.addWidget(self.export_button)
        layout.addWidget(self.error_card)
        layout.addWidget(self.progress_card)
        layout.addWidget(self.done_card)
        layout.addStretch()

        self.render(self.store.get_state())

    def render(self, state) -> None:
        project = state.projects.get(state.current_project_id)
        if not project:
            return

        self.summary_label.setText(
            f"Estimated output: {project.settings.resolution} • {project.settings.fps}fps • {project.settings.aspect_ratio}"
        )
        self.items_label.setText(f"Items: {len(project.clips)}")
        mode_text = "Merged" if project.settings.export_mode == ExportMode.MERGED else "Separate"
        self.mode_label.setText(f"Mode: {mode_text}")

        self.progress_bar.setValue(int(project.render_progress))
        self.progress_label.setText(f"Rendering… {int(project.render_progress)}%")

        is_rendering = project.render_state == RenderState.RENDERING
        self.progress_card.setVisible(is_rendering)
        self.export_button.setVisible(project.render_state in (RenderState.READY, RenderState.ERROR))
        self.error_card.setVisible(project.render_state == RenderState.ERROR)
        self.done_card.setVisible(project.render_state == RenderState.DONE)
        self.error_label.setText(project.last_error or "Something went wrong.")

        if project.settings.export_mode == ExportMode.SEPARATE:
            self.done_label.setText(f"{len(project.clips)} clips exported")
            self.open_clips_button.setVisible(True)
        else:
            self.done_label.setText("Video ready")
            self.open_clips_button.setVisible(False)
