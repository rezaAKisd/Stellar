"""Instagram Gateway Adapter - Wraps myhighlights InstagramService"""
import logging
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime
import uuid

from ..domain.interfaces import IInstagramGateway
from ..domain.entities import UserHighlight, HighlightItem
from ..domain.value_objects import HighlightUrl, Username, FolderPath, SessionToken

logger = logging.getLogger(__name__)


class InstagramGatewayAiograpi(IInstagramGateway):
    """
    Instagram gateway adapter that wraps the myhighlights InstagramService.

    This adapter translates between app/ domain types and myhighlights service types,
    maintaining clean architecture layer separation.
    """

    def __init__(self, session_dir: Path):
        """
        Initialize Instagram gateway with session directory.

        Args:
            session_dir: Directory for storing Instagram session data
        """
        # Import here to avoid circular dependencies
        from myhighlights.services.instagram import InstagramService

        self.service = InstagramService(session_dir)
        self.session_dir = session_dir

    async def login(
        self,
        username: str,
        password: str,
        verification_code: Optional[str] = None
    ) -> tuple[bool, Optional[str], bool]:
        """
        Login to Instagram.

        Args:
            username: Instagram username
            password: Instagram password
            verification_code: Optional 2FA verification code

        Returns:
            Tuple of (success: bool, error_message: Optional[str], needs_2fa: bool)
        """
        try:
            success, error_message = await self.service.login(
                username, password, verification_code
            )

            # Check if error indicates 2FA is required
            needs_2fa = error_message == "2FA_REQUIRED"

            return success, error_message, needs_2fa

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False, f"Login error: {str(e)}", False

    async def restore_session(self) -> tuple[bool, Optional[str]]:
        """
        Attempt to restore saved session.

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            success, username_or_error = await self.service.restore_session()

            if success:
                # username_or_error is the username on success
                return True, None
            else:
                # username_or_error is the error message on failure
                return False, username_or_error

        except Exception as e:
            logger.error(f"Session restoration error: {str(e)}")
            return False, f"Session restoration error: {str(e)}"

    async def logout(self) -> None:
        """Logout and clear session"""
        try:
            await self.service.logout()
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")

    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        return self.service.is_logged_in()

    async def authenticate_with_session(self, token: SessionToken) -> bool:
        """
        Authenticate using session token.

        Note: This method is not implemented as the Instagram service uses
        file-based session storage. Use restore_session() instead.
        """
        # The Instagram service uses file-based session storage,
        # so this method is not applicable
        logger.warning("authenticate_with_session called but not implemented")
        return False

    async def fetch_user_highlights(self, username: Username) -> List[UserHighlight]:
        """
        Fetch all highlights for a user.

        Args:
            username: Instagram username

        Returns:
            List of UserHighlight entities
        """
        try:
            # Call the service method to get user highlights
            highlights_data = await self.service.get_user_highlights(str(username))

            # Convert to domain entities
            user_highlights = []
            for hl_data in highlights_data:
                user_highlight = UserHighlight(
                    id=str(uuid.uuid4()),  # Generate unique ID
                    name=hl_data.get('title', 'Untitled'),
                    cover_url=hl_data.get('cover_url', ''),
                    item_count=hl_data.get('total_items', 0),
                    highlight_id=hl_data.get('id', ''),
                    project_id=None  # Not linked to a project yet
                )
                user_highlights.append(user_highlight)

            return user_highlights

        except Exception as e:
            logger.error(f"Error fetching user highlights: {str(e)}")
            raise ValueError(f"Failed to fetch user highlights: {str(e)}")

    async def fetch_highlight_metadata(self, url: HighlightUrl) -> dict:
        """
        Fetch metadata for a highlight from URL.

        Args:
            url: Instagram highlight URL

        Returns:
            Dictionary with highlight metadata
        """
        try:
            # Call the service method to get highlight info
            info = await self.service.get_highlight_info(url.value)

            return {
                'id': info.get('id', ''),
                'title': info.get('title', 'Untitled'),
                'cover_url': info.get('cover_url', ''),
                'total_items': info.get('total_items', 0)
            }

        except Exception as e:
            logger.error(f"Error fetching highlight metadata: {str(e)}")
            raise ValueError(f"Failed to fetch highlight metadata: {str(e)}")

    async def fetch_highlight_items(self, highlight_id: str) -> List[HighlightItem]:
        """
        Fetch all items in a highlight.

        Args:
            highlight_id: Instagram highlight ID

        Returns:
            List of HighlightItem entities
        """
        try:
            # Call the service method to get highlight info with items
            info = await self.service.get_highlight_info_by_id(highlight_id)

            # Convert items to domain entities
            items = []
            for item_data in info.get('items', []):
                item = HighlightItem(
                    id=str(uuid.uuid4()),  # Generate unique ID
                    item_type=item_data.get('type', 'image'),
                    url=item_data.get('url', ''),
                    thumbnail_url=item_data.get('thumbnail_url', ''),
                    downloaded_path=None,
                    created_at=datetime.now()
                )
                items.append(item)

            return items

        except Exception as e:
            logger.error(f"Error fetching highlight items: {str(e)}")
            raise ValueError(f"Failed to fetch highlight items: {str(e)}")

    async def download_item(
        self,
        item: HighlightItem,
        destination: FolderPath,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """
        Download a single item.

        Args:
            item: HighlightItem to download
            destination: Destination folder path
            progress_callback: Optional progress callback

        Returns:
            Local file path of downloaded item
        """
        try:
            # Ensure destination exists
            destination.ensure_exists()

            # Download the item using the service
            local_path = await self.service.download_media(
                item.url,
                destination.value,
                progress_callback
            )

            return str(local_path)

        except Exception as e:
            logger.error(f"Error downloading item: {str(e)}")
            raise ValueError(f"Failed to download item: {str(e)}")
