"""Stubbed Instagram Gateway - Simulates Instagram API"""
import asyncio
from typing import List, Optional, Callable
from pathlib import Path
import random

from ..domain.interfaces import IInstagramGateway
from ..domain.entities import HighlightItem, UserHighlight
from ..domain.value_objects import HighlightUrl, Username, FolderPath, SessionToken


class InstagramGatewayStub(IInstagramGateway):
    """Stub implementation for testing/demo"""

    def __init__(self):
        self._authenticated = False

    async def authenticate_with_session(self, token: SessionToken) -> bool:
        """Simulate session authentication"""
        await asyncio.sleep(0.5)  # Simulate network delay
        self._authenticated = token.is_valid()
        return self._authenticated

    async def fetch_user_highlights(self, username: Username) -> List[UserHighlight]:
        """Simulate fetching user highlights"""
        await asyncio.sleep(1.0)  # Simulate network delay

        # Generate 6-12 fake highlights
        count = random.randint(6, 12)
        highlights = []

        highlight_names = [
            "Travel", "Food", "Fitness", "Work", "Family", "Pets",
            "Music", "Art", "Nature", "Fashion", "Sports", "Friends"
        ]

        for i in range(count):
            name = random.choice(highlight_names)
            highlights.append(UserHighlight(
                name=f"{name} {i+1}",
                cover_url=f"https://picsum.photos/200/300?random={i}",
                item_count=random.randint(3, 15),
                highlight_id=f"highlight_{username.value}_{i}"
            ))

        return highlights

    async def fetch_highlight_metadata(self, url: HighlightUrl) -> dict:
        """Simulate fetching highlight metadata"""
        await asyncio.sleep(0.5)

        return {
            "title": f"Highlight from {url.value[:30]}",
            "item_count": random.randint(5, 20),
            "owner": "sample_user"
        }

    async def fetch_highlight_items(self, highlight_id: str) -> List[HighlightItem]:
        """Simulate fetching highlight items"""
        await asyncio.sleep(0.8)

        # Generate 5-15 fake items
        count = random.randint(5, 15)
        items = []

        for i in range(count):
            item_type = random.choice(["image", "image", "video"])  # More images
            items.append(HighlightItem(
                item_type=item_type,
                url=f"https://picsum.photos/600/800?random={i}",
                thumbnail_url=f"https://picsum.photos/200/300?random={i}"
            ))

        return items

    async def download_item(
        self,
        item: HighlightItem,
        destination: FolderPath,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """Simulate downloading an item"""
        destination.ensure_exists()

        # Simulate download with progress updates
        steps = 20
        for step in range(steps):
            await asyncio.sleep(0.05)  # 50ms per step = ~1s total
            if progress_callback:
                progress_callback((step + 1) / steps)

        # Create a dummy file
        extension = "jpg" if item.item_type == "image" else "mp4"
        filename = f"{item.id}.{extension}"
        file_path = Path(destination.value) / filename

        # Write small dummy content
        with open(file_path, 'wb') as f:
            f.write(b"DUMMY_CONTENT")

        return str(file_path)
