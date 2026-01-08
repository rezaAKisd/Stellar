"""Instagram Gateway Adapter - aiograpi-backed implementation"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional
import base64
import inspect
import re
import uuid

import anyio
import requests
from aiograpi import Client
from aiograpi import exceptions as ig_exceptions

from ..domain.entities import HighlightItem, UserHighlight
from ..domain.interfaces import IInstagramGateway
from ..domain.value_objects import FolderPath, HighlightUrl, SessionToken, Username

logger = logging.getLogger(__name__)

_HIGHLIGHT_ID_RE = re.compile(r"/highlights/(?P<id>\\d+)")


def _safe_model_dump(obj) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    dump = getattr(obj, "model_dump", None)
    if callable(dump):
        return dump()
    dump = getattr(obj, "dict", None)
    if callable(dump):
        return dump()
    return {}

def _extract_highlight_pk_from_share_url(url: str) -> Optional[str]:
    """
    Instagram sometimes shares highlights as `https://www.instagram.com/s/<token>?...`
    where `<token>` base64-decodes to something like `highlight:<numeric_id>`.
    """
    try:
        match = re.search(r"/s/([^/?#]+)", url)
        if not match:
            return None
        token = match.group(1)
        # Add padding if needed (base64 url-safe)
        padded = token + "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="ignore")
        if decoded.startswith("highlight:"):
            highlight_id = decoded.split("highlight:", 1)[1].strip()
            return highlight_id if highlight_id.isdigit() else None
        return None
    except Exception:
        return None


class InstagramGatewayAiograpi(IInstagramGateway):
    """
    Instagram gateway backed by aiograpi (sync client) exposed via async methods.

    Session persistence is handled via aiograpi settings file stored in `session_dir`.
    """

    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.session_dir / "aiograpi_settings.json"
        self.client = Client()

        if self.settings_path.exists():
            try:
                self.client.load_settings(self.settings_path)
            except Exception as e:
                logger.warning(f"Failed to load saved aiograpi settings: {e}")

    async def _call(self, fn, *args, **kwargs):
        """
        Call aiograpi methods safely.

        Newer aiograpi releases expose many methods as async coroutines while
        settings helpers remain sync.
        """
        if inspect.iscoroutinefunction(fn):
            return await fn(*args, **kwargs)

        result = fn(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    async def login(
        self,
        username: str,
        password: str,
        verification_code: Optional[str] = None,
    ) -> tuple[bool, Optional[str], bool]:
        try:
            code = verification_code or ""
            success = await self._call(self.client.login, username, password, False, code)
            if success:
                # Verify session is usable (Instagram may accept login but block private endpoints)
                try:
                    await self._call(self.client.account_info)
                except (ig_exceptions.ClientForbiddenError, ig_exceptions.ClientUnauthorizedError) as e:
                    logger.warning(f"Login verified but private API blocked: {e}")
                    return False, "INSTAGRAM_FORBIDDEN", False

                self.client.dump_settings(self.settings_path)
                return True, None, False
            return False, "Invalid credentials", False
        except ig_exceptions.TwoFactorRequired:
            return False, "2FA_REQUIRED", True
        except ig_exceptions.ChallengeRequired as e:
            logger.warning(f"Instagram challenge required: {e}")
            return False, "Challenge required by Instagram. Try again later.", False
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            return False, str(e), False

    async def restore_session(self) -> tuple[bool, Optional[str]]:
        if not self.settings_path.exists():
            return False, "No saved session"

        try:
            self.client.load_settings(self.settings_path)

            # Verify the session is still valid.
            await self._call(self.client.account_info)

            # Get username from client attribute or fall back to session directory name
            username = getattr(self.client, "username", None)
            if not username:
                # Extract username from session directory path
                username = self.session_dir.name

            return True, username
        except Exception as e:
            logger.info(f"Saved session invalid: {e}")
            return False, "Saved session invalid"

    async def logout(self) -> None:
        try:
            await self._call(self.client.logout)
        except Exception as e:
            logger.warning(f"Logout error: {e}")
        finally:
            try:
                if self.settings_path.exists():
                    self.settings_path.unlink()
            except Exception:
                pass

    def is_authenticated(self) -> bool:
        user_id = getattr(self.client, "user_id", None)
        return bool(user_id)

    async def authenticate_with_session(self, token: SessionToken) -> bool:
        logger.warning("authenticate_with_session is not supported; use restore_session() instead")
        return False

    async def fetch_user_highlights(self, username: Username) -> List[UserHighlight]:
        try:
            logger.info(f"Fetching user ID for username: {username}")
            user_id = await self._call(self.client.user_id_from_username, str(username))
            logger.info(f"Got user ID: {user_id}, fetching highlights...")

            # Fetch highlights with retry logic for GraphQL errors
            highlights = None
            try:
                highlights = await self._call(self.client.user_highlights, int(user_id), 0)
            except KeyError as e:
                # Instagram GraphQL API may return unexpected structure, retry with amount parameter
                logger.warning(f"KeyError when fetching highlights (GraphQL issue): {e}, retrying...")
                try:
                    highlights = await self._call(self.client.user_highlights, int(user_id))
                except Exception as retry_err:
                    logger.error(f"Retry failed: {retry_err}")
                    raise ValueError(f"Instagram API returned unexpected format. The account may have no highlights or the API format changed.")

            if not highlights:
                logger.info(f"No highlights found for user {username}")
                return []

            logger.info(f"Found {len(highlights)} highlights for user {username}")
            result: List[UserHighlight] = []
            for hl in highlights:
                hl_data = _safe_model_dump(hl)
                cover_media = hl_data.get("cover_media") or {}
                cover_media_data = _safe_model_dump(cover_media)

                highlight_id = str(hl_data.get("pk") or hl_data.get("id") or "")
                title = hl_data.get("title") or "Untitled"
                item_count = int(hl_data.get("media_count") or 0)
                cover_url = cover_media_data.get("thumbnail_url") or ""

                result.append(
                    UserHighlight(
                        id=str(uuid.uuid4()),
                        name=title,
                        cover_url=cover_url,
                        item_count=item_count,
                        highlight_id=highlight_id,
                        project_id=None,
                    )
                )

            logger.info(f"Successfully parsed {len(result)} highlights")
            return result
        except ig_exceptions.ClientLoginRequired:
            raise ValueError("Instagram login required. Please sign in again.")
        except ig_exceptions.ClientForbiddenError:
            raise ValueError(
                "Instagram blocked this request (403). This is usually a temporary restriction on your account/IP/device; try logging out/in, waiting, or using a different network/proxy."
            )
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error fetching user highlights: {e}", exc_info=True)
            raise ValueError(f"Failed to fetch user highlights: {str(e)}")

    async def fetch_highlight_metadata(self, url: HighlightUrl) -> dict:
        try:
            highlight_pk: Optional[str] = None

            # Most URLs look like `/stories/highlights/<id>/...` and work directly.
            if "/highlights/" in url.value:
                match = _HIGHLIGHT_ID_RE.search(url.value)
                if match:
                    highlight_pk = match.group("id")
                else:
                    highlight_pk = await self._call(self.client.highlight_pk_from_url, url.value)
            else:
                # Handle share URLs like `/s/<base64>`
                highlight_pk = _extract_highlight_pk_from_share_url(url.value)

            if not highlight_pk:
                raise ValueError('Invalid highlight URL (expected "/highlights/" or a highlight share link)')

            highlight = await self._call(self.client.highlight_info, str(highlight_pk))
            hl_data = _safe_model_dump(highlight)
            cover_media = _safe_model_dump(hl_data.get("cover_media"))
            return {
                "id": str(hl_data.get("pk") or hl_data.get("id") or highlight_pk),
                "title": hl_data.get("title") or "Untitled",
                "cover_url": cover_media.get("thumbnail_url") or "",
                "total_items": int(hl_data.get("media_count") or 0),
            }
        except ig_exceptions.ClientLoginRequired:
            raise ValueError("Instagram login required. Please sign in again.")
        except ig_exceptions.ClientForbiddenError:
            raise ValueError(
                "Instagram blocked this request (403). This is usually a temporary restriction on your account/IP/device; try logging out/in, waiting, or using a different network/proxy."
            )
        except Exception as e:
            logger.error(f"Error fetching highlight metadata: {e}", exc_info=True)
            raise ValueError(f"Failed to fetch highlight metadata: {e}")

    async def fetch_highlight_items(self, highlight_id: str) -> List[HighlightItem]:
        try:
            logger.info(f"Fetching items for highlight PK: {highlight_id}")
            highlight = await self._call(self.client.highlight_info, str(highlight_id))
            hl_data = _safe_model_dump(highlight)
            items = hl_data.get("items") or []

            logger.info(f"Found {len(items)} items in highlight {highlight_id}")

            result: List[HighlightItem] = []
            for story in items:
                story_data = _safe_model_dump(story)
                video_url = story_data.get("video_url") or ""
                thumbnail_url = story_data.get("thumbnail_url") or ""
                taken_at = story_data.get("taken_at")
                created_at = taken_at if isinstance(taken_at, datetime) else datetime.now()

                item_type = "video" if video_url else "image"
                media_url = video_url or thumbnail_url

                result.append(
                    HighlightItem(
                        id=str(uuid.uuid4()),
                        item_type=item_type,
                        url=media_url,
                        thumbnail_url=thumbnail_url,
                        downloaded_path=None,
                        created_at=created_at,
                    )
                )

            return result
        except ig_exceptions.ClientLoginRequired as e:
            from core.errors import CategorizedError, ErrorCategory
            raise CategorizedError(
                category=ErrorCategory.AUTH_ERROR,
                user_message="Instagram login required. Please sign out and sign in again.",
                technical_message=str(e)
            )
        except ig_exceptions.ClientForbiddenError as e:
            from core.errors import CategorizedError, ErrorCategory
            raise CategorizedError(
                category=ErrorCategory.INSTAGRAM_BLOCKED,
                user_message="Instagram blocked this request. Try again later or use a different network.",
                technical_message=str(e),
                should_retry=True,
                retry_after=3600
            )
        except ig_exceptions.ClientNotFoundError as e:
            from core.errors import CategorizedError, ErrorCategory
            raise CategorizedError(
                category=ErrorCategory.NOT_FOUND,
                user_message=f"Highlight not found (ID: {highlight_id}). It may have been deleted or expired.",
                technical_message=str(e)
            )
        except Exception as e:
            from core.errors import categorize_instagram_error
            error_str = str(e).lower()
            if "not found" in error_str:
                from core.errors import CategorizedError, ErrorCategory
                raise CategorizedError(
                    category=ErrorCategory.NOT_FOUND,
                    user_message=f"Highlight not found (ID: {highlight_id}). It may have been deleted or expired.",
                    technical_message=str(e)
                )
            logger.error(f"Error fetching highlight items: {e}", exc_info=True)
            categorized = categorize_instagram_error(e)
            raise categorized

    async def download_item(
        self,
        item: HighlightItem,
        destination: FolderPath,
        progress_callback: Optional[Callable[[float], None]] = None,
        index: Optional[int] = None,
    ) -> str:
        destination.ensure_exists()

        def _download_sync() -> str:
            import time
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            url = item.url
            if not url:
                raise ValueError("Missing media URL")

            ext = ".mp4" if item.item_type == "video" else ".jpg"
            # Include index and timestamp in filename for proper ordering
            if index is not None:
                timestamp = int(item.created_at.timestamp()) if item.created_at else 0
                filename = f"{index:04d}_{timestamp}_{item.id}{ext}"
            else:
                filename = f"{item.id}{ext}"
            output_path = Path(destination.value) / filename

            # Configure retry strategy for connection issues
            retry_strategy = Retry(
                total=5,  # Total number of retries
                backoff_factor=1,  # Wait 1, 2, 4, 8, 16 seconds between retries
                status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
                allowed_methods=["GET"],  # Only retry GET requests
                raise_on_status=False,  # Don't raise exception on failed retries
            )

            # Create session with retry adapter
            session = requests.Session()
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

            # Add browser-like headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
            }

            # Manual retry loop for SSL errors with resume capability
            max_attempts = 3
            last_error = None

            for attempt in range(max_attempts):
                try:
                    # Check if file partially exists and get its size for resume
                    existing_size = 0
                    if output_path.exists():
                        existing_size = output_path.stat().st_size
                        logger.info(f"Resuming download from byte {existing_size}")

                    # Add Range header for resuming if file partially exists
                    request_headers = headers.copy()
                    if existing_size > 0:
                        request_headers['Range'] = f'bytes={existing_size}-'

                    with session.get(url, stream=True, timeout=30, headers=request_headers) as response:
                        # 206 = Partial Content (resume), 200 = OK (fresh download)
                        if response.status_code not in [200, 206]:
                            response.raise_for_status()

                        # Get total size (handle both fresh and resumed downloads)
                        if response.status_code == 206:
                            # For partial content, parse Content-Range header
                            content_range = response.headers.get('Content-Range', '')
                            if content_range:
                                total = int(content_range.split('/')[-1])
                            else:
                                total = existing_size + int(response.headers.get("content-length") or 0)
                        else:
                            # Fresh download
                            total = int(response.headers.get("content-length") or 0)
                            existing_size = 0  # Reset if server doesn't support resume

                        downloaded = existing_size

                        # Open in append mode if resuming, write mode if fresh
                        file_mode = "ab" if existing_size > 0 and response.status_code == 206 else "wb"

                        with output_path.open(file_mode) as f:
                            for chunk in response.iter_content(chunk_size=1024 * 256):
                                if not chunk:
                                    continue
                                f.write(chunk)
                                if progress_callback and total > 0:
                                    downloaded += len(chunk)
                                    progress_callback(min(1.0, downloaded / total))

                    if progress_callback:
                        progress_callback(1.0)

                    logger.info(f"Download complete: {output_path}")
                    return str(output_path)

                except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                        logger.warning(f"SSL/Connection error on attempt {attempt + 1}/{max_attempts}, retrying in {wait_time}s: {e}")
                        # File remains partially downloaded for resume
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Failed after {max_attempts} attempts due to SSL/Connection error")
                        raise

            # If we get here, all retries failed
            raise ValueError(f"Failed to download after {max_attempts} attempts: {last_error}")

        try:
            return await anyio.to_thread.run_sync(_download_sync)
        except Exception as e:
            logger.error(f"Error downloading item: {e}", exc_info=True)
            raise ValueError(f"Failed to download item: {e}")
