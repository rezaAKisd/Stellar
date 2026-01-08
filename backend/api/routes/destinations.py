"""Destination usernames API routes - Username/Playlists tab functionality"""
import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.security import get_current_user
from api.dependencies import get_instagram_gateway, get_state_db
from app.infrastructure.state_db import StateDB, DestinationUsernameRow, DestinationHighlightRow
from app.domain.value_objects import Username

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Schemas
class AddDestinationUsernameRequest(BaseModel):
    username: str


class DestinationUsernameResponse(BaseModel):
    id: str
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    last_fetched_at: Optional[str]
    created_at: str


class DestinationUsernamesResponse(BaseModel):
    destinations: List[DestinationUsernameResponse]


class DestinationHighlightResponse(BaseModel):
    id: str
    highlight_id: str
    name: str
    cover_url: Optional[str]
    item_count: int
    project_id: Optional[str]


class DestinationHighlightsResponse(BaseModel):
    highlights: List[DestinationHighlightResponse]


class MessageResponse(BaseModel):
    message: str


def _username_to_response(row: DestinationUsernameRow) -> DestinationUsernameResponse:
    return DestinationUsernameResponse(
        id=row.id,
        username=row.username,
        display_name=row.display_name,
        avatar_url=row.avatar_url,
        last_fetched_at=row.last_fetched_at,
        created_at=row.created_at,
    )


def _highlight_to_response(row: DestinationHighlightRow) -> DestinationHighlightResponse:
    return DestinationHighlightResponse(
        id=row.id,
        highlight_id=row.highlight_id,
        name=row.name,
        cover_url=row.cover_url,
        item_count=row.item_count,
        project_id=row.project_id,
    )


@router.post("/add", response_model=DestinationUsernameResponse, status_code=status.HTTP_201_CREATED)
async def add_destination_username(
    request: AddDestinationUsernameRequest,
    current_user: str = Depends(get_current_user),
    instagram_gateway = Depends(get_instagram_gateway),
    db: StateDB = Depends(get_state_db),
):
    """
    Add a destination username to track.

    Creates a new destination username entry for the current user.
    Optionally fetches basic profile info from Instagram.
    """
    try:
        # Validate username format
        username = Username(request.username)
        logger.info(f"Adding destination username for user {current_user}: {username}")

        # Check if already exists (will be handled by UNIQUE constraint, but check first for better error message)
        existing_usernames = db.list_destination_usernames(current_user)
        if any(u.username == str(username) for u in existing_usernames):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Destination username '@{username}' already exists"
            )

        # Create destination username entry
        username_id = db.upsert_destination_username(
            owner=current_user,
            username=str(username),
            display_name=str(username),  # Will be updated when highlights are fetched
            avatar_url=None,
        )

        # Get the created record
        destination = db.get_destination_username(current_user, username_id)
        if not destination:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create destination username"
            )

        logger.info(f"Destination username added successfully: {username_id}")
        return _username_to_response(destination)

    except ValueError as e:
        logger.warning(f"Invalid username format: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding destination username: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add destination username: {str(e)}"
        )


