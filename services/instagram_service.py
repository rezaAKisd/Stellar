from __future__ import annotations

try:
    from aiograpi import Client
except ImportError:  # pragma: no cover - optional dependency
    Client = None


class InstagramService:
    def __init__(self):
        self.client = Client() if Client else None

    def connect_with_session_id(self, session_id: str) -> str:
        if not self.client:
            raise RuntimeError("aiograpi is not installed.")
        if not session_id:
            raise ValueError("Session token is required.")
        self.client.login_by_sessionid(session_id)
        return session_id
