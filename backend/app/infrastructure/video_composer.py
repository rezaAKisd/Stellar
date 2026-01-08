"""Real Video Composer using MoviePy and FFmpeg"""
import asyncio
from typing import List, Optional, Callable
from pathlib import Path
import logging

from ..domain.interfaces import IVideoComposer
from ..domain.entities import HighlightItem
from ..domain.value_objects import FolderPath

logger = logging.getLogger(__name__)


class VideoComposer(IVideoComposer):
    """Real implementation for video composition using MoviePy"""

    async def merge_items_to_video(
        self,
        items: List[HighlightItem],
        output_path: FolderPath,
        filename: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """Merge all items (videos and photos) into a single video using MoviePy"""
        output_path.ensure_exists()

        def _merge_sync() -> str:
            try:
                from moviepy.editor import (
                    VideoFileClip, ImageClip, concatenate_videoclips,
                    CompositeVideoClip, AudioFileClip
                )

                # Filter items that have been downloaded
                downloaded_items = [item for item in items if item.downloaded_path]
                if not downloaded_items:
                    raise ValueError("No downloaded items to merge")

                # Sort items by their downloaded path (which contains index and timestamp)
                # Files are named like: 0001_1234567890_uuid.mp4
                downloaded_items.sort(key=lambda x: Path(x.downloaded_path).name)

                logger.info(f"Merging {len(downloaded_items)} items in order:")
                for idx, item in enumerate(downloaded_items):
                    logger.info(f"  {idx}: {Path(item.downloaded_path).name}")

                clips = []
                total_items = len(downloaded_items)

                for idx, item in enumerate(downloaded_items):
                    try:
                        file_path = Path(item.downloaded_path)

                        if item.item_type == "video":
                            # Load video clip
                            clip = VideoFileClip(str(file_path))
                        else:
                            # Convert image to video (3 seconds duration)
                            clip = ImageClip(str(file_path), duration=3)
                            # Set fps for images
                            clip = clip.set_fps(24)

                        clips.append(clip)

                        # Update progress
                        if progress_callback:
                            progress = (idx + 0.5) / total_items * 0.5  # First 50% for loading
                            progress_callback(progress)

                    except Exception as e:
                        logger.error(f"Error loading item {file_path}: {e}")
                        # Skip problematic items
                        continue

                if not clips:
                    raise ValueError("No clips could be loaded")

                # Concatenate all clips
                logger.info(f"Concatenating {len(clips)} clips...")
                final_clip = concatenate_videoclips(clips, method="compose")

                # Write output file
                output_file = Path(output_path.value) / filename
                logger.info(f"Writing merged video to {output_file}")

                # Custom progress logger for MoviePy using proglog
                custom_logger = None
                if progress_callback:
                    try:
                        from proglog import ProgressBarLogger

                        class CustomProgressLogger(ProgressBarLogger):
                            def __init__(self, progress_cb, clip_duration):
                                super().__init__()
                                import time
                                # Store callback as private attribute to avoid proglog interference
                                self._progress_callback = progress_cb
                                self._clip_duration = clip_duration
                                self._last_progress = 0.5
                                self._last_update_time = time.time()
                                self._update_count = 0

                            def callback(self, **kw):
                                """Override proglog's callback to prevent errors"""
                                # proglog calls this with various keyword arguments
                                # We safely ignore them and handle progress in bars_callback
                                pass

                            def bars_callback(self, bar, attr, value, old_value=None):
                                """Called when progress bar updates"""
                                import time

                                self._update_count += 1

                                # Log first few updates for debugging
                                if self._update_count <= 5:
                                    logger.info(f"Progress update #{self._update_count}: bar={bar}, attr={attr}, value={value}, old={old_value}")

                                # Only process 'index' updates (ignore 'total' and other attributes)
                                if attr != 'index':
                                    if self._update_count <= 5:
                                        logger.info(f"Ignoring attr={attr} update")
                                    return

                                if bar and self.bars and bar in self.bars:
                                    bar_info = self.bars[bar]
                                    total = bar_info.get('total', 0)

                                    if total > 0 and value is not None:
                                        # Calculate current progress percentage
                                        percentage = min(value / total, 0.99)  # Cap at 99% during encoding

                                        # Map encoding phase to 50-99% (reserve 100% for completion)
                                        overall_progress = 0.5 + percentage * 0.49

                                        current_time = time.time()
                                        time_delta = current_time - self._last_update_time
                                        progress_delta = overall_progress - self._last_progress

                                        # Throttle: update every 1% OR every 2 seconds OR at 99%
                                        should_update = (
                                            progress_delta >= 0.01 or  # 1% change
                                            time_delta >= 2.0 or       # 2 seconds elapsed
                                            overall_progress >= 0.99   # Near completion
                                        )

                                        if should_update:
                                            self._last_progress = overall_progress
                                            self._last_update_time = current_time
                                            self._progress_callback(overall_progress)

                                            logger.info(f"Video encoding progress: {overall_progress*100:.1f}% (chunk {value}/{total})")

                        custom_logger = CustomProgressLogger(progress_callback, final_clip.duration)
                    except ImportError:
                        logger.warning("proglog not available, progress updates may not work")
                        custom_logger = None

                final_clip.write_videofile(
                    str(output_file),
                    codec='libx264',
                    audio_codec='aac',
                    fps=24,
                    preset='medium',
                    logger=custom_logger,
                    verbose=False
                )

                # Close all clips to free resources
                final_clip.close()
                for clip in clips:
                    clip.close()

                if progress_callback:
                    progress_callback(1.0)

                logger.info(f"Successfully created merged video: {output_file}")
                return str(output_file)

            except ImportError:
                logger.error("MoviePy not installed. Install with: pip install moviepy")
                raise ValueError("Video processing library not available")
            except Exception as e:
                logger.error(f"Error merging video: {e}", exc_info=True)
                raise ValueError(f"Failed to merge video: {str(e)}")

        # Run in thread pool to avoid blocking
        return await asyncio.to_thread(_merge_sync)

    async def export_separate_clips(
        self,
        items: List[HighlightItem],
        output_path: FolderPath,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> List[str]:
        """Export items as separate clips (not implemented in v1)"""
        raise NotImplementedError("Separate clip export not implemented yet")
