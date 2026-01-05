"""Video builder using moviepy"""
import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional
import os

try:
    from moviepy.editor import (
        VideoFileClip, ImageClip, concatenate_videoclips,
        CompositeVideoClip
    )
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("Warning: moviepy not installed. Video building will be limited.")

try:
    from PIL import Image as PILImage
    if not hasattr(PILImage, "ANTIALIAS") and hasattr(PILImage, "Resampling"):
        PILImage.ANTIALIAS = PILImage.Resampling.LANCZOS
except Exception:
    pass

try:
    from proglog import ProgressBarLogger
    PROGLOG_AVAILABLE = True
except Exception:
    PROGLOG_AVAILABLE = False

from ..models.job import HighlightJob, JobStatus

logger = logging.getLogger(__name__)


class _BuildProgressLogger(ProgressBarLogger):
    """MoviePy logger that reports export progress back to the job."""

    def __init__(self, job, emit_progress, start: float, end: float):
        super().__init__(logged_bars=None, min_time_interval=0.1)
        self.job = job
        self.emit_progress = emit_progress
        self.start = start
        self.end = end
        self._last_progress = start

    def bars_callback(self, bar, attr, value, old_value=None):
        if bar != "t" or attr != "index":
            return
        total = self.bars.get(bar, {}).get("total")
        if not total:
            return
        frac = min(max(value / total, 0.0), 1.0)
        progress = self.start + (self.end - self.start) * frac
        if progress <= self._last_progress:
            return
        self._last_progress = progress
        self.job.build_progress = progress
        self.job.build_stage = f"Exporting video... {int(frac * 100)}%"
        self.emit_progress()


class VideoBuilder:
    """Build videos from downloaded highlights"""

    def __init__(self):
        if not MOVIEPY_AVAILABLE:
            print("Warning: moviepy not available")

        self.default_image_duration = 3  # seconds per image
        self.default_resolution = (1080, 1920)  # Instagram story size (9:16)
        self.default_fps = 30

    async def build_video(
        self,
        job: HighlightJob,
        progress_callback: Optional[Callable[[HighlightJob], None]] = None
    ):
        """Build a video from highlight items"""
        logger.info(f"Starting video build for job={job.id} title='{job.title}'")
        if not MOVIEPY_AVAILABLE:
            job.status = JobStatus.ERROR
            job.error_message = "moviepy not installed. Install with: pip install moviepy"
            if progress_callback:
                progress_callback(job)
            return

        job.status = JobStatus.BUILDING
        job.build_progress = 0.0
        job.should_cancel = False
        job.error_message = None
        if progress_callback:
            progress_callback(job)

        loop = asyncio.get_running_loop()
        await asyncio.to_thread(
            self._build_video_sync,
            job,
            progress_callback,
            loop
        )

    def cancel_build(self, job: HighlightJob):
        """Cancel an ongoing build"""
        job.should_cancel = True

    def _build_video_sync(
        self,
        job: HighlightJob,
        progress_callback: Optional[Callable[[HighlightJob], None]],
        loop
    ):
        """Blocking video build executed in a worker thread."""
        def emit_progress():
            if progress_callback:
                loop.call_soon_threadsafe(progress_callback, job)

        # Create exports folder (root of highlight folder)
        if job.folder_path:
            job.exports_folder = job.folder_path
            job.exports_folder.mkdir(parents=True, exist_ok=True)
        else:
            job.status = JobStatus.ERROR
            job.error_message = "Job folder_path not set"
            emit_progress()
            return

        clips = []
        final_clip = None
        try:
            downloaded_items = [i for i in job.items if i.downloaded and i.local_path]
            total_items = len(downloaded_items)
            load_weight = 0.4
            encode_start = load_weight
            encode_end = 0.99

            logger.info(
                f"Downloaded items for job={job.id}: {total_items}/{len(job.items)}"
            )

            if total_items == 0:
                job.status = JobStatus.ERROR
                job.error_message = "No downloaded items to build video from"
                emit_progress()
                return

            for idx, item in enumerate(downloaded_items):
                # Check cancel flag
                if job.should_cancel:
                    job.status = JobStatus.BUILD_CANCELLED
                    job.build_stage = "Cancelled"
                    emit_progress()
                    return

                path = Path(item.local_path)

                if not path.exists():
                    logger.warning(
                        f"Missing file for job={job.id} item={idx + 1} path='{path}'"
                    )
                    continue

                try:
                    # Update stage
                    job.build_stage = f"Loading clips {idx + 1}/{total_items}"
                    emit_progress()

                    if item.type == 'video':
                        clip = VideoFileClip(str(path))
                    else:
                        clip = ImageClip(str(path)).set_duration(self.default_image_duration)

                    clip = clip.resize(height=self.default_resolution[1])
                    clips.append(clip)
                    logger.debug(
                        f"Loaded clip for job={job.id} item={idx + 1} "
                        f"type={item.type} path='{path}'"
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to load clip for job={job.id} item={idx + 1} "
                        f"path='{path}': {e}"
                    )
                    continue

                job.build_progress = (idx + 1) / total_items * load_weight
                emit_progress()

            if not clips:
                logger.error(f"No valid clips found for job={job.id}")
                job.status = JobStatus.ERROR
                job.error_message = "No valid clips to merge"
                emit_progress()
                return

            job.build_progress = load_weight
            job.build_stage = "Merging clips..."
            emit_progress()

            final_clip = concatenate_videoclips(clips, method="compose")

            output_path = job.exports_folder / "final_video.mp4"

            logger.info(
                f"Writing output for job={job.id} to '{output_path}'"
            )

            job.build_progress = max(job.build_progress, encode_start)
            job.build_stage = "Encoding video..."
            emit_progress()

            export_logger = None
            if PROGLOG_AVAILABLE:
                export_logger = _BuildProgressLogger(job, emit_progress, encode_start, encode_end)

            final_clip.write_videofile(
                str(output_path),
                fps=self.default_fps,
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                verbose=False,
                logger=export_logger
            )

            job.output_video_path = output_path
            job.status = JobStatus.EXPORTED
            job.build_progress = 1.0
            job.build_stage = "Complete"
            emit_progress()

        except Exception as e:
            logger.error(f"Video build failed for job={job.id}: {e}", exc_info=True)
            job.status = JobStatus.ERROR
            job.error_message = f"Video build failed: {str(e)}"
            emit_progress()
        finally:
            for clip in clips:
                try:
                    clip.close()
                except Exception:
                    pass
            if final_clip:
                try:
                    final_clip.close()
                except Exception:
                    pass
