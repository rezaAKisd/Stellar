"""Highlights API routes - Link-based highlight management"""
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from api.schemas import (
    AddLinkRequest,
    HighlightProjectResponse,
    HighlightProjectsResponse,
    TaskStartedResponse,
    MessageResponse
)
from api.dependencies import get_instagram_gateway, get_file_storage, get_video_composer, get_state_db
from core.security import get_current_user
from app.application.use_cases import (
    AddHighlightLinkUseCase,
    DownloadHighlightUseCase,
    BuildVideoUseCase,
    OpenExportsFolderUseCase
)
from app.domain.entities import HighlightProject, DownloadStatus, ExportStatus
from app.infrastructure.state_db import StateDB, ProjectRow

logger = logging.getLogger(__name__)

router = APIRouter()

def _row_to_response(project: ProjectRow) -> HighlightProjectResponse:
    return HighlightProjectResponse(
        id=project.project_id,
        title=project.title,
        source=project.source,
        folder_path=project.folder_path,
        item_count=project.item_count,
        download_status=project.download_status,
        export_status=project.export_status,
        download_progress=project.download_progress,
        export_progress=project.export_progress,
        error_message=project.error_message,
        has_downloads=project.download_status == "downloaded",
        has_exports=project.export_status == "exported",
        video_urls=project.video_urls,
        photo_urls=project.photo_urls,
        merged_video_url=project.merged_video_url,
        zip_bundle_url=project.zip_bundle_url,
        expires_at=project.expires_at,
        is_expired=project.is_expired,
    )


@router.post("/add-link", response_model=HighlightProjectResponse, status_code=status.HTTP_201_CREATED)
async def add_highlight_link(
    request: AddLinkRequest,
    current_user: str = Depends(get_current_user),
    instagram_gateway = Depends(get_instagram_gateway),
    file_storage = Depends(get_file_storage),
    db: StateDB = Depends(get_state_db),
):
    """
    Add a new highlight by Instagram URL.

    Returns the created project with metadata.
    """
    try:
        logger.info(f"Adding highlight link for user {current_user}: {request.url}")

        # Check for duplicate URL (per user)
        if db.check_duplicate_url(current_user, request.url):
            logger.info(f"Duplicate URL blocked for user {current_user}: {request.url}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This highlight URL has already been added"
            )

        # Check and increment daily quota (50 submissions/day per user)
        count, exceeded = db.increment_daily_quota(current_user)
        if exceeded:
            logger.warning(f"Daily quota exceeded for user {current_user}: {count}/50")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily submission limit reached (50/day). Current submissions today: {count}"
            )

        # Execute use case
        add_uc = AddHighlightLinkUseCase(instagram_gateway, file_storage)
        project_dto = await add_uc.execute(request.url, current_user)

        # Create domain entity from DTO
        project = HighlightProject(
            id=project_dto.id,
            title=project_dto.title,
            source=project_dto.source,
            folder_path=project_dto.folder_path,
            download_status=DownloadStatus(project_dto.download_status),
            export_status=ExportStatus(project_dto.export_status)
        )

        # Calculate expiration date (30 days from now)
        from datetime import datetime, timezone
        created_at = datetime.now(timezone.utc).isoformat()
        expires_at = db.calculate_expiration_date(created_at)
        submission_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        db.upsert_project(
            owner=current_user,
            project_id=project.id,
            title=project.title,
            source=project.source,
            folder_path=project.folder_path,
            item_count=project_dto.item_count,
            download_status=project.download_status.value,
            export_status=project.export_status.value,
            download_progress=project.download_progress,
            export_progress=project.export_progress,
            error_message=project.error_message,
            expires_at=expires_at,
            submission_date=submission_date,
        )

        logger.info(f"Highlight added successfully: {project.id}")
        row = db.get_project(current_user, project.id)
        return _row_to_response(row) if row else _row_to_response(
            ProjectRow(
                owner=current_user,
                project_id=project.id,
                title=project.title,
                source=project.source,
                folder_path=project.folder_path,
                item_count=project.item_count,
                download_status=project.download_status.value,
                export_status=project.export_status.value,
                download_progress=project.download_progress,
                export_progress=project.export_progress,
                error_message=project.error_message,
                created_at="",
                updated_at="",
            )
        )

    except ValueError as e:
        message = str(e)
        is_validation_error = "Invalid highlight URL" in message or "Invalid Instagram URL" in message
        status_code = status.HTTP_400_BAD_REQUEST if is_validation_error else status.HTTP_502_BAD_GATEWAY
        logger.warning(f"Add highlight failed: {message}")
        raise HTTPException(status_code=status_code, detail=message)
    except Exception as e:
        logger.error(f"Error adding highlight: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add highlight: {str(e)}"
        )


