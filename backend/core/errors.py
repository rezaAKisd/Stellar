"""Error categorization and handling utilities"""
from enum import Enum
from typing import Optional


class ErrorCategory(Enum):
    """Categories of errors that can occur"""
    NETWORK_ERROR = "network"           # Retry automatically
    AUTH_ERROR = "auth"                 # Require re-login
    NOT_FOUND = "not_found"            # Don't retry
    RATE_LIMIT = "rate_limit"          # Retry with delay
    INSTAGRAM_BLOCKED = "blocked"       # User action needed
    VALIDATION_ERROR = "validation"     # Bad input
    PERMISSION_ERROR = "permission"     # Access denied
    QUOTA_EXCEEDED = "quota"           # Quota limit hit
    EXPIRED = "expired"                # Resource expired
    UNKNOWN = "unknown"                # Uncategorized


class CategorizedError(Exception):
    """Exception with categorization and user-friendly message"""

    def __init__(
        self,
        category: ErrorCategory,
        user_message: str,
        technical_message: Optional[str] = None,
        should_retry: bool = False,
        retry_after: Optional[int] = None
    ):
        self.category = category
        self.user_message = user_message
        self.technical_message = technical_message or user_message
        self.should_retry = should_retry
        self.retry_after = retry_after  # seconds
        super().__init__(self.user_message)


def categorize_instagram_error(error: Exception) -> CategorizedError:
    """
    Categorize Instagram API errors into user-friendly categories.

    Args:
        error: The exception from Instagram API

    Returns:
        CategorizedError with appropriate category and message
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Not found errors
    if "not found" in error_str or "404" in error_str:
        return CategorizedError(
            category=ErrorCategory.NOT_FOUND,
            user_message=(
                "Content not found. The highlight may have been deleted, expired, "
                "or is no longer accessible."
            ),
            technical_message=str(error),
            should_retry=False
        )

    # Rate limiting
    if "rate limit" in error_str or "429" in error_str or "too many requests" in error_str:
        return CategorizedError(
            category=ErrorCategory.RATE_LIMIT,
            user_message=(
                "Instagram rate limit reached. Please wait a few minutes before trying again."
            ),
            technical_message=str(error),
            should_retry=True,
            retry_after=300  # 5 minutes
        )

    # Authentication errors
    if "login required" in error_str or "401" in error_str or "unauthorized" in error_str:
        return CategorizedError(
            category=ErrorCategory.AUTH_ERROR,
            user_message=(
                "Instagram login required. Please sign out and sign in again."
            ),
            technical_message=str(error),
            should_retry=False
        )

    # Forbidden / Blocked
    if "403" in error_str or "forbidden" in error_str or "blocked" in error_str:
        return CategorizedError(
            category=ErrorCategory.INSTAGRAM_BLOCKED,
            user_message=(
                "Instagram blocked this request. This is usually a temporary restriction. "
                "Try again later or use a different network."
            ),
            technical_message=str(error),
            should_retry=True,
            retry_after=3600  # 1 hour
        )

    # Network errors
    if any(keyword in error_str for keyword in ["timeout", "connection", "network", "unreachable"]):
        return CategorizedError(
            category=ErrorCategory.NETWORK_ERROR,
            user_message=(
                "Network error. Please check your connection and try again."
            ),
            technical_message=str(error),
            should_retry=True,
            retry_after=30
        )

    # Permission errors
    if "permission" in error_str or "access denied" in error_str:
        return CategorizedError(
            category=ErrorCategory.PERMISSION_ERROR,
            user_message=(
                "Access denied. The content may be private or you don't have permission to access it."
            ),
            technical_message=str(error),
            should_retry=False
        )

    # Default to unknown
    return CategorizedError(
        category=ErrorCategory.UNKNOWN,
        user_message="An unexpected error occurred. Please try again.",
        technical_message=str(error),
        should_retry=False
    )
