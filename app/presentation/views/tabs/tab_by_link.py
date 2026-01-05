"""By Highlight Link Tab"""
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QScrollArea, QFrame
)
from qtpy.QtCore import Qt

from ..widgets.empty_state import EmptyState
from ..widgets.highlight_row import HighlightRow
from ...viewmodels.link_tab_vm import LinkTabViewModel


class TabByLink(QWidget):
    """Tab for adding highlights by link"""

    def __init__(self, viewmodel: LinkTabViewModel, parent=None):
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

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste highlight link...")
        self.url_input.setObjectName("main-input")
        self.url_input.returnPressed.connect(self._on_add_clicked)
        input_layout.addWidget(self.url_input, 1)

        self.add_btn = QPushButton("Add & Download")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self._on_add_clicked)
        input_layout.addWidget(self.add_btn)

        layout.addLayout(input_layout)

        # Projects list container
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
            "No highlights yet",
            "Paste a highlight link and click 'Add & Download'."
        )
        self.list_layout.insertWidget(0, self.empty_state)

    def _connect_signals(self):
        """Connect ViewModel signals"""
        self.vm.projects_changed.connect(self._on_projects_changed)

    def _on_add_clicked(self):
        """Handle add button click"""
        url = self.url_input.text().strip()
        if url:
            self.vm.add_and_download(url)
            self.url_input.clear()

    def _on_projects_changed(self, projects):
        """Handle projects state change"""
        # Remove old rows
        for row in self.rows:
            self.list_layout.removeWidget(row)
            row.deleteLater()
        self.rows.clear()

        # Show/hide empty state
        if not projects:
            self.empty_state.show()
        else:
            self.empty_state.hide()

            # Create new rows
            for project_state in projects:
                row = HighlightRow(project_state)
                row.build_video_clicked.connect(self.vm.build_video)
                row.view_exports_clicked.connect(self.vm.view_exports)
                row.view_downloads_clicked.connect(self.vm.view_downloads)
                row.open_folder_clicked.connect(self.vm.view_downloads)
                row.remove_clicked.connect(self.vm.remove_project)
                row.retry_clicked.connect(lambda pid: self.vm.add_and_download(
                    self.vm.store.get_project(pid).source
                ))

                self.list_layout.insertWidget(len(self.rows), row)
                self.rows.append(row)
