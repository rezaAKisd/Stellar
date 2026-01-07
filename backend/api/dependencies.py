"""FastAPI dependencies for dependency injection"""
from pathlib import Path
from functools import lru_cache
from typing import Optional

from ..core.config import settings


# Global dependency container instance
_container: Optional["DependencyContainer"] = None


def get_container() -> "DependencyContainer":
    """
    Get or create the global DependencyContainer instance.

    Returns:
        DependencyContainer instance
    """
    global _container

    if _container is None:
        # Import here to avoid circular dependencies
        from ..app.infrastructure.container import DependencyContainer

        _container = DependencyContainer(
            session_dir=settings.SESSION_DIR,
            data_dir=settings.DATA_DIR
        )

    return _container


@lru_cache()
def get_instagram_gateway():
    """
    Get the Instagram gateway instance.

    Returns:
        IInstagramGateway instance
    """
    container = get_container()
    return container.instagram_gateway


@lru_cache()
def get_file_storage():
    """
    Get the file storage instance.

    Returns:
        IFileStorage instance
    """
    container = get_container()
    return container.file_storage


@lru_cache()
def get_video_composer():
    """
    Get the video composer instance.

    Returns:
        IVideoComposer instance
    """
    container = get_container()
    return container.video_composer
