"""In-process task runner that persists state to SQLite and emits WebSocket updates."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional, List

from core.config import settings
from app.application.use_cases import DownloadHighlightUseCase, BuildVideoUseCase, CreateZipBundleUseCase
from app.domain.entities import DownloadStatus, ExportStatus, HighlightItem, HighlightProject
from app.domain.value_objects import FolderPath, Username
from .instagram_aiograpi import InstagramGatewayAiograpi
from .state_db import StateDB, TaskRow

logger = logging.getLogger(__name__)


class TaskRunner:
    def __init__(self, db: StateDB, file_storage, video_composer, max_workers: int = 3):
        self.db = db
        self.file_storage = file_storage
        self.video_composer = video_composer
        self.max_workers = max_workers
        self._workers: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        self._semaphore = asyncio.Semaphore(max_workers)

    def start(self) -> None:
        if self._workers and any(not w.done() for w in self._workers):
            return
        self._stop_event.clear()
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.max_workers)
        ]
        logger.info(f"TaskRunner started with {self.max_workers} workers")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("TaskRunner stopped")

    async def _worker(self, worker_id: int) -> None:
        """Worker loop that processes tasks concurrently"""
        from api.websockets.progress import broadcast_progress

        loop = asyncio.get_running_loop()
        logger.info(f"TaskRunner worker {worker_id} started")

        while not self._stop_event.is_set():
            # Acquire semaphore to limit concurrent tasks
            async with self._semaphore:
                task = self.db.claim_next_task()
                if not task:
                    # Release semaphore immediately if no task
                    pass
                else:
                    try:
                        logger.info(f"Worker {worker_id} processing task {task.task_id} ({task.task_type})")
                        await self._run_task(task, loop)
                    except Exception as e:
                        logger.error(f"Worker {worker_id} task crash: {e}", exc_info=True)
                        self.db.update_task(task_id=task.task_id, fields={"status": "failed", "error_message": str(e)})
                        await broadcast_progress(task.owner, task.project_id, "error", message=f"Task failed: {e}", task_id=task.task_id, task_type=task.task_type)

            # Small sleep to prevent busy loop when no tasks
            await asyncio.sleep(0.4)

        logger.info(f"TaskRunner worker {worker_id} stopped")

    async def _run_task(self, task: TaskRow, loop: asyncio.AbstractEventLoop) -> None:
        from api.websockets.progress import broadcast_progress

        owner = task.owner
        project_id = task.project_id

        project_row = self.db.get_project(owner, project_id)
        if not project_row:
            self.db.update_task(task_id=task.task_id, fields={"status": "failed", "error_message": "Project not found"})
            await broadcast_progress(owner, project_id, "error", message="Project not found")
            return

        safe_owner = str(Username(owner))
        ig = InstagramGatewayAiograpi(settings.SESSION_DIR / safe_owner)

        if task.task_type == "download":
            self.db.update_project(owner=owner, project_id=project_id, fields={"download_status": "downloading", "download_progress": 0.0, "error_message": None})
            await broadcast_progress(owner, project_id, "download_progress", progress=0.0, status="downloading", task_id=task.task_id, task_type="download")

            download_uc = DownloadHighlightUseCase(ig, self.file_storage)

            def progress_callback(progress: float) -> None:
                # Check if task was cancelled
                current_task = self.db.get_task(task.task_id)
                if current_task and current_task.status == "cancelled":
                    raise RuntimeError("Task cancelled by user")

                self.db.update_task(task_id=task.task_id, fields={"progress": float(progress)})
                self.db.update_project(owner=owner, project_id=project_id, fields={"download_progress": float(progress)})
                loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(
                        broadcast_progress(owner, project_id, "download_progress", progress=progress, status="downloading", task_id=task.task_id, task_type="download")
                    )
                )

            project_entity = HighlightProject(
                id=project_row.project_id,
                title=project_row.title,
                source=project_row.source,
                folder_path=project_row.folder_path,
                download_status=DownloadStatus.DOWNLOADING,
                export_status=ExportStatus(project_row.export_status),
            )

            result = await download_uc.execute(project_entity, progress_callback)

            if result.success:
                self.db.update_task(task_id=task.task_id, fields={"status": "success", "progress": 1.0, "message": result.message, "error_message": None})
                self.db.update_project(
                    owner=owner,
                    project_id=project_id,
                    fields={"download_status": "downloaded", "download_progress": 1.0, "item_count": len(project_entity.items)},
                )
                await broadcast_progress(owner, project_id, "task_complete", status="downloaded", message=result.message, task_id=task.task_id, task_type="download")
            else:
                # Check if task was cancelled before setting error
                current_task = self.db.get_task(task.task_id)
                if current_task and current_task.status == "cancelled":
                    # Task was cancelled, don't overwrite the clean state
                    logger.info(f"Task {task.task_id} was cancelled, skipping error message")
                    return

                # Only set error if task wasn't cancelled
                self.db.update_task(task_id=task.task_id, fields={"status": "failed", "error_message": result.message})
                self.db.update_project(owner=owner, project_id=project_id, fields={"download_status": "error", "error_message": result.message})
                await broadcast_progress(owner, project_id, "error", message=result.message, task_id=task.task_id, task_type="download")

            return

        if task.task_type == "build":
            self.db.update_project(owner=owner, project_id=project_id, fields={"export_status": "building", "export_progress": 0.0, "error_message": None})
            await broadcast_progress(owner, project_id, "export_progress", progress=0.0, status="building", task_id=task.task_id, task_type="build")

            build_uc = BuildVideoUseCase(self.video_composer, self.file_storage)

            def progress_callback(progress: float) -> None:
                self.db.update_task(task_id=task.task_id, fields={"progress": float(progress)})
                self.db.update_project(owner=owner, project_id=project_id, fields={"export_progress": float(progress)})
                loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(
                        broadcast_progress(owner, project_id, "export_progress", progress=progress, status="building", task_id=task.task_id, task_type="build")
                    )
                )

            downloads_path = Path(project_row.folder_path) / "downloads"
            items: list[HighlightItem] = []
            if downloads_path.exists():
                for file in sorted(downloads_path.iterdir()):
                    if not file.is_file():
                        continue
                    suffix = file.suffix.lower()
                    item_type = "video" if suffix in {".mp4", ".mov"} else "image"
                    items.append(HighlightItem(item_type=item_type, downloaded_path=str(file)))

            project_entity = HighlightProject(
                id=project_row.project_id,
                title=project_row.title,
                source=project_row.source,
                folder_path=project_row.folder_path,
                items=items,
                download_status=DownloadStatus(project_row.download_status),
                export_status=ExportStatus.BUILDING,
            )

            result = await build_uc.execute(project_entity, progress_callback)

            if result.success:
                # Update project with merged video URL
                video_filename = Path(result.data).name if result.data else None
                video_url = f"/api/v1/files/download/{project_id}/video/{video_filename}" if video_filename else None

                self.db.update_task(task_id=task.task_id, fields={"status": "success", "progress": 1.0, "message": result.message, "error_message": None})
                self.db.update_project(
                    owner=owner,
                    project_id=project_id,
                    fields={"export_status": "exported", "export_progress": 1.0, "merged_video_url": video_url}
                )
                await broadcast_progress(owner, project_id, "task_complete", status="exported", message=result.message, task_id=task.task_id, task_type="build")
            else:
                # Check if task was cancelled before setting error
                current_task = self.db.get_task(task.task_id)
                if current_task and current_task.status == "cancelled":
                    # Task was cancelled, don't overwrite the clean state
                    logger.info(f"Task {task.task_id} was cancelled, skipping error message")
                    return

                # Only set error if task wasn't cancelled
                self.db.update_task(task_id=task.task_id, fields={"status": "failed", "error_message": result.message})
                self.db.update_project(owner=owner, project_id=project_id, fields={"export_status": "error", "error_message": result.message})
                await broadcast_progress(owner, project_id, "error", message=result.message, task_id=task.task_id, task_type="build")

            return

        if task.task_type == "create_zip":
            logger.info(f"Starting ZIP bundle creation for project {project_id}")

            zip_uc = CreateZipBundleUseCase(self.file_storage)

            def progress_callback(progress: float) -> None:
                self.db.update_task(task_id=task.task_id, fields={"progress": float(progress)})
                loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(
                        broadcast_progress(owner, project_id, "zip_progress", progress=progress, status="creating_zip", task_id=task.task_id, task_type="create_zip")
                    )
                )

            project_entity = HighlightProject(
                id=project_row.project_id,
                title=project_row.title,
                source=project_row.source,
                folder_path=project_row.folder_path,
                download_status=DownloadStatus(project_row.download_status),
                export_status=ExportStatus(project_row.export_status),
            )

            result = await zip_uc.execute(project_entity, progress_callback)

            if result.success:
                # Update project with ZIP URL
                zip_filename = Path(result.data).name if result.data else None
                zip_url = f"/api/v1/files/download/{project_id}/zip/{zip_filename}" if zip_filename else None

                self.db.update_task(task_id=task.task_id, fields={"status": "success", "progress": 1.0, "message": result.message, "error_message": None})
                self.db.update_project(
                    owner=owner,
                    project_id=project_id,
                    fields={"zip_bundle_url": zip_url}
                )
                await broadcast_progress(owner, project_id, "task_complete", status="zip_created", message=result.message, task_id=task.task_id, task_type="create_zip")
            else:
                self.db.update_task(task_id=task.task_id, fields={"status": "failed", "error_message": result.message})
                await broadcast_progress(owner, project_id, "error", message=result.message, task_id=task.task_id, task_type="create_zip")

            return

        self.db.update_task(task_id=task.task_id, fields={"status": "failed", "error_message": f"Unknown task type: {task.task_type}"})
        await broadcast_progress(owner, project_id, "error", message=f"Unknown task type: {task.task_type}", task_id=task.task_id, task_type=task.task_type)
