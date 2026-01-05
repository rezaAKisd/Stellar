"""Local File Storage Implementation"""
from pathlib import Path
from typing import List, Optional
import json
import subprocess
import platform

from ..domain.interfaces import IFileStorage
from ..domain.value_objects import FolderPath, SessionToken


class FileStorageLocal(IFileStorage):
    """Local file system storage implementation"""

    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.session_file = self.base_path / ".session"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def create_project_folders(self, base_path: FolderPath) -> tuple[FolderPath, FolderPath]:
        """Create downloads/ and exports/ folders"""
        base_path.ensure_exists()

        downloads = base_path / "downloads"
        exports = base_path / "exports"

        downloads.ensure_exists()
        exports.ensure_exists()

        return downloads, exports

    def save_media(self, data: bytes, path: FolderPath, filename: str) -> str:
        """Save media file"""
        path.ensure_exists()
        file_path = Path(path.value) / filename

        with open(file_path, 'wb') as f:
            f.write(data)

        return str(file_path)

    def list_exports(self, exports_path: FolderPath) -> List[str]:
        """List all export files"""
        if not exports_path.value.exists():
            return []

        return [
            str(f) for f in exports_path.value.iterdir()
            if f.is_file()
        ]

    def open_folder_in_explorer(self, path: FolderPath) -> None:
        """Open folder in OS file explorer"""
        path.ensure_exists()

        system = platform.system()
        try:
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(path.value)], check=True)
            elif system == "Windows":
                subprocess.run(["explorer", str(path.value)], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(path.value)], check=True)
        except Exception as e:
            print(f"Failed to open folder: {e}")

    def save_session(self, token: SessionToken) -> None:
        """Save session token to file"""
        data = {"token": token.value}
        with open(self.session_file, 'w') as f:
            json.dump(data, f)

    def load_session(self) -> Optional[SessionToken]:
        """Load saved session token"""
        if not self.session_file.exists():
            return None

        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)
                return SessionToken(data.get("token", ""))
        except Exception:
            return None
