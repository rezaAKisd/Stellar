"""Pydantic schemas for API request/response validation"""
from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Authentication Schemas
# ============================================================================

class LoginRequest(BaseModel):
    """Login request schema"""
    username: str = Field(..., min_length=1, description="Instagram username")
    password: str = Field(..., min_length=6, description="Instagram password")


class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    token_type: str = "bearer"
    username: str
    needs_2fa: bool = False


class Verify2FARequest(BaseModel):
    """2FA verification request schema"""
    username: str
    password: str
    code: str = Field(..., min_length=6, max_length=6, description="6-digit 2FA code")
    trust_device: bool = False


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
    username: str


class UserResponse(BaseModel):
    """Current user response schema"""
    username: str
    is_authenticated: bool


class MessageResponse(BaseModel):
    """Generic message response schema"""
    message: str


# ============================================================================
# Highlight Project Schemas
# ============================================================================

class AddLinkRequest(BaseModel):
    """Add highlight link request schema"""
    url: str = Field(..., description="Instagram highlight URL")


class HighlightProjectResponse(BaseModel):
    """Highlight project response schema"""
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
    has_downloads: bool
    has_exports: bool
    video_urls: Optional[str] = None
    photo_urls: Optional[str] = None
    merged_video_url: Optional[str] = None
    zip_bundle_url: Optional[str] = None
    expires_at: Optional[str] = None
    is_expired: int = 0


class HighlightProjectsResponse(BaseModel):
    """List of highlight projects response schema"""
    projects: List[HighlightProjectResponse]


class TaskStartedResponse(BaseModel):
    """Task started response schema"""
    message: str
    task_id: Optional[str] = None


# ============================================================================
# User Schemas
# ============================================================================

class AddUserRequest(BaseModel):
    """Add user request schema"""
    username: str = Field(..., min_length=1, description="Instagram username")


class UserHighlightResponse(BaseModel):
    """User highlight response schema"""
    id: str
    name: str
    cover_url: str
    item_count: int
    highlight_id: str
    project_id: Optional[str] = None


class UserHighlightsResponse(BaseModel):
    """List of user highlights response schema"""
    highlights: List[UserHighlightResponse]


class UserProfileResponse(BaseModel):
    """User profile response schema"""
    id: str
    username: str
    display_name: str
    avatar_url: str
    highlights: List[UserHighlightResponse] = []


class UsersResponse(BaseModel):
    """List of users response schema"""
    users: List[UserProfileResponse]


# ============================================================================
# WebSocket Schemas
# ============================================================================

class WebSocketMessage(BaseModel):
    """WebSocket message schema"""
    type: str  # download_progress, export_progress, task_complete, error
    project_id: str
    progress: Optional[float] = None
    status: Optional[str] = None
    message: Optional[str] = None


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response schema"""
    detail: str
    code: Optional[str] = None
