from qtpy import QtCore, QtWidgets

from models import ClipStatus, Phase
from store import (
    BuildVideo,
    MarkExportSeparately,
    NavigatePhase,
    RemoveClip,
    ReorderClips,
    SetCoverClip,
    SetSelectedClips,
)
from widgets.clip_tile import ClipTile


class ClipsScreen(QtWidgets.QWidget):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.store.stateChanged.connect(self.render)

        self.title_label = QtWidgets.QLabel("Clips")
        self.title_label.setObjectName("Title")
        self.drag_label = QtWidgets.QLabel("Drag to reorder")
        self.drag_label.setObjectName("Muted")

        self.view_toggle = QtWidgets.QButtonGroup(self)
        grid_button = QtWidgets.QToolButton()
        grid_button.setText("Grid")
        grid_button.setCheckable(True)
        grid_button.setChecked(True)
        list_button = QtWidgets.QToolButton()
        list_button.setText("List")
        list_button.setCheckable(True)
        self.view_toggle.addButton(grid_button, 0)
        self.view_toggle.addButton(list_button, 1)
        self.view_toggle.buttonClicked.connect(self._toggle_view)

        view_layout = QtWidgets.QHBoxLayout()
        view_layout.addWidget(self.title_label)
        view_layout.addStretch()
        view_layout.addWidget(grid_button)
        view_layout.addWidget(list_button)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setObjectName("ClipList")
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_widget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.list_widget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.list_widget.setSpacing(12)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.model().rowsMoved.connect(self._on_reordered)

        self.empty_state = QtWidgets.QFrame()
        self.empty_state.setObjectName("Card")
        empty_layout = QtWidgets.QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_label = QtWidgets.QLabel("No clips yet")
        empty_label.setObjectName("Title")
        empty_subtitle = QtWidgets.QLabel("Download items to start arranging your highlight.")
        empty_subtitle.setObjectName("Muted")
        empty_button = QtWidgets.QPushButton("Go to Download")
        empty_button.setObjectName("SecondaryButton")
        empty_button.clicked.connect(lambda: self.store.dispatch(NavigatePhase(Phase.DOWNLOAD)))
        empty_layout.addWidget(empty_label)
        empty_layout.addWidget(empty_subtitle)
        empty_layout.addWidget(empty_button)

        self.selection_bar = QtWidgets.QFrame()
        self.selection_bar.setObjectName("StickyBar")
        selection_layout = QtWidgets.QHBoxLayout(self.selection_bar)
        selection_layout.setContentsMargins(16, 12, 16, 12)
        self.selection_label = QtWidgets.QLabel("0 selected")
        delete_button = QtWidgets.QPushButton("Delete")
        delete_button.setObjectName("DestructiveButton")
        delete_button.clicked.connect(self._delete_selected)
        cover_button = QtWidgets.QPushButton("Set as Cover")
        cover_button.setObjectName("SecondaryButton")
        cover_button.clicked.connect(self._set_cover)
        export_sep_button = QtWidgets.QPushButton("Export Separately")
        export_sep_button.setObjectName("SecondaryButton")
        export_sep_button.clicked.connect(self._export_separately)
        selection_layout.addWidget(self.selection_label)
        selection_layout.addStretch()
        selection_layout.addWidget(delete_button)
        selection_layout.addWidget(cover_button)
        selection_layout.addWidget(export_sep_button)

        self.build_bar = QtWidgets.QFrame()
        self.build_bar.setObjectName("StickyBar")
        build_layout = QtWidgets.QHBoxLayout(self.build_bar)
        build_layout.setContentsMargins(16, 12, 16, 12)
        self.build_button = QtWidgets.QPushButton("Build Video")
        self.build_button.setObjectName("PrimaryButton")
        self.build_button.clicked.connect(lambda: self.store.dispatch(BuildVideo()))
        build_layout.addStretch()
        build_layout.addWidget(self.build_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addLayout(view_layout)
        layout.addWidget(self.drag_label)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.selection_bar)
        layout.addWidget(self.build_bar)

        self._set_grid_view()
        self.render(self.store.get_state())

    def _set_grid_view(self) -> None:
        self.list_widget.setViewMode(QtWidgets.QListView.IconMode)
        self.list_widget.setResizeMode(QtWidgets.QListView.Adjust)
        self.list_widget.setIconSize(QtCore.QSize(140, 90))
        self.list_widget.setGridSize(QtCore.QSize(220, 140))
        self.list_widget.setMovement(QtWidgets.QListView.Free)

    def _set_list_view(self) -> None:
        self.list_widget.setViewMode(QtWidgets.QListView.ListMode)
        self.list_widget.setMovement(QtWidgets.QListView.Snap)

    def _toggle_view(self, button):
        if self.view_toggle.id(button) == 0:
            self._set_grid_view()
        else:
            self._set_list_view()

    def _on_selection_changed(self):
        selected_ids = [item.data(QtCore.Qt.UserRole) for item in self.list_widget.selectedItems()]
        self.store.dispatch(SetSelectedClips(selected_ids))

    def _on_reordered(self):
        new_order = [self.list_widget.item(i).data(QtCore.Qt.UserRole) for i in range(self.list_widget.count())]
        self.store.dispatch(ReorderClips(new_order))

    def _delete_selected(self):
        for item in self.list_widget.selectedItems():
            self.store.dispatch(RemoveClip(item.data(QtCore.Qt.UserRole)))

    def _set_cover(self):
        items = self.list_widget.selectedItems()
        if items:
            self.store.dispatch(SetCoverClip(items[0].data(QtCore.Qt.UserRole)))

    def _export_separately(self):
        clip_ids = [item.data(QtCore.Qt.UserRole) for item in self.list_widget.selectedItems()]
        if clip_ids:
            self.store.dispatch(MarkExportSeparately(clip_ids))

    def render(self, state) -> None:
        project = state.projects.get(state.current_project_id)
        if not project:
            return

        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        for clip in project.clips:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, clip.id)
            widget = ClipTile()
            status_label, tone = self._status_label(clip.status)
            duration = f"{clip.duration}s" if clip.duration else ""
            widget.set_data(clip.label, clip.media_type.title(), status_label, tone, duration)
            widget.set_selected(clip.selected)
            item.setSizeHint(QtCore.QSize(200, 120))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            if clip.selected:
                item.setSelected(True)

        self.list_widget.blockSignals(False)

        has_clips = len(project.clips) > 0
        self.empty_state.setVisible(not has_clips)
        self.list_widget.setVisible(has_clips)

        selected_count = len([clip for clip in project.clips if clip.selected])
        self.selection_label.setText(f"{selected_count} selected")
        self.selection_bar.setVisible(selected_count > 0)

        can_build = project.download_done and has_clips
        self.build_button.setEnabled(can_build)

    @staticmethod
    def _status_label(status: ClipStatus) -> tuple[str, str]:
        mapping = {
            ClipStatus.WAITING: ("waiting", "neutral"),
            ClipStatus.DOWNLOADING: ("downloading", "info"),
            ClipStatus.COMPLETED: ("completed", "success"),
            ClipStatus.FAILED: ("failed", "danger"),
            ClipStatus.PAUSED: ("paused", "warning"),
        }
        return mapping.get(status, ("waiting", "neutral"))
