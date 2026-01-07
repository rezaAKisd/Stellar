"""Users API routes - Username-based highlight management"""
import logging
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from ..schemas import (
    AddUserRequest,
    UserProfileResponse,
    UsersResponse,
    UserHighlightsResponse,
    UserHighlightResponse,
    TaskStartedResponse,
    MessageResponse
)
from ..dependencies import get_instagram_gateway, get_file_storage
from ...core.security import get_current_user
from ...app.application.use_cases import (
    AddUsernameUseCase,
    LoadUserHighlightsUseCase,
    DownloadUserHighlightUseCase
)
from ...app.domain.entities import UserProfile, UserHighlight

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for users (in production, use database)
# Key: current_user -> List[UserProfile]
_user_profiles: dict[str, List[UserProfile]] = {}


def _profile_to_response(profile: UserProfile) -> UserProfileResponse:
    """Convert UserProfile entity to API response"""
    return UserProfileResponse(
        id=profile.id,
        username=profile.username,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        highlights=[
            UserHighlightResponse(
                id=h.id,
                name=h.name,
                cover_url=h.cover_url,
                item_count=h.item_count,
                highlight_id=h.highlight_id,
                project_id=h.project_id
            )
            for h in profile.highlights
        ]
    )


@router.post("/add", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def add_user(
    request: AddUserRequest,
    current_user: str = Depends(get_current_user),
    instagram_gateway = Depends(get_instagram_gateway),
    file_storage = Depends(get_file_storage)
):
    """
    Add a new Instagram user to track.

    Returns the user profile.
    """
    try:
        logger.info(f"Adding user for {current_user}: {request.username}")

        # Execute use case
        add_uc = AddUsernameUseCase(instagram_gateway, file_storage)
        profile_dto = await add_uc.execute(request.username)

        # Create domain entity from DTO
        profile = UserProfile(
            id=profile_dto.id,
            username=profile_dto.username,
            display_name=profile_dto.display_name,
            avatar_url=profile_dto.avatar_url,
            highlights=[]
        )

        # Store in memory
        if current_user not in _user_profiles:
            _user_profiles[current_user] = []
        _user_profiles[current_user].append(profile)

        logger.info(f"User added successfully: {profile.username}")
        return _profile_to_response(profile)

    except ValueError as e:
        logger.warning(f"Invalid username: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add user: {str(e)}"
        )


@router.get("", response_model=UsersResponse)
async def get_users(
    current_user: str = Depends(get_current_user)
):
    """
    Get all tracked users for the current user.
    """
    try:
        profiles = _user_profiles.get(current_user, [])

        return UsersResponse(
            users=[_profile_to_response(p) for p in profiles]
        )

    except Exception as e:
        logger.error(f"Error getting users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get users: {str(e)}"
        )


@router.get("/{username}/highlights", response_model=UserHighlightsResponse)
async def get_user_highlights(
    username: str,
    current_user: str = Depends(get_current_user),
    instagram_gateway = Depends(get_instagram_gateway)
):
    """
    Load all highlights for a specific user.

    This fetches the latest highlights from Instagram.
    """
    try:
        logger.info(f"Loading highlights for user: {username}")

        # Execute use case
        load_uc = LoadUserHighlightsUseCase(instagram_gateway)
        highlights_dtos = await load_uc.execute(username)

        # Convert to response
        highlights = [
            UserHighlightResponse(
                id=h.id,
                name=h.name,
                cover_url=h.cover_url,
                item_count=h.item_count,
                highlight_id=h.highlight_id,
                project_id=h.project_id
            )
            for h in highlights_dtos
        ]

        # Update stored profile
        for profile in _user_profiles.get(current_user, []):
            if profile.username == username:
                profile.highlights = [
                    UserHighlight(
                        id=h.id,
                        name=h.name,
                        cover_url=h.cover_url,
                        item_count=h.item_count,
                        highlight_id=h.highlight_id,
                        project_id=h.project_id
                    )
                    for h in highlights_dtos
                ]
                break

        logger.info(f"Loaded {len(highlights)} highlights for {username}")

        return UserHighlightsResponse(highlights=highlights)

    except ValueError as e:
        logger.warning(f"Error loading highlights: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error loading highlights: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load highlights: {str(e)}"
        )


async def _download_user_highlight_task(
    username: str,
    highlight_id: str,
    task_id: str,
    user: str,
    instagram_gateway,
    file_storage
):
    """Background task for downloading user highlight"""
    from ..websockets.progress import broadcast_progress

    try:
        logger.info(f"Starting user highlight download task {task_id}")

        # Find highlight
        highlight_dto = None
        for profile in _user_profiles.get(user, []):
            if profile.username == username:
                for h in profile.highlights:
                    if h.highlight_id == highlight_id:
                        from ...app.application.dtos import UserHighlightDTO
                        highlight_dto = UserHighlightDTO(
                            id=h.id,
                            name=h.name,
                            cover_url=h.cover_url,
                            item_count=h.item_count,
                            highlight_id=h.highlight_id,
                            project_id=h.project_id
                        )
                        break
                break

        if not highlight_dto:
            logger.error(f"Highlight {highlight_id} not found")
            await broadcast_progress(
                user, highlight_id, "error",
                message="Highlight not found"
            )
            return

        # Execute download use case with WebSocket progress updates
        download_uc = DownloadUserHighlightUseCase(instagram_gateway, file_storage)

        def progress_callback(progress: float):
            """Send progress updates via WebSocket"""
            import asyncio
            asyncio.create_task(broadcast_progress(
                user, highlight_id, "download_progress",
                progress=progress,
                status="downloading"
            ))

        result = await download_uc.execute(username, highlight_dto, progress_callback)

        logger.info(f"User highlight download completed: {result.id}")
        await broadcast_progress(
            user, highlight_id, "task_complete",
            status="downloaded",
            message=f"Downloaded highlight '{highlight_dto.name}'"
        )

    except Exception as e:
        logger.error(f"User highlight download task error: {str(e)}", exc_info=True)
        await broadcast_progress(
            user, highlight_id, "error",
            message=f"Download error: {str(e)}"
        )


@router.post("/{username}/highlights/{highlight_id}/download",
             response_model=TaskStartedResponse,
             status_code=status.HTTP_202_ACCEPTED)
async def download_user_highlight(
    username: str,
    highlight_id: str,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    instagram_gateway = Depends(get_instagram_gateway),
    file_storage = Depends(get_file_storage)
):
    """
    Start downloading a user's highlight in the background.

    Returns a task ID for tracking progress (via WebSocket in Phase 4).
    """
    try:
        # Verify highlight exists
        highlight_found = False
        for profile in _user_profiles.get(current_user, []):
            if profile.username == username:
                for h in profile.highlights:
                    if h.highlight_id == highlight_id:
                        highlight_found = True
                        break
                break

        if not highlight_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Highlight {highlight_id} not found for user {username}"
            )

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Add background task
        background_tasks.add_task(
            _download_user_highlight_task,
            username,
            highlight_id,
            task_id,
            current_user,
            instagram_gateway,
            file_storage
        )

        logger.info(f"User highlight download task {task_id} queued")

        return TaskStartedResponse(
            message="Download started",
            task_id=task_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting user highlight download: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start download: {str(e)}"
        )


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Delete a tracked user.
    """
    try:
        # Find and remove user
        profiles = _user_profiles.get(current_user, [])
        profile = None

        for i, p in enumerate(profiles):
            if p.id == user_id:
                profile = profiles.pop(i)
                break

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        logger.info(f"User {user_id} deleted")

        return MessageResponse(message="User deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )
