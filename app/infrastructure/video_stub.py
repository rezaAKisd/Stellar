"""Stubbed Video Composer - Simulates video creation"""
import asyncio
from typing import List, Optional, Callable
from pathlib import Path

from ..domain.interfaces import IVideoComposer
from ..domain.entities import HighlightItem
from ..domain.value_objects import FolderPath


class VideoComposerStub(IVideoComposer):
    """Stub implementation for video composition"""

    async def merge_items_to_video(
        self,
        items: List[HighlightItem],
        output_path: FolderPath,
        filename: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """Simulate merging items into a video"""
        output_path.ensure_exists()

        # Simulate video rendering with progress
        steps = 50
        for step in range(steps):
            await asyncio.sleep(0.05)  # 50ms per step = ~2.5s total
            if progress_callback:
                progress_callback((step + 1) / steps)

        # Create dummy video file
        file_path = Path(output_path.value) / filename
        with open(file_path, 'wb') as f:
            f.write(b"DUMMY_VIDEO_CONTENT_MERGED")

        return str(file_path)

    async def export_separate_clips(
        self,
        items: List[HighlightItem],
        output_path: FolderPath,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> List[str]:
        """Simulate exporting separate clips"""
        output_path.ensure_exists()

        output_files = []
        total = len(items)

        for idx, item in enumerate(items):
            # Simulate per-clip processing
            await asyncio.sleep(0.1)

            extension = "mp4" if item.item_type == "video" else "jpg"
            filename = f"clip_{idx + 1}.{extension}"
            file_path = Path(output_path.value) / filename

            with open(file_path, 'wb') as f:
                f.write(b"DUMMY_CLIP_CONTENT")

            output_files.append(str(file_path))

            if progress_callback:
                progress_callback((idx + 1) / total)

        return output_files
