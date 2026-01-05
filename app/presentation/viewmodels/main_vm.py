"""Main Window ViewModel"""
import asyncio
from qtpy.QtCore import QObject, Signal

from ..store import AppStore
from ...application.use_cases import ConnectSessionUseCase, LoadSavedSessionUseCase
from ...infrastructure.instagram_stub import InstagramGatewayStub
from ...infrastructure.storage_local import FileStorageLocal


class MainViewModel(QObject):
    """ViewModel for main window and header"""

    connection_changed = Signal(bool, bool, str)  # is_connected, session_present, status_text

    def __init__(self, store: AppStore):
        super().__init__()
        self.store = store
        self.storage = FileStorageLocal()
        self.instagram = InstagramGatewayStub()

        # Listen to store changes
        self.store.state_changed.connect(self._on_state_changed)

        # Load session on init
        asyncio.create_task(self._load_saved_session())

    def _on_state_changed(self):
        """Handle store state changes"""
        conn = self.store.state.connection
        self.connection_changed.emit(
            conn.is_connected,
            conn.session_present,
            conn.status_text
        )

    async def _load_saved_session(self):
        """Attempt to load saved session on startup"""
        use_case = LoadSavedSessionUseCase(self.instagram, self.storage)
        result = await use_case.execute()
        self.store.set_connection_state(result.is_connected, result.session_present)

    def connect_session(self, session_token: str):
        """Connect with session token"""
        asyncio.create_task(self._connect_session_async(session_token))

    async def _connect_session_async(self, session_token: str):
        """Async session connection"""
        use_case = ConnectSessionUseCase(self.instagram, self.storage)
        result = await use_case.execute(session_token)
        self.store.set_connection_state(result.is_connected, result.session_present)

        if result.is_connected:
            self.store.show_toast("Session saved", "success")
        else:
            self.store.show_toast(result.message, "error")

    def disconnect_session(self):
        """Disconnect session"""
        self.store.set_connection_state(False, False)
        self.store.show_toast("Disconnected", "info")
