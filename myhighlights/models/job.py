"""Job models for highlight downloads and exports"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from pathlib import Path
import uuid


class JobStatus(Enum):
    """Job status states"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    DOWNLOADED = "downloaded"
    BUILDING = "building"
    BUILD_CANCELLED = "cancelled"
    EXPORTED = "exported"
    ERROR = "error"


@dataclass
class HighlightItem:
    """Single media item in a highlight"""
    url: str
    type: str  # 'image' or 'video'
    thumbnail_url: str
    local_path: Optional[str] = None
    downloaded: bool = False

    def to_dict(self) -> dict:
        """Serialize item for persistence."""
        return {
            "url": self.url,
            "type": self.type,
            "thumbnail_url": self.thumbnail_url,
            "local_path": self.local_path,
            "downloaded": self.downloaded,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HighlightItem":
        """Deserialize item from persistence."""
        return cls(
            url=data.get("url", ""),
            type=data.get("type", "image"),
            thumbnail_url=data.get("thumbnail_url", ""),
            local_path=data.get("local_path"),
            downloaded=bool(data.get("downloaded", False)),
        )


@dataclass
class HighlightJob:
    """A highlight download/export job"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    source_url: str = ""
    cover_url: str = ""
    folder_path: Optional[Path] = None

    # Items
    items: List[HighlightItem] = field(default_factory=list)
    total_items: int = 0
    downloaded_items: int = 0

    # Status
    status: JobStatus = JobStatus.PENDING
    download_progress: float = 0.0  # 0-1
    build_progress: float = 0.0     # 0-1
    error_message: Optional[str] = None

    # Progress details
    download_speed: float = 0.0  # bytes/sec
    estimated_time_remaining: int = 0  # seconds
    current_item_progress: float = 0.0  # 0-1 for current item
    current_item_index: int = 0  # which item is being downloaded
    build_stage: str = ""  # e.g., "Processing video 1/10"

    # Paths
    downloads_folder: Optional[Path] = None
    exports_folder: Optional[Path] = None
    output_video_path: Optional[Path] = None

    # Control flags
    should_pause: bool = False
    should_cancel: bool = False

    def __post_init__(self):
        """Initialize folder path if not set"""
        if self.folder_path is None and self.title:
            safe_title = "".join(c for c in self.title if c.isalnum() or c in (' ', '_')).rstrip()
            safe_title = safe_title.replace(' ', '_')
            from ..core.config import Config
            self.folder_path = Config.HIGHLIGHTS_DIR / safe_title

    def to_dict(self) -> dict:
        """Serialize job for persistence."""
        return {
            "id": self.id,
            "title": self.title,
            "source_url": self.source_url,
            "cover_url": self.cover_url,
            "folder_path": str(self.folder_path) if self.folder_path else None,
            "items": [item.to_dict() for item in self.items],
            "total_items": self.total_items,
            "downloaded_items": self.downloaded_items,
            "status": self.status.value if self.status else JobStatus.PENDING.value,
            "download_progress": self.download_progress,
            "build_progress": self.build_progress,
            "error_message": self.error_message,
            "download_speed": self.download_speed,
            "estimated_time_remaining": self.estimated_time_remaining,
            "current_item_progress": self.current_item_progress,
            "current_item_index": self.current_item_index,
            "build_stage": self.build_stage,
            "downloads_folder": str(self.downloads_folder) if self.downloads_folder else None,
            "exports_folder": str(self.exports_folder) if self.exports_folder else None,
            "output_video_path": str(self.output_video_path) if self.output_video_path else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HighlightJob":
        """Deserialize job from persistence."""
        try:
            status = JobStatus(data.get("status", JobStatus.PENDING.value))
        except Exception:
            status = JobStatus.PENDING
        job = cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            source_url=data.get("source_url", ""),
            cover_url=data.get("cover_url", ""),
            folder_path=Path(data["folder_path"]) if data.get("folder_path") else None,
            items=[HighlightItem.from_dict(item) for item in data.get("items", [])],
            total_items=int(data.get("total_items", 0)),
            downloaded_items=int(data.get("downloaded_items", 0)),
            status=status,
            download_progress=float(data.get("download_progress", 0.0)),
            build_progress=float(data.get("build_progress", 0.0)),
            error_message=data.get("error_message"),
            download_speed=float(data.get("download_speed", 0.0)),
            estimated_time_remaining=int(data.get("estimated_time_remaining", 0)),
            current_item_progress=float(data.get("current_item_progress", 0.0)),
            current_item_index=int(data.get("current_item_index", 0)),
            build_stage=data.get("build_stage", ""),
            downloads_folder=Path(data["downloads_folder"]) if data.get("downloads_folder") else None,
            exports_folder=Path(data["exports_folder"]) if data.get("exports_folder") else None,
            output_video_path=Path(data["output_video_path"]) if data.get("output_video_path") else None,
        )
        return job
