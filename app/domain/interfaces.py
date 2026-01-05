"""Domain Service Interfaces - Abstract contracts"""
from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from .entities import HighlightProject, UserProfile, UserHighlight, HighlightItem
from .value_objects import HighlightUrl, Username, FolderPath, SessionToken


class IInstagramGateway(ABC):
    """Interface for Instagram data access"""

    @abstractmethod
    async def authenticate_with_session(self, token: SessionToken) -> bool:
        """Authenticate using session token"""
        pass

    @abstractmethod
    async def fetch_user_highlights(self, username: Username) -> List[UserHighlight]:
        """Fetch all highlights for a user"""
        pass

    @abstractmethod
    async def fetch_highlight_metadata(self, url: HighlightUrl) -> dict:
        """Fetch metadata for a highlight from URL"""
        pass

    @abstractmethod
    async def fetch_highlight_items(self, highlight_id: str) -> List[HighlightItem]:
        """Fetch all items in a highlight"""
        pass

    @abstractmethod
    async def download_item(
        self,
        item: HighlightItem,
        destination: FolderPath,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """Download a single item, returns local path"""
        pass


class IFileStorage(ABC):
    """Interface for file system operations"""

    @abstractmethod
    def create_project_folders(self, base_path: FolderPath) -> tuple[FolderPath, FolderPath]:
        """Create downloads/ and exports/ folders, returns (downloads_path, exports_path)"""
        pass

    @abstractmethod
    def save_media(self, data: bytes, path: FolderPath, filename: str) -> str:
        """Save media file, returns full path"""
        pass

    @abstractmethod
    def list_exports(self, exports_path: FolderPath) -> List[str]:
        """List all export files"""
        pass

    @abstractmethod
    def open_folder_in_explorer(self, path: FolderPath) -> None:
        """Open folder in OS file explorer"""
        pass

    @abstractmethod
    def save_session(self, token: SessionToken) -> None:
        """Save session token securely"""
        pass

    @abstractmethod
    def load_session(self) -> Optional[SessionToken]:
        """Load saved session token"""
        pass


class IVideoComposer(ABC):
    """Interface for video composition"""

    @abstractmethod
    async def merge_items_to_video(
        self,
        items: List[HighlightItem],
        output_path: FolderPath,
        filename: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """Merge items into a single video, returns output path"""
        pass

    @abstractmethod
    async def export_separate_clips(
        self,
        items: List[HighlightItem],
        output_path: FolderPath,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> List[str]:
        """Export items as separate clips, returns list of paths"""
        pass
