"""Async image loader with LRU cache"""
import asyncio
import logging
from pathlib import Path
from typing import Optional
from collections import OrderedDict

import requests
from qtpy.QtWidgets import QLabel
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QPixmap

logger = logging.getLogger(__name__)


class ImageCache:
    """LRU cache for loaded images"""

    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._max_size = max_size

    def get(self, url: str) -> Optional[QPixmap]:
        """Get image from cache"""
        if url in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(url)
            return self._cache[url]
        return None

    def put(self, url: str, pixmap: QPixmap):
        """Put image in cache"""
        if url in self._cache:
            # Update existing
            self._cache.move_to_end(url)
            self._cache[url] = pixmap
        else:
            # Add new
            self._cache[url] = pixmap
            # Evict oldest if cache is full
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def clear(self):
        """Clear cache"""
        self._cache.clear()


# Global image cache
_image_cache = ImageCache(max_size=100)


class AsyncImageLabel(QLabel):
    """Label that loads images asynchronously with caching"""

    image_loaded = Signal(bool)  # success

    def __init__(self, placeholder_text: str = "Loading...", size: tuple = (80, 80)):
        super().__init__()
        self._url: Optional[str] = None
        self._loading = False
        self._size = size
        self._placeholder_text = placeholder_text

        # Setup
        self.setFixedSize(*size)
        self.setScaledContents(True)
        self.setAlignment(Qt.AlignCenter)
        self.setObjectName("async-image")

        # Show placeholder initially
        self.setText(placeholder_text)

    def load_url(self, url: str, placeholder_pixmap: Optional[QPixmap] = None):
        """Load image from URL asynchronously"""
        if not url:
            self.setText("No\nImage")
            return

        self._url = url

        # Check cache first
        cached = _image_cache.get(url)
        if cached:
            self.setPixmap(cached)
            self.image_loaded.emit(True)
            return

        # Show placeholder
        if placeholder_pixmap:
            self.setPixmap(placeholder_pixmap)
        else:
            self.setText(self._placeholder_text)

        # Load in background
        if not self._loading:
            self._loading = True
            asyncio.create_task(self._load_async(url))

    async def _load_async(self, url: str):
        """Load image in background thread"""
        try:
            # Download image in background thread
            response = await asyncio.to_thread(
                requests.get, url, timeout=10
            )
            response.raise_for_status()

            # Load pixmap
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)

            if not pixmap.isNull():
                # Cache it
                _image_cache.put(url, pixmap)

                # Update UI (only if URL hasn't changed)
                if self._url == url:
                    self.setPixmap(pixmap)
                    self.image_loaded.emit(True)
            else:
                raise ValueError("Invalid image data")

        except Exception as e:
            logger.warning(f"Failed to load image from {url}: {e}")
            if self._url == url:
                self.setText("Error")
                self.image_loaded.emit(False)

        finally:
            self._loading = False

    def clear_image(self):
        """Clear current image and show placeholder"""
        self._url = None
        self.setText(self._placeholder_text)

    @staticmethod
    def clear_cache():
        """Clear global image cache"""
        _image_cache.clear()
