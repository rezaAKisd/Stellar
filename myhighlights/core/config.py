"""Application configuration"""
from pathlib import Path


class Config:
    """Application configuration"""

    # Paths
    BASE_DIR = Path(__file__).resolve().parents[2]
    DATA_DIR = BASE_DIR / "data"
    HIGHLIGHTS_DIR = DATA_DIR / "Highlights"
    SESSION_DIR = DATA_DIR / ".session"
    JOBS_FILE = DATA_DIR / "jobs.json"

    # Instagram
    INSTAGRAM_SESSION_FILE = SESSION_DIR / "instagram_session.json"

    # Video settings
    DEFAULT_IMAGE_DURATION = 3  # seconds
    DEFAULT_VIDEO_RESOLUTION = (1080, 1920)  # 9:16 Instagram story
    DEFAULT_FPS = 30

    # UI
    TOAST_DURATION = 3000  # milliseconds

    @classmethod
    def ensure_dirs(cls):
        """Create necessary directories"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.HIGHLIGHTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.SESSION_DIR.mkdir(parents=True, exist_ok=True)
