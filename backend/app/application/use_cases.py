"""Use Cases - Application business logic orchestration"""
from typing import Optional, Callable, List
from pathlib import Path
from datetime import datetime
import uuid
import re

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

    async def execute(self, url_str: str, owner: str) -> HighlightProjectDTO:
        """Create a highlight project from URL"""
        try:
            url = HighlightUrl(url_str)

            # Fetch metadata
            metadata = await self.instagram.fetch_highlight_metadata(url)
            expected_items = int(metadata.get("total_items") or 0)

            # Create project folder with owner isolation
            base_path = FolderPath(Path("./data") / owner / "projects" / url.slug)
            downloads_path, exports_path = self.storage.create_project_folders(base_path)

            # Create project entity
            project = HighlightProject(
                id=str(metadata.get("id") or uuid.uuid4()),
                title=metadata.get("title", "Untitled Highlight"),
                source=url_str,
                folder_path=str(base_path),
                items=[],
                download_status=DownloadStatus.IDLE
            )

            return self._to_dto(project, item_count_override=expected_items)

        except Exception as e:
            raise ValueError(f"Failed to add highlight: {str(e)}")

    def _to_dto(self, project: HighlightProject, item_count_override: Optional[int] = None) -> HighlightProjectDTO:
        return HighlightProjectDTO(
            id=project.id,
            title=project.title,
            source=project.source,
            folder_path=project.folder_path,
            item_count=project.item_count if item_count_override is None else item_count_override,
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

            # Extract Instagram highlight PK from source
            # Source can be:
            # - Full URL: "https://www.instagram.com/stories/highlights/123456/"
            # - Destination format: "@username/highlight_pk"
            # - Or the project.id itself for direct links (legacy)
            highlight_pk = project.id
            if project.source.startswith("@"):
                # Destination format: @username/highlight_pk
                parts = project.source.split("/")
                if len(parts) >= 2:
                    highlight_pk = parts[-1]
            elif "instagram.com" in project.source or "/highlights/" in project.source:
                # Try to fetch metadata to get the PK
                url = HighlightUrl(project.source)
                metadata = await self.instagram.fetch_highlight_metadata(url)
                highlight_pk = str(metadata.get("id") or project.id)

            # Fetch items from Instagram
            items = await self.instagram.fetch_highlight_items(highlight_pk)

            # Sort items by created_at (oldest to newest) to maintain chronological order
            items.sort(key=lambda x: x.created_at if x.created_at else datetime.min)
            project.items = items

            # Download each item with index for ordering
            downloads_path = FolderPath(Path(project.folder_path) / "downloads")
            total = len(items)

            # Check for existing partial downloads (for resume)
            already_downloaded = 0
            downloads_dir = Path(project.folder_path) / "downloads"
            if downloads_dir.exists():
                # Count complete files (non-zero size)
                existing_files = {f.name for f in downloads_dir.iterdir() if f.is_file() and f.stat().st_size > 0}
                logger.info(f"Found {len(existing_files)} existing files for resume: {existing_files}")

                # Check each item to see if it's already downloaded
                for idx, item in enumerate(items):
                    timestamp = int(item.created_at.timestamp()) if item.created_at else 0
                    ext = ".mp4" if item.item_type == "video" else ".jpg"
                    expected_filename = f"{idx:04d}_{timestamp}_{item.id}{ext}"

                    if expected_filename in existing_files:
                        already_downloaded += 1
                        item.downloaded_path = str(downloads_dir / expected_filename)
                        logger.info(f"Skipping already downloaded item {idx}: {expected_filename}")

            if already_downloaded > 0:
                logger.info(f"Resuming download: {already_downloaded}/{total} items already complete")
                # Update initial progress
                initial_progress = already_downloaded / total
                project.download_progress = initial_progress
                if progress_callback:
                    progress_callback(initial_progress)

            downloaded_count = already_downloaded
            for idx, item in enumerate(items):
                # Skip if already downloaded
                if item.downloaded_path:
                    continue

                def item_progress(p: float):
                    # Progress = (complete items + current item progress) / total
                    overall = (downloaded_count + p) / total
                    project.download_progress = overall
                    if progress_callback:
                        progress_callback(overall)

                local_path = await self.instagram.download_item(
                    item,
                    downloads_path,
                    item_progress,
                    index=idx  # Pass index for filename ordering
                )
                item.downloaded_path = local_path
                downloaded_count += 1  # Increment after each successful download

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
            safe_title = re.sub(r"[^a-zA-Z0-9._-]+", "_", project.title).strip("_") or "highlight"
            filename = f"{safe_title}_merged.mp4"

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
        owner: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> HighlightProjectDTO:
        """Download a user's highlight"""
        try:
            # Create project folder with owner isolation
            safe_name = highlight.name.replace(" ", "_").replace("/", "_")
            base_path = FolderPath(Path("./data") / owner / "users" / username / safe_name)
            downloads_path, exports_path = self.storage.create_project_folders(base_path)

            # Create project
            project = HighlightProject(
                id=str(highlight.highlight_id),
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


class CreateZipBundleUseCase:
    """Use case for creating ZIP bundle of project artifacts"""

    def __init__(self, file_storage: IFileStorage):
        self.storage = file_storage

    async def execute(
        self,
        project: HighlightProject,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> OperationResultDTO:
        """
        Create ZIP bundle containing downloads and exports.

        Args:
            project: HighlightProject to bundle
            progress_callback: Optional callback for progress updates

        Returns:
            OperationResultDTO with success status and ZIP file path
        """
        import zipfile

        try:
            if project.download_status != DownloadStatus.DOWNLOADED:
                return OperationResultDTO(
                    success=False,
                    message="Project must be downloaded before creating ZIP"
                )

            project_path = Path(project.folder_path)
            downloads_path = project_path / "downloads"
            exports_path = project_path / "exports"

            # Create ZIP filename
            safe_title = re.sub(r"[^a-zA-Z0-9._-]+", "_", project.title).strip("_") or "highlight"
            zip_filename = f"{safe_title}_bundle.zip"
            zip_path = project_path / zip_filename

            # Create ZIP file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                files_added = 0
                total_files = 0

                # Count total files
                if downloads_path.exists():
                    total_files += sum(1 for f in downloads_path.iterdir() if f.is_file())
                if exports_path.exists():
                    total_files += sum(1 for f in exports_path.iterdir() if f.is_file())

                # Add downloads
                if downloads_path.exists():
                    for file in downloads_path.iterdir():
                        if file.is_file():
                            zipf.write(file, f"downloads/{file.name}")
                            files_added += 1
                            if progress_callback and total_files > 0:
                                progress_callback(files_added / total_files)

                # Add exports
                if exports_path.exists():
                    for file in exports_path.iterdir():
                        if file.is_file():
                            zipf.write(file, f"exports/{file.name}")
                            files_added += 1
                            if progress_callback and total_files > 0:
                                progress_callback(files_added / total_files)

            if progress_callback:
                progress_callback(1.0)

            return OperationResultDTO(
                success=True,
                message=f"ZIP bundle created with {files_added} files",
                data=str(zip_path)
            )

        except Exception as e:
            return OperationResultDTO(
                success=False,
                message=f"Failed to create ZIP bundle: {str(e)}"
            )


class OpenExportsFolderUseCase:
    """Use case for opening exports folder"""

    def __init__(self, file_storage: IFileStorage):
        self.storage = file_storage

    def execute(self, folder_path: str, subfolder: str = "exports") -> None:
        """Open a project's exports or downloads folder"""
        path = FolderPath(Path(folder_path) / subfolder)
        self.storage.open_folder_in_explorer(path)
