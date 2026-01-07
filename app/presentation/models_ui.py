"""UI State Models - Frontend state representation"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ViewMode(Enum):
    """Current view mode"""
    AUTH = "auth"
    MAIN = "main"
    USER_DETAIL = "user_detail"


class AuthScreen(Enum):
    """Authentication screen states"""
    SIGN_IN = "sign_in"
    TWO_FACTOR = "two_factor"
    AUTHENTICATED = "authenticated"


class StatusType(Enum):
    """Status types for pills"""
    IDLE = "Idle"
    DOWNLOADING = "Downloading"
    DOWNLOADED = "Downloaded"
    BUILDING = "Building"
    EXPORTED = "Exported"
    ERROR = "Error"


@dataclass
class ConnectionState:
    """Connection status state"""
    is_connected: bool = False
    session_present: bool = False
    status_text: str = "Not connected"


@dataclass
class HighlightRowState:
    """State for a single highlight row in link tab"""
    id: str
    title: str
    source: str
    folder_path: str
    item_count: int
    status: StatusType
    download_progress: float = 0.0
    export_progress: float = 0.0
    error_message: Optional[str] = None
    has_downloads: bool = False
    has_exports: bool = False

    @property
    def status_text(self) -> str:
        return self.status.value

    @property
    def can_build_video(self) -> bool:
        return self.status == StatusType.DOWNLOADED or self.status == StatusType.EXPORTED

    @property
    def can_retry(self) -> bool:
        return self.status == StatusType.ERROR

    @property
    def is_busy(self) -> bool:
        return self.status in [StatusType.DOWNLOADING, StatusType.BUILDING]


@dataclass
class UserRowState:
    """State for a single user row in username tab"""
    id: str
    username: str
    display_name: str
    avatar_url: str = ""
    metadata_text: str = "Tap to view highlights"


@dataclass
class UserHighlightCardState:
    """State for a highlight card in user detail view"""
    id: str
    name: str
    cover_url: str
    item_count: int
    highlight_id: str
    status: StatusType = StatusType.IDLE
    download_progress: float = 0.0
    export_progress: float = 0.0
    project_id: Optional[str] = None
    folder_path: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def status_text(self) -> str:
        return self.status.value

    @property
    def can_download(self) -> bool:
        return self.status in [StatusType.IDLE, StatusType.ERROR]

    @property
    def can_build_video(self) -> bool:
        return self.status == StatusType.DOWNLOADED or self.status == StatusType.EXPORTED

    @property
    def has_downloads(self) -> bool:
        return self.status in [StatusType.DOWNLOADED, StatusType.BUILDING, StatusType.EXPORTED]

    @property
    def has_exports(self) -> bool:
        return self.status == StatusType.EXPORTED

    @property
    def is_busy(self) -> bool:
        return self.status in [StatusType.DOWNLOADING, StatusType.BUILDING]


@dataclass
class UserDetailState:
    """State for user detail view"""
    is_open: bool = False
    username: str = ""
    highlights: List[UserHighlightCardState] = field(default_factory=list)
    is_loading: bool = False


@dataclass
class ToastMessage:
    """Toast notification message"""
    message: str
    type: str = "info"  # info, success, error


@dataclass
class SignInState:
    """State for sign-in screen"""
    username: str = ""
    password: str = ""
    password_visible: bool = False
    remember_device: bool = False
    is_loading: bool = False
    error_message: Optional[str] = None


@dataclass
class TwoFactorState:
    """State for 2FA screen"""
    code_digits: List[str] = field(default_factory=lambda: [""] * 6)
    trust_device: bool = False
    is_loading: bool = False
    error_message: Optional[str] = None
    username: str = ""
    password: str = ""  # Store temporarily for 2FA verification


@dataclass
class AuthState:
    """Overall authentication state"""
    current_screen: AuthScreen = AuthScreen.SIGN_IN
    is_authenticated: bool = False
    username: Optional[str] = None
    sign_in: SignInState = field(default_factory=SignInState)
    two_factor: TwoFactorState = field(default_factory=TwoFactorState)


@dataclass
class AppUiState:
    """Complete application UI state"""
    auth: AuthState = field(default_factory=AuthState)
    connection: ConnectionState = field(default_factory=ConnectionState)
    link_projects: List[HighlightRowState] = field(default_factory=list)
    users: List[UserRowState] = field(default_factory=list)
    user_detail: UserDetailState = field(default_factory=UserDetailState)
    current_view: ViewMode = ViewMode.AUTH
    toasts: List[ToastMessage] = field(default_factory=list)
    current_user: Optional[str] = None
    status_text: str = "Offline"
    active_downloads: int = 0
    app_version: str = "1.0.0"
