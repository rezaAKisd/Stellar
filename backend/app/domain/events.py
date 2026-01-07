"""Domain Events - Business events that occur in the domain"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DomainEvent:
    """Base domain event"""
    occurred_at: datetime = datetime.now()


@dataclass
class DownloadCompleted(DomainEvent):
    """Raised when a download completes successfully"""
    project_id: str
    item_count: int
    downloads_path: str


@dataclass
class DownloadFailed(DomainEvent):
    """Raised when a download fails"""
    project_id: str
    error_message: str


@dataclass
class ExportCompleted(DomainEvent):
    """Raised when an export completes successfully"""
    project_id: str
    output_path: str
    file_size_mb: float


@dataclass
class ExportFailed(DomainEvent):
    """Raised when an export fails"""
    project_id: str
    error_message: str


@dataclass
class SessionConnected(DomainEvent):
    """Raised when session is successfully connected"""
    session_valid: bool


@dataclass
class SessionDisconnected(DomainEvent):
    """Raised when session is disconnected"""
    pass
