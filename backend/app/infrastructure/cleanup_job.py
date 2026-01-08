"""Background job for artifact retention cleanup (30-day policy)"""
import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional

from .state_db import StateDB

logger = logging.getLogger(__name__)


class CleanupJob:
    """
    Background job that periodically cleans up expired project artifacts.

    Runs every 24 hours by default and:
    1. Marks projects as expired if past their expires_at date
    2. Deletes physical files for expired projects
    3. Keeps database records for audit trail
    """

    def __init__(self, db: StateDB, data_dir: Path, interval_hours: int = 24):
        """
        Initialize cleanup job.

        Args:
            db: StateDB instance for database operations
            data_dir: Base data directory containing user folders
            interval_hours: How often to run cleanup (default: 24 hours)
        """
        self.db = db
        self.data_dir = data_dir
        self.interval_hours = interval_hours
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        """Start the cleanup job background task."""
        if self._task and not self._task.done():
            logger.warning("Cleanup job already running")
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Cleanup job started (interval: {self.interval_hours} hours)")

    async def stop(self) -> None:
        """Stop the cleanup job gracefully."""
        if not self._task:
            return

        logger.info("Stopping cleanup job...")
        self._stop_event.set()

        try:
            await asyncio.wait_for(self._task, timeout=5.0)
            logger.info("Cleanup job stopped")
        except asyncio.TimeoutError:
            logger.warning("Cleanup job did not stop gracefully, cancelling...")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("Cleanup job cancelled")

    async def _run_loop(self) -> None:
        """Main cleanup loop - runs every interval_hours."""
        logger.info("Cleanup job loop started")

        while not self._stop_event.is_set():
            try:
                await self._cleanup_expired_artifacts()
            except Exception as e:
                logger.error(f"Cleanup job error: {e}", exc_info=True)

            # Sleep for interval_hours, checking stop event every minute
            for _ in range(self.interval_hours * 60):
                if self._stop_event.is_set():
                    break
                await asyncio.sleep(60)  # Check every minute

        logger.info("Cleanup job loop exited")

    async def _cleanup_expired_artifacts(self) -> None:
        """
        Find and delete expired project artifacts.

        Process:
        1. Mark expired projects in database (is_expired=1)
        2. Get list of expired projects
        3. Delete physical files from disk
        4. Keep database records for audit trail
        """
        try:
            # Step 1: Mark expired projects
            marked_count = self.db.mark_expired_projects()
            if marked_count > 0:
                logger.info(f"Marked {marked_count} projects as expired")

            # Step 2: Get list of expired projects
            expired_projects = self.db.cleanup_expired_artifacts()

            if not expired_projects:
                logger.debug("No expired projects to clean up")
                return

            logger.info(f"Found {len(expired_projects)} expired projects to clean up")

            # Step 3: Delete physical files
            deleted_count = 0
            failed_count = 0

            for project in expired_projects:
                try:
                    folder_path = Path(project.folder_path)

                    if folder_path.exists():
                        # Verify path is within data directory (security check)
                        data_dir_resolved = self.data_dir.resolve()
                        folder_path_resolved = folder_path.resolve()

                        if not str(folder_path_resolved).startswith(str(data_dir_resolved)):
                            logger.error(
                                f"Security: Refusing to delete path outside data dir: {folder_path_resolved}"
                            )
                            failed_count += 1
                            continue

                        # Delete the entire project folder
                        shutil.rmtree(folder_path)
                        deleted_count += 1
                        logger.info(
                            f"Deleted expired project files: {project.project_id} "
                            f"(owner: {project.owner}, expired: {project.expires_at})"
                        )
                    else:
                        logger.debug(
                            f"Project folder already deleted or doesn't exist: {folder_path}"
                        )
                        deleted_count += 1

                except PermissionError as e:
                    logger.error(
                        f"Permission denied deleting project {project.project_id}: {e}"
                    )
                    failed_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to delete project {project.project_id}: {e}",
                        exc_info=True
                    )
                    failed_count += 1

            # Summary
            logger.info(
                f"Cleanup completed: {deleted_count} projects cleaned, "
                f"{failed_count} failed, {len(expired_projects)} total expired"
            )

        except Exception as e:
            logger.error(f"Error during artifact cleanup: {e}", exc_info=True)
            raise

    async def run_once(self) -> None:
        """
        Run cleanup once (useful for testing or manual triggers).

        This is a convenience method that runs the cleanup immediately
        without starting the background loop.
        """
        logger.info("Running manual cleanup...")
        await self._cleanup_expired_artifacts()
        logger.info("Manual cleanup completed")
