"""Domain Value Objects - Immutable, validated values"""
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class HighlightUrl:
    """Instagram highlight URL value object"""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("HighlightUrl must be a non-empty string")
        # Basic validation - can be enhanced
        if not ("instagram.com" in self.value or "instagr.am" in self.value):
            raise ValueError("Invalid Instagram URL")

    @property
    def slug(self) -> str:
        """Generate a safe slug from URL for folder naming"""
        safe = re.sub(r'[^\w\-]', '_', self.value)
        return safe[:50]  # Limit length


@dataclass(frozen=True)
class Username:
    """Instagram username value object"""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Username must be a non-empty string")
        if not re.match(r'^[a-zA-Z0-9._]+$', self.value):
            raise ValueError("Invalid username format")
        object.__setattr__(self, 'value', self.value.lstrip('@'))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class FolderPath:
    """File system folder path value object"""
    value: Path

    def __post_init__(self):
        if not isinstance(self.value, Path):
            object.__setattr__(self, 'value', Path(self.value))

    def ensure_exists(self) -> None:
        """Create folder if it doesn't exist"""
        self.value.mkdir(parents=True, exist_ok=True)

    def __truediv__(self, other) -> 'FolderPath':
        return FolderPath(self.value / other)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class SessionToken:
    """Encrypted/safe session token"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("SessionToken cannot be empty")

    def is_valid(self) -> bool:
        """Basic validation - can be enhanced"""
        return len(self.value) > 10
