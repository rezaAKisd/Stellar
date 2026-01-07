"""Highlights API routes - Link-based highlight management"""
import logging
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from ..schemas import (
    AddLinkRequest,
    HighlightProjectResponse,
    HighlightProjectsResponse,
    TaskStartedResponse,
    MessageResponse
)
from ..dependencies import get_instagram_gateway, get_file_storage, get_video_composer
from ...core.security import get_current_user
from ...app.application.use_cases import (
    AddHighlightLinkUseCase,
    DownloadHighlightUseCase,
    BuildVideoUseCase,
    OpenExportsFolderUseCase
)
from ...app.domain.entities import HighlightProject

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for projects (in production, use database)
# Key: user -> List[HighlightProject]
_user_projects: dict[str, List[HighlightProject]] = {}


def _project_to_response(project: HighlightProject) -> HighlightProjectResponse:
    """Convert HighlightProject entity to API response"""
    return HighlightProjectResponse(
        id=project.id,
        title=project.title,
        source=project.source,
        folder_path=project.folder_path,
        item_count=project.item_count,
        download_status=project.download_status.value,
        export_status=project.export_status.value,
        download_progress=project.download_progress,
        export_progress=project.export_progress,
        error_message=project.error_message,
        has_downloads=project.has_downloads,
        has_exports=project.has_exports
    )


@router.post("/add-link", response_model=HighlightProjectResponse, status_code=status.HTTP_201_CREATED)
async def add_highlight_link(
    request: AddLinkRequest,
    current_user: str = Depends(get_current_user),
    instagram_gateway = Depends(get_instagram_gateway),
    file_storage = Depends(get_file_storage)
):
    """
    Add a new highlight by Instagram URL.

    Returns the created project with metadata.
    """
    try:
        logger.info(f"Adding highlight link for user {current_user}: {request.url}")

        # Execute use case
        add_uc = AddHighlightLinkUseCase(instagram_gateway, file_storage)
        project_dto = await add_uc.execute(request.url)

        # Create domain entity from DTO
        from ...app.domain.entities import HighlightProject, DownloadStatus, ExportStatus
        project = HighlightProject(
            id=project_dto.id,
            title=project_dto.title,
            source=project_dto.source,
            folder_path=project_dto.folder_path,
            download_status=DownloadStatus(project_dto.download_status),
            export_status=ExportStatus(project_dto.export_status)
        )

        # Store in memory
        if current_user not in _user_projects:
            _user_projects[current_user] = []
        _user_projects[current_user].append(project)

        logger.info(f"Highlight added successfully: {project.id}")
        return _project_to_response(project)

    except ValueError as e:
        logger.warning(f"Invalid highlight URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
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
    from ..websockets.progress import broadcast_progress

    try:
        logger.info(f"Starting download task {task_id} for project {project_id}")

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
            import asyncio
            asyncio.create_task(broadcast_progress(
                user, project_id, "download_progress",
                progress=progress,
                status="downloading"
            ))

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
    instagram_gateway = Depends(get_instagram_gateway),
    file_storage = Depends(get_file_storage)
):
    """
    Start downloading highlight items in the background.

    Returns a task ID for tracking progress (via WebSocket in Phase 4).
    """
    try:
        # Verify project exists
        project = None
        for p in _user_projects.get(current_user, []):
            if p.id == project_id:
                project = p
                break

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Add background task
        background_tasks.add_task(
            _download_highlight_task,
            project_id,
            task_id,
            current_user,
            instagram_gateway,
            file_storage
        )

        logger.info(f"Download task {task_id} queued for project {project_id}")

        return TaskStartedResponse(
            message="Download started",
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
    from ..websockets.progress import broadcast_progress

    try:
        logger.info(f"Starting video build task {task_id} for project {project_id}")

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
            import asyncio
            asyncio.create_task(broadcast_progress(
                user, project_id, "export_progress",
                progress=progress,
                status="building"
            ))

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
    video_composer = Depends(get_video_composer),
    file_storage = Depends(get_file_storage)
):
    """
    Start building video from downloaded items in the background.

    Requires that the project has been downloaded first.
    """
    try:
        # Verify project exists and is downloaded
        project = None
        for p in _user_projects.get(current_user, []):
            if p.id == project_id:
                project = p
                break

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        if not project.has_downloads:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project must be downloaded before building video"
            )

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Add background task
        background_tasks.add_task(
            _build_video_task,
            project_id,
            task_id,
            current_user,
            video_composer,
            file_storage
        )

        logger.info(f"Video build task {task_id} queued for project {project_id}")

        return TaskStartedResponse(
            message="Video build started",
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
    current_user: str = Depends(get_current_user)
):
    """
    Get all highlight projects for the current user.
    """
    try:
        projects = _user_projects.get(current_user, [])

        return HighlightProjectsResponse(
            projects=[_project_to_response(p) for p in projects]
        )

    except Exception as e:
        logger.error(f"Error getting projects: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get projects: {str(e)}"
        )


@router.get("/{project_id}/status", response_model=HighlightProjectResponse)
async def get_project_status(
    project_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get current status of a specific project.
    """
    try:
        # Find project
        project = None
        for p in _user_projects.get(current_user, []):
            if p.id == project_id:
                project = p
                break

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        return _project_to_response(project)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project status: {str(e)}"
        )


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Delete a project and its files.
    """
    try:
        # Find and remove project
        projects = _user_projects.get(current_user, [])
        project = None

        for i, p in enumerate(projects):
            if p.id == project_id:
                project = projects.pop(i)
                break

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        # TODO: Delete files from disk
        logger.info(f"Project {project_id} deleted")

        return MessageResponse(message="Project deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )
