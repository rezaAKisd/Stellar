"""Instagram service using aiograpi"""
import asyncio
import inspect
import re
import base64
import json
import logging
from pathlib import Path
from typing import Optional, List, Callable, Tuple
import time
import requests

logger = logging.getLogger(__name__)

try:
    from aiograpi import Client
    from aiograpi.exceptions import (
        TwoFactorRequired,
        ChallengeRequired,
        LoginRequired,
        ClientError
    )
    AIOGRAPI_AVAILABLE = True
except ImportError:
    AIOGRAPI_AVAILABLE = False
    print("Warning: aiograpi not installed. Instagram features will be limited.")


class InstagramService:
    """Instagram API service using aiograpi"""

    def __init__(self, session_dir: Path):
        if not AIOGRAPI_AVAILABLE:
            raise ImportError("aiograpi is required. Install with: pip install aiograpi")

        self.client = Client()
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.session_dir / "instagram_session.json"
        self.user_file = self.session_dir / "user.json"
        self._logged_in = False

    async def _run_client(self, func, *args, **kwargs):
        """Run an aiograpi call without blocking the UI event loop."""
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return await asyncio.to_thread(func, *args, **kwargs)

    @staticmethod
    def _parse_highlight_id_from_url(url: str) -> Optional[str]:
        """Extract highlight id from known URL formats."""
        if not url:
            return None
        match = re.search(r"/s/([A-Za-z0-9_-]+)", url)
        if match:
            token = match.group(1)
            padded = token + "=" * (-len(token) % 4)
            try:
                decoded = base64.urlsafe_b64decode(padded).decode("utf-8", "ignore")
                token_match = re.search(r"highlight:(\d+)", decoded)
                if token_match:
                    return token_match.group(1)
                digits_match = re.search(r"(\d+)", decoded)
                if digits_match:
                    return digits_match.group(1)
            except Exception:
                pass
        match = re.search(r"stories/highlights/(\d+)", url)
        if match:
            return match.group(1)
        match = re.search(r"highlights/(\d+)", url)
        if match:
            return match.group(1)
        match = re.search(r"highlight_id[\"']?\s*[:=]\s*[\"']?(\d+)", url)
        if match:
            return match.group(1)
        return None

    async def _resolve_highlight_id(self, highlight_url: str) -> Optional[str]:
        """Resolve highlight id from share links or non-standard URLs."""
        highlight_id = self._parse_highlight_id_from_url(highlight_url)
        if highlight_id:
            return highlight_id

        if hasattr(self.client, "highlight_id_from_url"):
            try:
                resolved = await self._run_client(self.client.highlight_id_from_url, highlight_url)
                if resolved:
                    return str(resolved)
            except Exception as e:
                logger.warning(f"highlight_id_from_url failed: {e}")

        def fetch():
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            return requests.get(highlight_url, allow_redirects=True, timeout=15, headers=headers)

        try:
            response = await asyncio.to_thread(fetch)
        except Exception as e:
            logger.warning(f"Failed to resolve highlight URL: {e}")
            return None

        highlight_id = self._parse_highlight_id_from_url(response.url)
        if highlight_id:
            return highlight_id

        return self._parse_highlight_id_from_url(response.text)

    async def login(
        self,
        username: str,
        password: str,
        verification_code: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Login to Instagram
        Returns: (success, error_message)
        """
        import sys
        print("\n" + "=" * 60, file=sys.stderr)
        print("INSTAGRAM SERVICE: Login attempt", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        logger.info("=" * 60)
        logger.info("INSTAGRAM SERVICE: Login attempt")
        logger.info("=" * 60)
        logger.info(f"Username: {username}")
        logger.info(f"Password length: {len(password)}")
        logger.info(f"2FA code: {verification_code if verification_code else '(None)'}")
        logger.info(f"Session file exists: {self.session_file.exists()}")

        print(f"Username: {username}", file=sys.stderr)
        print(f"Password length: {len(password)}", file=sys.stderr)
        print(f"2FA code: {verification_code if verification_code else '(None)'}", file=sys.stderr)
        print(f"Session file exists: {self.session_file.exists()}", file=sys.stderr)

        try:
            # Try to load existing session first
            if self.session_file.exists():
                print("Attempting to load existing session...", file=sys.stderr)
                logger.info("Attempting to load existing session...")
                try:
                    await self._run_client(self.client.load_settings, str(self.session_file))
                    print("Session loaded, attempting login...", file=sys.stderr)
                    logger.info("Session loaded, attempting login...")
                    await self._run_client(self.client.login, username, password)
                    self._logged_in = True
                    print("✓ Login successful with existing session", file=sys.stderr)
                    logger.info("✓ Login successful with existing session")
                    return True, None
                except Exception as e:
                    print(f"Session invalid, will try fresh login: {e}", file=sys.stderr)
                    logger.warning(f"Session invalid, will try fresh login: {e}")
                    # Session invalid, continue with fresh login
                    pass

            # Fresh login
            print("Performing fresh login...", file=sys.stderr)
            logger.info("Performing fresh login...")
            # Only pass verification_code if it's not empty
            if verification_code and verification_code.strip():
                print("Using 2FA code for login", file=sys.stderr)
                logger.info("Using 2FA code for login")
                await self._run_client(
                    self.client.login,
                    username,
                    password,
                    verification_code=verification_code
                )
            else:
                print("Logging in without 2FA code", file=sys.stderr)
                logger.info("Logging in without 2FA code")
                await self._run_client(self.client.login, username, password)

            # Save session
            print("Saving session to file...", file=sys.stderr)
            logger.info("Saving session to file...")
            await self._run_client(self.client.dump_settings, str(self.session_file))
            self._save_username(username)
            self._logged_in = True
            print("✓ Login successful - session saved", file=sys.stderr)
            logger.info("✓ Login successful - session saved")
            return True, None

        except TwoFactorRequired as e:
            print("2FA required", file=sys.stderr)
            logger.warning("2FA required")
            return False, "2FA_REQUIRED"
        except ChallengeRequired as e:
            print(f"Challenge required: {e}", file=sys.stderr)
            logger.error(f"Challenge required: {e}")
            return False, f"Instagram challenge required. Please verify your account and try again."
        except LoginRequired as e:
            print(f"Login required: {e}", file=sys.stderr)
            logger.error(f"Login required: {e}")
            return False, "Invalid username or password"
        except ClientError as e:
            print(f"Client error: {e}", file=sys.stderr)
            logger.error(f"Client error: {e}")
            return False, f"Instagram error: {str(e)}"
        except Exception as e:
            print(f"Unexpected error during login: {e}", file=sys.stderr)
            logger.error(f"Unexpected error during login: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            return False, f"Login failed: {str(e)}"

    async def logout(self):
        """Logout and clear session"""
        if self.session_file.exists():
            self.session_file.unlink()
        if self.user_file.exists():
            self.user_file.unlink()
        self._logged_in = False

    def is_logged_in(self) -> bool:
        """Check if logged in"""
        return self._logged_in

    async def restore_session(self) -> Tuple[bool, Optional[str]]:
        """Restore a saved session without re-entering credentials."""
        if not self.session_file.exists():
            return False, "No saved session"

        try:
            await self._run_client(self.client.load_settings, str(self.session_file))

            username = self._load_username()
            if hasattr(self.client, "account_info"):
                info = await self._run_client(self.client.account_info)
                if hasattr(info, "username") and info.username:
                    username = info.username

            self._logged_in = True
            return True, username
        except Exception as e:
            logger.warning(f"Failed to restore session: {e}")
            self._logged_in = False
            return False, str(e)

    async def get_highlight_info_by_id(self, highlight_id: str) -> dict:
        """
        Get highlight information by ID (used for 'By Username' tab)
        Returns: {
            'id': str,
            'title': str,
            'cover_url': str,
            'items': List[dict],
            'total_items': int
        }
        """
        if not self._logged_in:
            raise LoginRequired("Please login first")

        try:
            # Fetch highlight directly by ID
            highlight = await self._run_client(self.client.highlight_info, highlight_id)

            def get_attr(obj, name, default=None):
                if isinstance(obj, dict):
                    return obj.get(name, default)
                return getattr(obj, name, default)

            def pick_image_url(data):
                if isinstance(data, dict):
                    # Check for cropped_image_version first (used in highlights list)
                    cropped = data.get("cropped_image_version")
                    if cropped and isinstance(cropped, dict):
                        url = cropped.get("url")
                        if url:
                            return url

                    # Check for image_versions2 (used in media items)
                    image_versions = data.get("image_versions2") or {}
                    candidates = image_versions.get("candidates") or []
                    if candidates:
                        return candidates[0].get("url")

                    # Fall back to thumbnail_url or display_url
                    return data.get("thumbnail_url") or data.get("display_url")
                return get_attr(data, "thumbnail_url")

            def extract_media(item):
                if not isinstance(item, dict):
                    video_url = get_attr(item, "video_url")
                    thumb_url = get_attr(item, "thumbnail_url")
                    if video_url:
                        return str(video_url), "video", str(thumb_url) if thumb_url else ""
                    if thumb_url:
                        return str(thumb_url), "image", str(thumb_url)
                    image_url = get_attr(item, "image_url")
                    if image_url:
                        return str(image_url), "image", str(image_url)
                    return "", "image", ""

                video_versions = item.get("video_versions") or []
                video_url = video_versions[0].get("url") if video_versions else None
                thumb_url = pick_image_url(item)
                if video_url:
                    return str(video_url), "video", str(thumb_url) if thumb_url else ""
                if thumb_url:
                    return str(thumb_url), "image", str(thumb_url)
                return "", "image", ""

            raw_items = get_attr(highlight, "items") or []
            items = []
            for item in raw_items:
                media_url, media_type, thumb_url = extract_media(item)
                items.append({
                    'url': media_url,
                    'type': media_type,
                    'thumbnail_url': thumb_url,
                })

            cover_url = ""
            cover_media = get_attr(highlight, "cover_media")
            if cover_media:
                cover_url = str(pick_image_url(cover_media) or "")

            return {
                'id': str(get_attr(highlight, "pk") or highlight_id),
                'title': get_attr(highlight, "title") or f"Highlight {highlight_id}",
                'cover_url': cover_url,
                'items': items,
                'total_items': len(items)
            }

        except Exception as e:
            raise ValueError(f"Failed to fetch highlight: {str(e)}")

    async def get_highlight_info(self, highlight_url: str) -> dict:
        """
        Get highlight information from URL
        Returns: {
            'id': str,
            'title': str,
            'cover_url': str,
            'items': List[dict],
            'total_items': int
        }
        """
        if not self._logged_in:
            raise LoginRequired("Please login first")

        try:
            highlight_id = await self._resolve_highlight_id(highlight_url)
            if not highlight_id:
                raise ValueError("Invalid highlight URL format or share link not resolvable")

            # Reuse the by-ID method
            return await self.get_highlight_info_by_id(highlight_id)

        except Exception as e:
            raise ValueError(f"Failed to fetch highlight: {str(e)}")

    def _save_username(self, username: str) -> None:
        """Persist the last logged-in username."""
        try:
            self.user_file.write_text(
                json.dumps({"username": username}),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Failed to save username: {e}")

    def _load_username(self) -> Optional[str]:
        """Load the last logged-in username."""
        if not self.user_file.exists():
            return None
        try:
            content = self.user_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return data.get("username")
        except Exception as e:
            logger.warning(f"Failed to load username: {e}")
        return None

    async def download_media(
        self,
        url: str,
        destination: Path,
        filename: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Path:
        """Download a single media file"""
        loop = asyncio.get_running_loop()

        def _download() -> Path:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))

            # Generate filename if not provided
            local_name = filename
            if local_name is None:
                content_type = response.headers.get('content-type', '')
                extension = 'mp4' if 'video' in content_type else 'jpg'
                local_name = f"{hash(url)}_{int(time.time())}.{extension}"

            filepath = destination / local_name

            downloaded = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            loop.call_soon_threadsafe(
                                progress_callback,
                                downloaded,
                                total_size
                            )

            return filepath

        try:
            return await asyncio.to_thread(_download)
        except Exception as e:
            raise IOError(f"Failed to download media: {str(e)}")

    async def get_user_highlights(self, username: str) -> List[dict]:
        """Get all highlights for a user (for future 'By Username' tab)"""
        if not self._logged_in:
            raise LoginRequired("Please login first")

        try:
            user_id = await self._run_client(self.client.user_id_from_username, username)
            highlights = await self._run_client(self.client.user_highlights, user_id)

            def get_attr(obj, name, default=None):
                """Get attribute from object or dict"""
                if isinstance(obj, dict):
                    return obj.get(name, default)
                return getattr(obj, name, default)

            def pick_image_url(data):
                """Extract image URL from various response formats"""
                if isinstance(data, dict):
                    # Check for cropped_image_version first (used in highlights list)
                    cropped = data.get("cropped_image_version")
                    if cropped and isinstance(cropped, dict):
                        url = cropped.get("url")
                        if url:
                            return url

                    # Check for image_versions2 (used in media items)
                    image_versions = data.get("image_versions2") or {}
                    candidates = image_versions.get("candidates") or []
                    if candidates:
                        return candidates[0].get("url")

                    # Fall back to thumbnail_url or display_url
                    return data.get("thumbnail_url") or data.get("display_url")
                return get_attr(data, "thumbnail_url")

            result = []
            for highlight in highlights:
                # Extract cover URL
                cover_url = ""
                cover_media = get_attr(highlight, "cover_media")
                if cover_media:
                    cover_url = str(pick_image_url(cover_media) or "")

                # Extract item count - use media_count if available, otherwise try items
                item_count = get_attr(highlight, "media_count")
                if item_count is None:
                    items = get_attr(highlight, "items")
                    item_count = len(items) if items else 0

                result.append({
                    'id': str(get_attr(highlight, "pk") or ""),
                    'title': get_attr(highlight, "title") or "Untitled",
                    'cover_url': cover_url,
                    'item_count': item_count or 0
                })

            return result

        except Exception as e:
            raise ValueError(f"Failed to fetch user highlights: {str(e)}")
