"""User Detail ViewModel"""
import asyncio
from qtpy.QtCore import QObject, Signal

from ..store import AppStore
from ..models_ui import UserDetailState, UserHighlightCardState
from ...application.use_cases import (
    LoadUserHighlightsUseCase,
    DownloadUserHighlightUseCase,
    BuildVideoUseCase,
    OpenExportsFolderUseCase
)
from ...infrastructure.container import DependencyContainer


class UserDetailViewModel(QObject):
    """ViewModel for user detail page"""

    detail_changed = Signal(object)  # UserDetailState

    def __init__(self, store: AppStore, container: DependencyContainer):
        super().__init__()
        self.store = store
        self.container = container
        self.instagram = container.instagram_gateway
        self.storage = container.file_storage
        self.video_composer = container.video_composer

        # Listen to store
        self.store.state_changed.connect(self._on_state_changed)

    def _on_state_changed(self):
        """Handle store changes"""
        self.detail_changed.emit(self.store.state.user_detail)

    def load_highlights(self, username: str):
        """Load highlights for a user"""
        asyncio.create_task(self._load_highlights_async(username))

    async def _load_highlights_async(self, username: str):
        """Async load highlights"""
        try:
            load_uc = LoadUserHighlightsUseCase(self.instagram)
            highlights = await load_uc.execute(username)
            self.store.set_user_highlights(highlights)

        except Exception as e:
            self.store.show_toast(f"Error loading highlights: {str(e)}", "error")

    def download_highlight(self, username: str, card: UserHighlightCardState):
        """Download a user's highlight"""
        asyncio.create_task(self._download_highlight_async(username, card))

    async def _download_highlight_async(self, username: str, card: UserHighlightCardState):
        """Async download highlight"""
        try:
            from ...application.dtos import UserHighlightDTO
            from ...domain.entities import HighlightProject, DownloadStatus

            highlight_dto = UserHighlightDTO(
                id=card.id,
                name=card.name,
                cover_url=card.cover_url,
                item_count=card.item_count,
                highlight_id=card.highlight_id
            )

            download_uc = DownloadUserHighlightUseCase(self.instagram, self.storage)

            # Create temporary project
            from pathlib import Path
            from ...domain.value_objects import FolderPath

            safe_name = card.name.replace(" ", "_").replace("/", "_")
            base_path = FolderPath(Path("./data/users") / username / safe_name)
            self.storage.create_project_folders(base_path)

            project = HighlightProject(
                title=card.name,
                source=f"@{username}",
                folder_path=str(base_path),
                download_status=DownloadStatus.DOWNLOADING
            )

            # Update card in store
            self.store.update_user_highlight(card.highlight_id, project)
            self.store.show_toast("Download started", "info")

            # Download
            from ...application.use_cases import DownloadHighlightUseCase
            dl_uc = DownloadHighlightUseCase(self.instagram, self.storage)

            def progress_callback(p: float):
                self.store.update_user_highlight(card.highlight_id, project)

            result = await dl_uc.execute(project, progress_callback)

            if result.success:
                self.store.update_user_highlight(card.highlight_id, project)
                self.store.show_toast("Download completed", "success")
            else:
                self.store.update_user_highlight(card.highlight_id, project)
                self.store.show_toast(result.message, "error")

        except Exception as e:
            self.store.show_toast(f"Error: {str(e)}", "error")

    def build_video(self, card: UserHighlightCardState):
        """Build video for a highlight"""
        if not card.project_id:
            return

        project = self.store.get_project(card.project_id)
        if not project:
            return

        asyncio.create_task(self._build_video_async(project, card.highlight_id))

    async def _build_video_async(self, project, highlight_id: str):
        """Async video build"""
        build_uc = BuildVideoUseCase(self.video_composer, self.storage)

        def progress_callback(p: float):
            self.store.update_user_highlight(highlight_id, project)

        result = await build_uc.execute(project, progress_callback)

        if result.success:
            self.store.update_user_highlight(highlight_id, project)
            self.store.show_toast("Export completed", "success")
        else:
            self.store.update_user_highlight(highlight_id, project)
            self.store.show_toast(result.message, "error")

    def view_downloads(self, card: UserHighlightCardState):
        """Open downloads folder"""
        if not card.folder_path:
            return

        open_uc = OpenExportsFolderUseCase(self.storage)
        open_uc.execute(card.folder_path, "downloads")

    def view_exports(self, card: UserHighlightCardState):
        """Open exports folder"""
        if not card.folder_path:
            return

        open_uc = OpenExportsFolderUseCase(self.storage)
        open_uc.execute(card.folder_path, "exports")

    def go_back(self):
        """Navigate back to main view"""
        self.store.close_user_detail()
