"""Authenticated file serving routes - Secure downloads with ownership verification"""
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from core.security import get_current_user
from core.config import settings
from api.dependencies import get_state_db
from app.infrastructure.state_db import StateDB

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/download/{project_id}/{artifact_type}/{filename}")
async def download_artifact(
    project_id: str,
    artifact_type: str,
    filename: str,
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Serve files with authentication and ownership verification.

    Security checks:
    - Verify project belongs to current user
    - Check if project has expired (30-day retention)
    - Validate file path to prevent directory traversal
    - Log download for audit trail

    Args:
        project_id: Project identifier
        artifact_type: Type of artifact (downloads/exports/zip)
        filename: File name to download
        current_user: Authenticated user from JWT
        db: Database instance

    Returns:
        FileResponse with the requested file

    Raises:
        404: Project not found or user doesn't own it
        410: Project artifacts have expired
        403: Access denied (path traversal attempt)
    """
    try:
        # Verify project belongs to current user
        project = db.get_project(current_user, project_id)
        if not project:
            logger.warning(f"User {current_user} attempted to access non-existent project {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Check if expired
        if project.is_expired:
            logger.info(f"User {current_user} attempted to download expired project {project_id}")
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Project artifacts have expired (30-day retention policy)"
            )

        # Construct file path: ./data/{owner}/projects/{project_id}/{artifact_type}/{filename}
        # Note: project.folder_path already includes owner, so we use it directly
        file_path = Path(project.folder_path) / artifact_type / filename

        # Verify file exists
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        # Security: Verify path is within user's data directory
        # This prevents directory traversal attacks (../../../etc/passwd)
        data_dir_resolved = Path(settings.DATA_DIR).resolve()
        file_path_resolved = file_path.resolve()

        if not str(file_path_resolved).startswith(str(data_dir_resolved)):
            logger.error(f"Path traversal attempt detected: {file_path} -> {file_path_resolved}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        # Log download for audit trail
        artifact_url = f"/files/download/{project_id}/{artifact_type}/{filename}"
        db.log_artifact_download(current_user, project_id, artifact_type, artifact_url)

        logger.info(f"Serving file to {current_user}: {project_id}/{artifact_type}/{filename}")

        # Serve file with streaming support for large files
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve file: {str(e)}"
        )
