"""Link Tab ViewModel"""
import asyncio
from qtpy.QtCore import QObject, Signal
from typing import List

from ..store import AppStore
from ..models_ui import HighlightRowState
from ...application.use_cases import (
    AddHighlightLinkUseCase,
    DownloadHighlightUseCase,
    BuildVideoUseCase,
    OpenExportsFolderUseCase
)
from ...infrastructure.instagram_stub import InstagramGatewayStub
from ...infrastructure.storage_local import FileStorageLocal
from ...infrastructure.video_stub import VideoComposerStub


class LinkTabViewModel(QObject):
    """ViewModel for By Highlight Link tab"""

    projects_changed = Signal(list)  # List[HighlightRowState]

    def __init__(self, store: AppStore):
        super().__init__()
        self.store = store
        self.instagram = InstagramGatewayStub()
        self.storage = FileStorageLocal()
        self.video_composer = VideoComposerStub()

        # Listen to store
        self.store.state_changed.connect(self._on_state_changed)

    def _on_state_changed(self):
        """Handle store changes"""
        self.projects_changed.emit(self.store.state.link_projects)

    def add_and_download(self, url: str):
        """Add highlight link and start download"""
        if not url or not url.strip():
            self.store.show_toast("Please enter a valid URL", "error")
            return

        asyncio.create_task(self._add_and_download_async(url.strip()))

    async def _add_and_download_async(self, url: str):
        """Async add and download"""
        try:
            # Add highlight
            add_uc = AddHighlightLinkUseCase(self.instagram, self.storage)
            project_dto = await add_uc.execute(url)

            # Create domain entity
            from ...domain.entities import HighlightProject, DownloadStatus
            project = HighlightProject(
                id=project_dto.id,
                title=project_dto.title,
                source=project_dto.source,
                folder_path=project_dto.folder_path
            )

            # Add to store
            self.store.add_link_project(project_dto, project)
            self.store.show_toast("Download started", "info")

            # Start download
            download_uc = DownloadHighlightUseCase(self.instagram, self.storage)

            def progress_callback(p: float):
                self.store.update_link_project(project.id, project)

            result = await download_uc.execute(project, progress_callback)

            if result.success:
                self.store.update_link_project(project.id, project)
                self.store.show_toast("Download completed", "success")
            else:
                self.store.update_link_project(project.id, project)
                self.store.show_toast(result.message, "error")

        except Exception as e:
            self.store.show_toast(f"Error: {str(e)}", "error")

    def build_video(self, project_id: str):
        """Build video for a project"""
        project = self.store.get_project(project_id)
        if not project:
            return

        asyncio.create_task(self._build_video_async(project))

    async def _build_video_async(self, project):
        """Async video build"""
        build_uc = BuildVideoUseCase(self.video_composer, self.storage)

        def progress_callback(p: float):
            self.store.update_link_project(project.id, project)

        result = await build_uc.execute(project, progress_callback)

        if result.success:
            self.store.update_link_project(project.id, project)
            self.store.show_toast("Export completed", "success")
        else:
            self.store.update_link_project(project.id, project)
            self.store.show_toast(result.message, "error")

    def view_exports(self, project_id: str):
        """Open exports folder"""
        project = self.store.get_project(project_id)
        if not project:
            return

        open_uc = OpenExportsFolderUseCase(self.storage)
        open_uc.execute(project.folder_path, "exports")

    def view_downloads(self, project_id: str):
        """Open downloads folder"""
        project = self.store.get_project(project_id)
        if not project:
            return

        open_uc = OpenExportsFolderUseCase(self.storage)
        open_uc.execute(project.folder_path, "downloads")

    def remove_project(self, project_id: str):
        """Remove a project"""
        self.store.remove_link_project(project_id)
        self.store.show_toast("Project removed", "info")
