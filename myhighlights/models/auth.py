"""Authentication state model"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class AuthState:
    """Authentication state"""
    is_logged_in: bool = False
    username: Optional[str] = None
    session_file: Optional[str] = None
    needs_2fa: bool = False
    error_message: Optional[str] = None
