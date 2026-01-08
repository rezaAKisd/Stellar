"""FastAPI dependencies for dependency injection"""
from pathlib import Path
from functools import lru_cache
from typing import Optional

from fastapi import Depends
from core.config import settings
from core.security import get_current_user


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
        from app.infrastructure.container import DependencyContainer

        _container = DependencyContainer(
            session_dir=settings.SESSION_DIR,
            data_dir=settings.DATA_DIR
        )

    return _container


@lru_cache()
def get_state_db():
    from app.infrastructure.state_db import StateDB

    db_path = settings.DATA_DIR / "stellar.sqlite3"
    db = StateDB(db_path)
    db.init_schema()
    return db


def get_instagram_gateway(current_user: str = Depends(get_current_user)):
    """
    Get an Instagram gateway bound to the authenticated user.

    Note: per-user sessions are stored under `settings.SESSION_DIR/<username>/`.
    """
    from app.infrastructure.instagram_aiograpi import InstagramGatewayAiograpi
    from app.domain.value_objects import Username

    safe_username = str(Username(current_user))
    return InstagramGatewayAiograpi(settings.SESSION_DIR / safe_username)


def get_instagram_gateway_for_username(username: str):
    """Get an Instagram gateway bound to an arbitrary username (used for login)."""
    from app.infrastructure.instagram_aiograpi import InstagramGatewayAiograpi
    from app.domain.value_objects import Username

    safe_username = str(Username(username))
    return InstagramGatewayAiograpi(settings.SESSION_DIR / safe_username)


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