@router.get("", response_model=DestinationUsernamesResponse)
async def list_destination_usernames(
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Get all destination usernames for the current user.

    Returns a list of all destination usernames added by the user.
    """
    try:
        destinations = db.list_destination_usernames(current_user)
        return DestinationUsernamesResponse(
            destinations=[_username_to_response(d) for d in destinations]
        )
    except Exception as e:
        logger.error(f"Error listing destination usernames: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list destination usernames: {str(e)}"
        )


@router.post("/{username_id}/fetch-highlights", response_model=DestinationHighlightsResponse)
async def fetch_destination_highlights(
    username_id: str,
    current_user: str = Depends(get_current_user),
    instagram_gateway = Depends(get_instagram_gateway),
    db: StateDB = Depends(get_state_db),
):
    """
    Fetch highlights for a destination username from Instagram.

    Retrieves all available highlights for the specified Instagram account
    and caches them in the database.
    """
    try:
        # Get destination username
        destination = db.get_destination_username(current_user, username_id)
        if not destination:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Destination username not found"
            )

        logger.info(f"Fetching highlights for destination {destination.username}")

        # Fetch highlights from Instagram
        username = Username(destination.username)
        highlights = await instagram_gateway.fetch_user_highlights(username)

        # Convert to dict format for database storage
        highlights_data = [
            {
                "instagram_username": destination.username,
                "highlight_id": h.highlight_id,
                "name": h.name,
                "cover_url": h.cover_url,
                "item_count": h.item_count,
            }
            for h in highlights
        ]

        # Bulk upsert highlights
        count = db.upsert_destination_highlights(current_user, username_id, highlights_data)

        # Update last_fetched_at timestamp
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        db.upsert_destination_username(
            owner=current_user,
            username=destination.username,
            username_id=username_id,
            last_fetched_at=now,
        )

        # Get the stored highlights
        stored_highlights = db.list_destination_highlights(current_user, username_id)

        logger.info(f"Fetched and stored {count} highlights for {destination.username}")

        return DestinationHighlightsResponse(
            highlights=[_highlight_to_response(h) for h in stored_highlights]
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Instagram fetch error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch highlights from Instagram: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error fetching highlights: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch highlights: {str(e)}"
        )


@router.get("/{username_id}/highlights", response_model=DestinationHighlightsResponse)
async def get_destination_highlights(
    username_id: str,
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Get cached highlights for a destination username.

    Returns highlights that have been previously fetched from Instagram.
    Does not make a new Instagram API call.
    """
    try:
        # Verify destination exists and belongs to user
        destination = db.get_destination_username(current_user, username_id)
        if not destination:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Destination username not found"
            )

        # Get cached highlights
        highlights = db.list_destination_highlights(current_user, username_id)

        return DestinationHighlightsResponse(
            highlights=[_highlight_to_response(h) for h in highlights]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting highlights: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get highlights: {str(e)}"
        )


@router.post("/{username_id}/highlights/{highlight_id}/download")
async def download_destination_highlight(
    username_id: str,
    highlight_id: str,
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Download a destination highlight (creates project + enqueues task).

    This creates a new project for the highlight and queues a download task,
    similar to adding a highlight via direct link.
    """
    try:
        # Verify destination exists
        destination = db.get_destination_username(current_user, username_id)
        if not destination:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Destination username not found"
            )

        # Get the specific highlight
        highlights = db.list_destination_highlights(current_user, username_id)
        highlight = next((h for h in highlights if h.highlight_id == highlight_id), None)

        if not highlight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Highlight not found"
            )

        logger.info(f"Downloading destination highlight {highlight_id} for user {current_user}")

        # Check if already downloaded (has project_id)
        if highlight.project_id:
            logger.info(f"Highlight already downloaded: project {highlight.project_id}")
            return {
                "message": "Highlight already downloaded",
                "project_id": highlight.project_id
            }

        # Create project for this highlight
        from datetime import datetime, timezone
        project_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        expires_at = db.calculate_expiration_date(created_at)
        submission_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Create folder path
        from pathlib import Path
        safe_name = highlight.name.replace(" ", "_").replace("/", "_")
        folder_path = str(Path("./data") / current_user / "destinations" / destination.username / safe_name)

        db.upsert_project(
            owner=current_user,
            project_id=project_id,
            title=highlight.name,
            source=f"@{destination.username}/{highlight_id}",
            folder_path=folder_path,
            item_count=highlight.item_count,
            download_status="queued",
            export_status="not_started",
            expires_at=expires_at,
            submission_date=submission_date,
        )

        # Enqueue download task
        task_id = str(uuid.uuid4())
        db.enqueue_task(
            task_id=task_id,
            owner=current_user,
            project_id=project_id,
            task_type="download",
            message="Download queued"
        )

        # Link highlight to project
        db.link_highlight_to_project(current_user, highlight_id, project_id)

        logger.info(f"Download task {task_id} queued for destination highlight {highlight_id}")

        return {
            "message": "Download queued",
            "project_id": project_id,
            "task_id": task_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading destination highlight: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download highlight: {str(e)}"
        )


@router.delete("/{username_id}", response_model=MessageResponse)
async def delete_destination_username(
    username_id: str,
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Delete a destination username (cascades to highlights).

    Removes the destination username and all associated cached highlights.
    Does not delete any projects that were created from downloading highlights.
    """
    try:
        deleted = db.delete_destination_username(current_user, username_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Destination username not found"
            )

        logger.info(f"Destination username {username_id} deleted")
        return MessageResponse(message="Destination username deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting destination username: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete destination username: {str(e)}"
        )
