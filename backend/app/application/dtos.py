"""Data Transfer Objects - Simple data carriers between layers"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class HighlightItemDTO:
    """DTO for highlight item"""
    id: str
    item_type: str
    url: str
    thumbnail_url: str
    downloaded_path: Optional[str] = None


@dataclass
class HighlightProjectDTO:
    """DTO for highlight project"""
    id: str
    title: str
    source: str
    folder_path: str
    item_count: int
    download_status: str
    export_status: str
    download_progress: float
    export_progress: float
    error_message: Optional[str] = None
    has_downloads: bool = False
    has_exports: bool = False


@dataclass
class UserHighlightDTO:
    """DTO for user's highlight"""
    id: str
    name: str
    cover_url: str
    item_count: int
    highlight_id: str
    project_id: Optional[str] = None


@dataclass
class UserProfileDTO:
    """DTO for user profile"""
    id: str
    username: str
    display_name: str
    avatar_url: str
    highlights: List[UserHighlightDTO]


@dataclass
class SessionStatusDTO:
    """DTO for session status"""
    is_connected: bool
    session_present: bool
    message: str = ""


@dataclass
class OperationResultDTO:
    """Generic operation result"""
    success: bool
    message: str
    data: Optional[any] = None


@dataclass
class LoginResultDTO:
    """DTO for login operation result"""
    success: bool
    needs_2fa: bool
    error_message: Optional[str] = None
    username: Optional[str] = None
    session_token: Optional[str] = None


@dataclass
class AuthStatusDTO:
    """DTO for authentication status"""
    is_authenticated: bool
    username: Optional[str] = None
    session_valid: bool = False