async def _download_highlight_task(
    project_id: str,
    task_id: str,
    user: str,
    instagram_gateway,
    file_storage
):
    """Background task for downloading highlight"""
    from api.websockets.progress import broadcast_progress
    import asyncio

    try:
        logger.info(f"Starting download task {task_id} for project {project_id}")
        loop = asyncio.get_running_loop()

        # Find project
        project = None
        for p in _user_projects.get(user, []):
            if p.id == project_id:
                project = p
                break

        if not project:
            logger.error(f"Project {project_id} not found")
            await broadcast_progress(
                user, project_id, "error",
                message="Project not found"
            )
            return

        # Execute download use case with WebSocket progress updates
        download_uc = DownloadHighlightUseCase(instagram_gateway, file_storage)

        def progress_callback(progress: float):
            """Send progress updates via WebSocket"""
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(
                    broadcast_progress(
                        user,
                        project_id,
                        "download_progress",
                        progress=progress,
                        status="downloading",
                    )
                )
            )

        result = await download_uc.execute(project, progress_callback)

        if result.success:
            logger.info(f"Download completed for project {project_id}")
            await broadcast_progress(
                user, project_id, "task_complete",
                status="downloaded",
                message="Download completed successfully"
            )
        else:
            logger.error(f"Download failed for project {project_id}: {result.message}")
            await broadcast_progress(
                user, project_id, "error",
                message=result.message
            )

    except Exception as e:
        logger.error(f"Download task error: {str(e)}", exc_info=True)
        await broadcast_progress(
            user, project_id, "error",
            message=f"Download error: {str(e)}"
        )


