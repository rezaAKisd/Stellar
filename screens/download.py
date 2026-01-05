from qtpy import QtCore, QtWidgets

from models import ClipStatus, DownloadState
from store import NavigatePhase, PauseDownload, ResumeDownload, RetryFailed
from widgets.status_pill import StatusPill


class DownloadItemWidget(QtWidgets.QFrame):
    def __init__(self, clip_id: str, parent=None):
        super().__init__(parent)
        self.clip_id = clip_id
        self.setObjectName("Card")

        self.title_label = QtWidgets.QLabel("Clip")
        self.title_label.setObjectName("CardTitle")
        self.status_pill = StatusPill("waiting", "neutral")
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)

        self.pause_button = QtWidgets.QPushButton("Pause")
        self.pause_button.setObjectName("SecondaryButton")
        self.resume_button = QtWidgets.QPushButton("Resume")
        self.resume_button.setObjectName("SecondaryButton")
        self.retry_button = QtWidgets.QPushButton("Retry")
        self.retry_button.setObjectName("SecondaryButton")
        self.remove_button = QtWidgets.QPushButton("Remove")
        self.remove_button.setObjectName("DestructiveButton")

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.resume_button)
        button_layout.addWidget(self.retry_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.addWidget(self.title_label)
        layout.addWidget(self.status_pill)
        layout.addWidget(self.progress)
        layout.addLayout(button_layout)

    def set_data(self, title: str, status: str, tone: str, progress: int) -> None:
        self.title_label.setText(title)
        self.status_pill.set_text(status, tone)
        self.progress.setValue(progress)


class DownloadScreen(QtWidgets.QWidget):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.store.stateChanged.connect(self.render)
        self._items = {}

        self.title_label = QtWidgets.QLabel("Download Queue")
        self.title_label.setObjectName("Title")

        self.progress_label = QtWidgets.QLabel("Downloading 0 of 0…")
        self.progress_label.setObjectName("Muted")
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)

        self.pause_all = QtWidgets.QPushButton("Pause All")
        self.pause_all.setObjectName("SecondaryButton")
        self.pause_all.clicked.connect(lambda: self.store.dispatch(PauseDownload()))

        self.resume_all = QtWidgets.QPushButton("Resume All")
        self.resume_all.setObjectName("SecondaryButton")
        self.resume_all.clicked.connect(lambda: self.store.dispatch(ResumeDownload()))

        self.retry_failed = QtWidgets.QPushButton("Retry Failed")
        self.retry_failed.setObjectName("SecondaryButton")
        self.retry_failed.clicked.connect(lambda: self.store.dispatch(RetryFailed()))

        top_action_layout = QtWidgets.QHBoxLayout()
        top_action_layout.addWidget(self.pause_all)
        top_action_layout.addWidget(self.resume_all)
        top_action_layout.addWidget(self.retry_failed)
        top_action_layout.addStretch()

        self.list_container = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(12)
        self.list_layout.addStretch()

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setWidget(self.list_container)

        self.storage_label = QtWidgets.QLabel("Used: 0.0 GB")
        self.storage_label.setObjectName("Muted")
        self.go_to_clips = QtWidgets.QPushButton("Go to Clips")
        self.go_to_clips.setObjectName("PrimaryButton")
        self.go_to_clips.clicked.connect(self._navigate_to_clips)

        bottom_bar = QtWidgets.QFrame()
        bottom_bar.setObjectName("StickyBar")
        bottom_layout = QtWidgets.QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(16, 12, 16, 12)
        bottom_layout.addWidget(self.storage_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.go_to_clips)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(self.title_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addLayout(top_action_layout)
        layout.addWidget(scroll)
        layout.addWidget(bottom_bar)

        self.render(self.store.get_state())

    def _navigate_to_clips(self):
        from models import Phase
        self.store.dispatch(NavigatePhase(Phase.ARRANGE))

    def render(self, state) -> None:
        project = state.projects.get(state.current_project_id)
        if not project:
            return

        completed = len([clip for clip in project.clips if clip.status == ClipStatus.COMPLETED])
        total = len(project.clips)
        self.progress_label.setText(f"Downloading {completed} of {total}…")
        self.progress_bar.setValue(int(project.download_progress))
        self.storage_label.setText(f"Used: {project.storage_used_gb:.2f} GB")

        self.go_to_clips.setEnabled(completed > 0)
        self.go_to_clips.setToolTip("" if completed > 0 else "Complete at least 1 item")

        for widget in self._items.values():
            widget.setParent(None)
        self._items.clear()

        for clip in project.clips:
            item = DownloadItemWidget(clip.id)
            tone, status_label = self._status_for_clip(clip.status)
            item.set_data(clip.label, status_label, tone, clip.progress)
            item.pause_button.clicked.connect(lambda _, cid=clip.id: self.store.dispatch(PauseDownload(cid)))
            item.resume_button.clicked.connect(lambda _, cid=clip.id: self.store.dispatch(ResumeDownload(cid)))
            item.retry_button.clicked.connect(lambda _, cid=clip.id: self._retry_clip(cid))
            item.remove_button.clicked.connect(lambda _, cid=clip.id: self._remove_clip(cid))
            self.list_layout.insertWidget(self.list_layout.count() - 1, item)
            self._items[clip.id] = item

        self.pause_all.setEnabled(project.download_state == DownloadState.DOWNLOADING)
        self.resume_all.setEnabled(project.download_state == DownloadState.PAUSED)

    def _retry_clip(self, clip_id: str) -> None:
        self.store.dispatch(ResumeDownload(clip_id))

    def _remove_clip(self, clip_id: str) -> None:
        from store import RemoveClip
        self.store.dispatch(RemoveClip(clip_id))

    @staticmethod
    def _status_for_clip(status: ClipStatus) -> tuple[str, str]:
        mapping = {
            ClipStatus.WAITING: ("neutral", "waiting"),
            ClipStatus.DOWNLOADING: ("info", "downloading"),
            ClipStatus.COMPLETED: ("success", "completed"),
            ClipStatus.FAILED: ("danger", "failed"),
            ClipStatus.PAUSED: ("warning", "paused"),
        }
        return mapping.get(status, ("neutral", "waiting"))
