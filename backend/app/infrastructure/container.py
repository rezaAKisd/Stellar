"""Dependency Injection Container - Centralized service management"""
from pathlib import Path
from typing import Optional

from ..domain.interfaces import IInstagramGateway, IFileStorage, IVideoComposer


class DependencyContainer:
    """Centralized dependency injection container for infrastructure services"""

    def __init__(self, session_dir: Path, data_dir: Path):
        """
        Initialize the dependency container.

        Args:
            session_dir: Directory for session storage
            data_dir: Directory for data storage
        """
        self.session_dir = session_dir
        self.data_dir = data_dir

        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Infrastructure service instances (lazy-loaded singletons)
        self._instagram_gateway: Optional[IInstagramGateway] = None
        self._file_storage: Optional[IFileStorage] = None
        self._video_composer: Optional[IVideoComposer] = None

    @property
    def instagram_gateway(self) -> IInstagramGateway:
        """Get Instagram gateway instance (singleton)"""
        if self._instagram_gateway is None:
            # Import here to avoid circular dependencies
            from .instagram_aiograpi import InstagramGatewayAiograpi
            self._instagram_gateway = InstagramGatewayAiograpi(self.session_dir)
        return self._instagram_gateway

    @property
    def file_storage(self) -> IFileStorage:
        """Get file storage instance (singleton)"""
        if self._file_storage is None:
            from .storage_local import FileStorageLocal
            self._file_storage = FileStorageLocal()
        return self._file_storage

    @property
    def video_composer(self) -> IVideoComposer:
        """Get video composer instance (singleton)"""
        if self._video_composer is None:
            from .video_composer import VideoComposer
            self._video_composer = VideoComposer()
        return self._video_composer

    def reset(self):
        """Reset all service instances (useful for testing)"""
        self._instagram_gateway = None
        self._file_storage = None
        self._video_composer = None
