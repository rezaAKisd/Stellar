"""Domain Entities - Core business objects with identity"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from datetime import datetime
import uuid


class DownloadStatus(Enum):
    """Status of a download operation"""
    IDLE = "idle"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    ERROR = "error"


class ExportStatus(Enum):
    """Status of an export operation"""
    NOT_STARTED = "not_started"
    BUILDING = "building"
    EXPORTED = "exported"
    ERROR = "error"


@dataclass
class HighlightItem:
    """Single item within a highlight (photo or video)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    item_type: str = "image"  # "image" or "video"
    url: str = ""
    thumbnail_url: str = ""
    downloaded_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class HighlightProject:
    """A highlight being managed (from link or username)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    source: str = ""  # URL or @username
    folder_path: str = ""
    items: List[HighlightItem] = field(default_factory=list)
    download_status: DownloadStatus = DownloadStatus.IDLE
    export_status: ExportStatus = ExportStatus.NOT_STARTED
    download_progress: float = 0.0  # 0.0 to 1.0
    export_progress: float = 0.0  # 0.0 to 1.0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def has_downloads(self) -> bool:
        return self.download_status == DownloadStatus.DOWNLOADED

    @property
    def has_exports(self) -> bool:
        return self.export_status == ExportStatus.EXPORTED


@dataclass
class UserProfile:
    """Instagram user profile"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""
    display_name: str = ""
    avatar_url: str = ""
    highlights: List['UserHighlight'] = field(default_factory=list)
    added_at: datetime = field(default_factory=datetime.now)


@dataclass
class UserHighlight:
    """A highlight belonging to a user"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    cover_url: str = ""
    item_count: int = 0
    highlight_id: str = ""  # Instagram's highlight ID
    project_id: Optional[str] = None  # Links to HighlightProject if downloaded


@dataclass
class DownloadItem:
    """Represents a download task"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    item: HighlightItem = field(default_factory=HighlightItem)
    status: DownloadStatus = DownloadStatus.IDLE
    progress: float = 0.0


@dataclass
class ExportJob:
    """Video export job"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    output_path: str = ""
    status: ExportStatus = ExportStatus.NOT_STARTED
    progress: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