@router.post("/{project_id}/download", response_model=TaskStartedResponse, status_code=status.HTTP_202_ACCEPTED)
async def download_highlight(
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Start downloading highlight items in the background.

    Returns a task ID for tracking progress (via WebSocket in Phase 4).
    """
    try:
        project = db.get_project(current_user, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        if project.download_status in {"queued", "downloading"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Download already in progress")

        if db.task_exists_active(owner=current_user, project_id=project_id, task_type="download"):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Download already queued")

        # Check concurrent download limit (5 simultaneous per user)
        running_count = db.get_concurrent_task_count(current_user)
        if running_count >= 5:
            logger.warning(f"Concurrent download limit reached for user {current_user}: {running_count}/5")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Maximum concurrent downloads reached (5). Currently running: {running_count}"
            )

        # Generate task ID
        task_id = str(uuid.uuid4())

        db.enqueue_task(task_id=task_id, owner=current_user, project_id=project_id, task_type="download", message="Download queued")
        db.update_project(owner=current_user, project_id=project_id, fields={"download_status": "queued", "download_progress": 0.0, "error_message": None})

        # Broadcast queued status immediately
        from api.websockets.progress import broadcast_progress
        await broadcast_progress(current_user, project_id, "download_progress", progress=0.0, status="queued", task_id=task_id, task_type="download")

        logger.info(f"Download task {task_id} queued for project {project_id}")

        return TaskStartedResponse(
            message="Download queued",
            task_id=task_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start download: {str(e)}"
        )


async def _build_video_task(
    project_id: str,
    task_id: str,
    user: str,
    video_composer,
    file_storage
):
    """Background task for building video"""
    from api.websockets.progress import broadcast_progress
    import asyncio

    try:
        logger.info(f"Starting video build task {task_id} for project {project_id}")
        loop = asyncio.get_running_loop()

        # Find project
        project = None
        for p in _user_projects.get(user, []):
            if p.id == project_id:
                project = p
                break

        if not project:
            logger.error(f"Project {project_id} not found")
            await broadcast_progress(
                user, project_id, "error",
                message="Project not found"
            )
            return

        # Execute build use case with WebSocket progress updates
        build_uc = BuildVideoUseCase(video_composer, file_storage)

        def progress_callback(progress: float):
            """Send progress updates via WebSocket"""
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(
                    broadcast_progress(
                        user,
                        project_id,
                        "export_progress",
                        progress=progress,
                        status="building",
                    )
                )
            )

        result = await build_uc.execute(project, progress_callback)

        if result.success:
            logger.info(f"Video build completed for project {project_id}")
            await broadcast_progress(
                user, project_id, "task_complete",
                status="exported",
                message="Video export completed successfully"
            )
        else:
            logger.error(f"Video build failed for project {project_id}: {result.message}")
            await broadcast_progress(
                user, project_id, "error",
                message=result.message
            )

    except Exception as e:
        logger.error(f"Video build task error: {str(e)}", exc_info=True)
        await broadcast_progress(
            user, project_id, "error",
            message=f"Video build error: {str(e)}"
        )


@router.post("/{project_id}/build-video", response_model=TaskStartedResponse, status_code=status.HTTP_202_ACCEPTED)
async def build_video(
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Start building video from downloaded items in the background.

    Requires that the project has been downloaded first.
    """
    try:
        project = db.get_project(current_user, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        if project.download_status != "downloaded":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project must be downloaded before building video"
            )

        if project.export_status in {"queued", "building"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Export already in progress")

        if db.task_exists_active(owner=current_user, project_id=project_id, task_type="build"):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Export already queued")

        # Generate task ID
        task_id = str(uuid.uuid4())

        db.enqueue_task(task_id=task_id, owner=current_user, project_id=project_id, task_type="build", message="Export queued")
        db.update_project(owner=current_user, project_id=project_id, fields={"export_status": "queued", "export_progress": 0.0, "error_message": None})

        # Broadcast queued status immediately
        from api.websockets.progress import broadcast_progress
        await broadcast_progress(current_user, project_id, "export_progress", progress=0.0, status="queued", task_id=task_id, task_type="build")

        logger.info(f"Video build task {task_id} queued for project {project_id}")

        return TaskStartedResponse(
            message="Video build queued",
            task_id=task_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting video build: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start video build: {str(e)}"
        )


@router.get("/projects", response_model=HighlightProjectsResponse)
async def get_projects(
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Get all highlight projects for the current user.
    """
    try:
        projects = db.list_projects(current_user)
        return HighlightProjectsResponse(projects=[_row_to_response(p) for p in projects])

    except Exception as e:
        logger.error(f"Error getting projects: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get projects: {str(e)}"
        )


@router.get("/{project_id}/status", response_model=HighlightProjectResponse)
async def get_project_status(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Get current status of a specific project.
    """
    try:
        project = db.get_project(current_user, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        return _row_to_response(project)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project status: {str(e)}"
        )


@router.post("/{project_id}/create-zip", response_model=TaskStartedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_zip_bundle(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Create ZIP bundle containing all project artifacts.

    Bundles downloads and exports into a single ZIP file.
    Requires that the project has been downloaded first.
    """
    try:
        project = db.get_project(current_user, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        if project.download_status != "downloaded":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project must be downloaded before creating ZIP bundle"
            )

        # Check if ZIP already exists
        if project.zip_bundle_url:
            logger.info(f"ZIP bundle already exists for project {project_id}")
            return TaskStartedResponse(
                message="ZIP bundle already exists",
                task_id="already_exists"
            )

        # Check if task already queued/running
        if db.task_exists_active(owner=current_user, project_id=project_id, task_type="create_zip"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="ZIP creation already in progress"
            )

        # Generate task ID and enqueue
        task_id = str(uuid.uuid4())
        db.enqueue_task(
            task_id=task_id,
            owner=current_user,
            project_id=project_id,
            task_type="create_zip",
            message="ZIP creation queued"
        )

        # Broadcast queued status immediately
        from api.websockets.progress import broadcast_progress
        await broadcast_progress(current_user, project_id, "zip_progress", progress=0.0, status="creating_zip", task_id=task_id, task_type="create_zip")

        logger.info(f"ZIP creation task {task_id} queued for project {project_id}")

        return TaskStartedResponse(
            message="ZIP creation queued",
            task_id=task_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ZIP bundle: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ZIP bundle: {str(e)}"
        )


@router.post("/{project_id}/cancel", response_model=MessageResponse)
async def cancel_project_task(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Cancel the active task for a project.

    Cancels any queued or running download/build/zip task for the project.
    """
    try:
        # Get the active task for this project
        task = db.get_active_task_for_project(current_user, project_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active task found for this project"
            )

        # Cancel the task
        cancelled = db.cancel_task(current_user, task.task_id)
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task could not be cancelled (may have already completed)"
            )

        # Update project status and clean up files based on task type
        if task.task_type == "download":
            # Get project to find folder path
            project = db.get_project(current_user, project_id)
            if project:
                # Delete downloaded files
                from pathlib import Path
                import shutil
                downloads_path = Path(project.folder_path) / "downloads"
                if downloads_path.exists():
                    try:
                        shutil.rmtree(downloads_path)
                        logger.info(f"Deleted downloads folder for cancelled project {project_id}")
                    except Exception as e:
                        logger.error(f"Error deleting downloads folder: {e}")

            # Reset to idle so user can retry
            db.update_project(
                owner=current_user,
                project_id=project_id,
                fields={"download_status": "idle", "download_progress": 0.0, "error_message": None}
            )
        elif task.task_type == "build":
            # Delete export files if any
            project = db.get_project(current_user, project_id)
            if project:
                from pathlib import Path
                import shutil
                exports_path = Path(project.folder_path) / "exports"
                if exports_path.exists():
                    try:
                        shutil.rmtree(exports_path)
                        logger.info(f"Deleted exports folder for cancelled project {project_id}")
                    except Exception as e:
                        logger.error(f"Error deleting exports folder: {e}")

            # Reset to not_started so user can retry
            db.update_project(
                owner=current_user,
                project_id=project_id,
                fields={"export_status": "not_started", "export_progress": 0.0, "merged_video_url": None, "error_message": None}
            )

        logger.info(f"Task {task.task_id} cancelled for project {project_id}")
        return MessageResponse(message="Task cancelled successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: str,
    current_user: str = Depends(get_current_user),
    db: StateDB = Depends(get_state_db),
):
    """
    Delete a project and clean up all associated files.
    """
    try:
        # Get project to verify ownership and get folder path
        project = db.get_project(current_user, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        # Cancel any running tasks for this project
        tasks = db.get_active_tasks(current_user, project_id)
        for task in tasks:
            db.update_task(task_id=task.task_id, fields={"status": "cancelled"})
            logger.info(f"Cancelled task {task.task_id} for project deletion")

        # Clean up all files
        from pathlib import Path
        import shutil

        project_folder = Path(project.folder_path)
        if project_folder.exists():
            try:
                shutil.rmtree(project_folder)
                logger.info(f"Deleted project folder: {project_folder}")
            except Exception as e:
                logger.error(f"Error deleting project folder: {e}")

        # Delete project from database
        db.delete_project(current_user, project_id)
        logger.info(f"Project {project_id} deleted from database")

        return MessageResponse(message="Project deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )
