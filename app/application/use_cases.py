"""Use Cases - Application business logic orchestration"""
from typing import Optional, Callable, List
from pathlib import Path

from ..domain.entities import (
    HighlightProject, DownloadStatus, ExportStatus,
    HighlightItem, UserProfile, UserHighlight
)
from ..domain.value_objects import HighlightUrl, Username, FolderPath, SessionToken
from ..domain.interfaces import IInstagramGateway, IFileStorage, IVideoComposer
from .dtos import (
    HighlightProjectDTO, UserProfileDTO, UserHighlightDTO,
    SessionStatusDTO, OperationResultDTO, HighlightItemDTO
)


class ConnectSessionUseCase:
    """Use case for connecting Instagram session"""

    def __init__(
        self,
        instagram_gateway: IInstagramGateway,
        file_storage: IFileStorage
    ):
        self.instagram = instagram_gateway
        self.storage = file_storage

    async def execute(self, session_token_str: str) -> SessionStatusDTO:
        """Connect using session token"""
        try:
            token = SessionToken(session_token_str)
            is_valid = await self.instagram.authenticate_with_session(token)

            if is_valid:
                self.storage.save_session(token)
                return SessionStatusDTO(
                    is_connected=True,
                    session_present=True,
                    message="Session connected successfully"
                )
            else:
                return SessionStatusDTO(
                    is_connected=False,
                    session_present=False,
                    message="Invalid session token"
                )
        except Exception as e:
            return SessionStatusDTO(
                is_connected=False,
                session_present=False,
                message=f"Connection failed: {str(e)}"
            )


class LoadSavedSessionUseCase:
    """Use case for loading saved session"""

    def __init__(
        self,
        instagram_gateway: IInstagramGateway,
        file_storage: IFileStorage
    ):
        self.instagram = instagram_gateway
        self.storage = file_storage

    async def execute(self) -> SessionStatusDTO:
        """Load and validate saved session"""
        try:
            token = self.storage.load_session()
            if not token:
                return SessionStatusDTO(
                    is_connected=False,
                    session_present=False,
                    message="No saved session"
                )

            is_valid = await self.instagram.authenticate_with_session(token)
            return SessionStatusDTO(
                is_connected=is_valid,
                session_present=True,
                message="Session loaded" if is_valid else "Session expired"
            )
        except Exception as e:
            return SessionStatusDTO(
                is_connected=False,
                session_present=False,
                message=f"Failed to load session: {str(e)}"
            )


class AddHighlightLinkUseCase:
    """Use case for adding a highlight by link"""

    def __init__(
        self,
        instagram_gateway: IInstagramGateway,
        file_storage: IFileStorage
    ):
        self.instagram = instagram_gateway
        self.storage = file_storage

    async def execute(self, url_str: str) -> HighlightProjectDTO:
        """Create a highlight project from URL"""
        try:
            url = HighlightUrl(url_str)

            # Fetch metadata
            metadata = await self.instagram.fetch_highlight_metadata(url)

            # Create project folder
            base_path = FolderPath(Path("./data/projects") / url.slug)
            downloads_path, exports_path = self.storage.create_project_folders(base_path)

            # Create project entity
            project = HighlightProject(
                title=metadata.get("title", "Untitled Highlight"),
                source=url_str,
                folder_path=str(base_path),
                items=[],
                download_status=DownloadStatus.IDLE
            )

            return self._to_dto(project)

        except Exception as e:
            raise ValueError(f"Failed to add highlight: {str(e)}")

    def _to_dto(self, project: HighlightProject) -> HighlightProjectDTO:
        return HighlightProjectDTO(
            id=project.id,
            title=project.title,
            source=project.source,
            folder_path=project.folder_path,
            item_count=project.item_count,
            download_status=project.download_status.value,
            export_status=project.export_status.value,
            download_progress=project.download_progress,
            export_progress=project.export_progress,
            error_message=project.error_message,
            has_downloads=project.has_downloads,
            has_exports=project.has_exports
        )


class DownloadHighlightUseCase:
    """Use case for downloading highlight items"""

    def __init__(
        self,
        instagram_gateway: IInstagramGateway,
        file_storage: IFileStorage
    ):
        self.instagram = instagram_gateway
        self.storage = file_storage

    async def execute(
        self,
        project: HighlightProject,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> OperationResultDTO:
        """Download all items for a project"""
        try:
            project.download_status = DownloadStatus.DOWNLOADING
            project.download_progress = 0.0

            # Fetch items from Instagram
            items = await self.instagram.fetch_highlight_items(project.id)
            project.items = items

            # Download each item
            downloads_path = FolderPath(Path(project.folder_path) / "downloads")
            total = len(items)

            for idx, item in enumerate(items):
                def item_progress(p: float):
                    overall = (idx + p) / total
                    project.download_progress = overall
                    if progress_callback:
                        progress_callback(overall)

                local_path = await self.instagram.download_item(
                    item,
                    downloads_path,
                    item_progress
                )
                item.downloaded_path = local_path

            project.download_status = DownloadStatus.DOWNLOADED
            project.download_progress = 1.0

            if progress_callback:
                progress_callback(1.0)

            return OperationResultDTO(
                success=True,
                message=f"Downloaded {total} items",
                data=total
            )

        except Exception as e:
            project.download_status = DownloadStatus.ERROR
            project.error_message = str(e)
            return OperationResultDTO(
                success=False,
                message=f"Download failed: {str(e)}"
            )


class BuildVideoUseCase:
    """Use case for building video from highlight"""

    def __init__(
        self,
        video_composer: IVideoComposer,
        file_storage: IFileStorage
    ):
        self.composer = video_composer
        self.storage = file_storage

    async def execute(
        self,
        project: HighlightProject,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> OperationResultDTO:
        """Build video from downloaded items"""
        try:
            if project.download_status != DownloadStatus.DOWNLOADED:
                return OperationResultDTO(
                    success=False,
                    message="Project not downloaded yet"
                )

            project.export_status = ExportStatus.BUILDING
            project.export_progress = 0.0

            exports_path = FolderPath(Path(project.folder_path) / "exports")
            filename = f"{project.title.replace(' ', '_')}_merged.mp4"

            def export_progress(p: float):
                project.export_progress = p
                if progress_callback:
                    progress_callback(p)

            output_path = await self.composer.merge_items_to_video(
                project.items,
                exports_path,
                filename,
                export_progress
            )

            project.export_status = ExportStatus.EXPORTED
            project.export_progress = 1.0

            if progress_callback:
                progress_callback(1.0)

            return OperationResultDTO(
                success=True,
                message="Video created successfully",
                data=output_path
            )

        except Exception as e:
            project.export_status = ExportStatus.ERROR
            project.error_message = str(e)
            return OperationResultDTO(
                success=False,
                message=f"Export failed: {str(e)}"
            )


class AddUsernameUseCase:
    """Use case for adding a username"""

    def __init__(
        self,
        instagram_gateway: IInstagramGateway,
        file_storage: IFileStorage
    ):
        self.instagram = instagram_gateway
        self.storage = file_storage

    async def execute(self, username_str: str) -> UserProfileDTO:
        """Add a user and fetch their highlights"""
        try:
            username = Username(username_str)

            # Create user profile
            profile = UserProfile(
                username=str(username),
                display_name=str(username),
                avatar_url=""
            )

            return UserProfileDTO(
                id=profile.id,
                username=profile.username,
                display_name=profile.display_name,
                avatar_url=profile.avatar_url,
                highlights=[]
            )

        except Exception as e:
            raise ValueError(f"Failed to add user: {str(e)}")


class LoadUserHighlightsUseCase:
    """Use case for loading user's highlights"""

    def __init__(
        self,
        instagram_gateway: IInstagramGateway
    ):
        self.instagram = instagram_gateway

    async def execute(self, username_str: str) -> List[UserHighlightDTO]:
        """Load all highlights for a username"""
        try:
            username = Username(username_str)
            highlights = await self.instagram.fetch_user_highlights(username)

            return [
                UserHighlightDTO(
                    id=h.id,
                    name=h.name,
                    cover_url=h.cover_url,
                    item_count=h.item_count,
                    highlight_id=h.highlight_id,
                    project_id=h.project_id
                )
                for h in highlights
            ]

        except Exception as e:
            raise ValueError(f"Failed to load highlights: {str(e)}")


class DownloadUserHighlightUseCase:
    """Use case for downloading a specific user highlight"""

    def __init__(
        self,
        instagram_gateway: IInstagramGateway,
        file_storage: IFileStorage
    ):
        self.instagram = instagram_gateway
        self.storage = file_storage

    async def execute(
        self,
        username: str,
        highlight: UserHighlightDTO,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> HighlightProjectDTO:
        """Download a user's highlight"""
        try:
            # Create project folder
            safe_name = highlight.name.replace(" ", "_").replace("/", "_")
            base_path = FolderPath(Path("./data/users") / username / safe_name)
            downloads_path, exports_path = self.storage.create_project_folders(base_path)

            # Create project
            project = HighlightProject(
                title=highlight.name,
                source=f"@{username}",
                folder_path=str(base_path),
                items=[],
                download_status=DownloadStatus.DOWNLOADING
            )

            # Use DownloadHighlightUseCase
            download_uc = DownloadHighlightUseCase(self.instagram, self.storage)
            result = await download_uc.execute(project, progress_callback)

            return HighlightProjectDTO(
                id=project.id,
                title=project.title,
                source=project.source,
                folder_path=project.folder_path,
                item_count=project.item_count,
                download_status=project.download_status.value,
                export_status=project.export_status.value,
                download_progress=project.download_progress,
                export_progress=project.export_progress,
                error_message=project.error_message,
                has_downloads=project.has_downloads,
                has_exports=project.has_exports
            )

        except Exception as e:
            raise ValueError(f"Failed to download highlight: {str(e)}")


class OpenExportsFolderUseCase:
    """Use case for opening exports folder"""

    def __init__(self, file_storage: IFileStorage):
        self.storage = file_storage

    def execute(self, folder_path: str, subfolder: str = "exports") -> None:
        """Open a project's exports or downloads folder"""
        path = FolderPath(Path(folder_path) / subfolder)
        self.storage.open_folder_in_explorer(path)
