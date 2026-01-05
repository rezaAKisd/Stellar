from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Phase(str, Enum):
    IMPORT = "IMPORT"
    DOWNLOAD = "DOWNLOAD"
    ARRANGE = "ARRANGE"
    SETTINGS = "SETTINGS"
    EXPORT = "EXPORT"


class ExportMode(str, Enum):
    MERGED = "MERGED"
    SEPARATE = "SEPARATE"


class ClipStatus(str, Enum):
    WAITING = "waiting"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class DownloadState(str, Enum):
    IDLE = "idle"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIAL_FAILED = "partial_failed"


class RenderState(str, Enum):
    READY = "ready"
    RENDERING = "rendering"
    DONE = "done"
    ERROR = "error"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    DOWNLOADING = "downloading"
    READY = "ready"
    EXPORTED = "exported"
    ERROR = "error"


class ImportState(str, Enum):
    EMPTY = "empty"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class AuthState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ClipItem:
    id: str
    label: str
    media_type: str
    duration: Optional[int] = None
    status: ClipStatus = ClipStatus.WAITING
    progress: int = 0
    thumbnail_path: Optional[str] = None
    export_separately: bool = False
    selected: bool = False


@dataclass
class VideoSettings:
    preset_name: str = "Classic"
    export_mode: ExportMode = ExportMode.MERGED
    also_create_merged: bool = False
    naming_template: str = "highlight_{index}_{date}"
    aspect_ratio: str = "9:16"
    resolution: str = "1080p"
    fps: int = 30
    transition: str = "Fade"
    still_duration: int = 3
    watermark: bool = False


@dataclass
class ProjectState:
    id: str
    title: str = "Untitled Project"
    link: str = ""
    cover_path: Optional[str] = None
    item_count: int = 0
    last_updated: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    import_state: ImportState = ImportState.EMPTY
    download_state: DownloadState = DownloadState.IDLE
    download_done: bool = False
    render_state: RenderState = RenderState.READY
    download_progress: float = 0.0
    render_progress: float = 0.0
    preview_state: str = "idle"
    settings_dirty: bool = False
    clips: List[ClipItem] = field(default_factory=list)
    settings: VideoSettings = field(default_factory=VideoSettings)
    last_error: str = ""
    storage_used_gb: float = 0.0


@dataclass
class ToastMessage:
    id: str
    message: str
    level: str = "info"


@dataclass
class UIState:
    toasts: List[ToastMessage] = field(default_factory=list)


@dataclass
class AppState:
    phase: Phase = Phase.IMPORT
    current_project_id: Optional[str] = None
    projects: Dict[str, ProjectState] = field(default_factory=dict)
    ui: UIState = field(default_factory=UIState)
    auth_state: AuthState = AuthState.DISCONNECTED
    session_id: Optional[str] = None
    auth_error: str = ""
