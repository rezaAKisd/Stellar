"""Download manager with pause/resume support"""
import asyncio
import time
from pathlib import Path
from typing import Callable, Optional
from ..models.job import HighlightJob, JobStatus, HighlightItem


class DownloadManager:
    """Manages download operations with pause/resume support"""

    def __init__(self, instagram_service):
        self.instagram = instagram_service
        self.active_tasks = {}  # job_id -> task

    async def start_download(
        self,
        job: HighlightJob,
        progress_callback: Optional[Callable[[HighlightJob], None]] = None
    ):
        """Start or resume downloading a highlight job"""
        job.status = JobStatus.DOWNLOADING
        job.should_pause = False
        job.error_message = None

        # Create folders
        if job.folder_path:
            job.downloads_folder = job.folder_path / "downloads"
            job.downloads_folder.mkdir(parents=True, exist_ok=True)
        else:
            raise ValueError("Job folder_path not set")

        # Speed tracking
        speed_samples = []  # List of (bytes, timestamp) tuples
        last_update_time = time.time()
        last_downloaded = 0

        # Download each item
        for idx, item in enumerate(job.items):
            # Check pause flag
            if job.should_pause:
                job.status = JobStatus.PAUSED
                if progress_callback:
                    progress_callback(job)
                break

            # Skip already downloaded
            if item.downloaded:
                continue

            try:
                job.current_item_index = idx
                item_start_time = time.time()
                item_downloaded = 0

                # Download item with progress tracking
                def item_progress(downloaded, total):
                    nonlocal item_downloaded, last_update_time, last_downloaded

                    # Calculate speed (using exponential moving average)
                    now = time.time()
                    elapsed = now - last_update_time
                    if elapsed > 0.1:  # Update every 100ms
                        bytes_diff = downloaded - last_downloaded
                        speed = bytes_diff / elapsed

                        # Exponential moving average for smoothing
                        if job.download_speed == 0:
                            job.download_speed = speed
                        else:
                            job.download_speed = 0.7 * job.download_speed + 0.3 * speed

                        last_update_time = now
                        last_downloaded = downloaded

                    # Calculate ETA
                    if total > 0 and job.download_speed > 0:
                        remaining_in_item = total - downloaded
                        remaining_items = job.total_items - job.downloaded_items - 1
                        # Rough estimate: assume all items are similar size
                        avg_item_size = total  # Current item size as estimate
                        total_remaining_bytes = remaining_in_item + (remaining_items * avg_item_size)
                        job.estimated_time_remaining = int(total_remaining_bytes / job.download_speed)

                    # Update item progress
                    if total > 0:
                        job.current_item_progress = downloaded / total
                        item_prog = downloaded / total
                        overall = (job.downloaded_items + item_prog) / job.total_items
                        job.download_progress = overall

                        if progress_callback:
                            progress_callback(job)

                filename = f"item_{idx + 1}_{item.type}.{'mp4' if item.type == 'video' else 'jpg'}"
                local_path = await self.instagram.download_media(
                    item.url,
                    job.downloads_folder,
                    filename,
                    item_progress
                )

                item.local_path = str(local_path)
                item.downloaded = True
                job.downloaded_items += 1
                job.current_item_progress = 0.0

                # Update progress
                job.download_progress = job.downloaded_items / job.total_items
                if progress_callback:
                    progress_callback(job)

                # Small delay to prevent rate limiting
                await asyncio.sleep(0.5)

            except Exception as e:
                job.status = JobStatus.ERROR
                job.error_message = f"Failed to download item {idx + 1}: {str(e)}"
                if progress_callback:
                    progress_callback(job)
                return

        # Mark as complete if not paused
        if not job.should_pause:
            job.status = JobStatus.DOWNLOADED
            job.download_progress = 1.0
            if progress_callback:
                progress_callback(job)

    def pause_download(self, job: HighlightJob):
        """Pause an ongoing download"""
        job.should_pause = True

    async def resume_download(
        self,
        job: HighlightJob,
        progress_callback: Optional[Callable[[HighlightJob], None]] = None
    ):
        """Resume a paused download"""
        await self.start_download(job, progress_callback)
