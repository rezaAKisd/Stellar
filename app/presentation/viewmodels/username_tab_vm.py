"""Username Tab ViewModel"""
import asyncio
from qtpy.QtCore import QObject, Signal

from ..store import AppStore
from ...application.use_cases import AddUsernameUseCase
from ...infrastructure.container import DependencyContainer


class UsernameTabViewModel(QObject):
    """ViewModel for By Username tab"""

    users_changed = Signal(list)  # List[UserRowState]

    def __init__(self, store: AppStore, container: DependencyContainer):
        super().__init__()
        self.store = store
        self.container = container
        self.instagram = container.instagram_gateway
        self.storage = container.file_storage

        # Listen to store
        self.store.state_changed.connect(self._on_state_changed)

    def _on_state_changed(self):
        """Handle store changes"""
        self.users_changed.emit(self.store.state.users)

    def add_user(self, username: str):
        """Add a username"""
        if not username or not username.strip():
            self.store.show_toast("Please enter a username", "error")
            return

        asyncio.create_task(self._add_user_async(username.strip()))

    async def _add_user_async(self, username: str):
        """Async add user"""
        try:
            add_uc = AddUsernameUseCase(self.instagram, self.storage)
            user_dto = await add_uc.execute(username)

            self.store.add_user(user_dto.username, user_dto.display_name, user_dto.id)
            self.store.show_toast(f"Added @{user_dto.username}", "success")

        except Exception as e:
            self.store.show_toast(f"Error: {str(e)}", "error")

    def open_user(self, username: str):
        """Open user detail view"""
        self.store.open_user_detail(username)

    def remove_user(self, user_id: str):
        """Remove a user"""
        self.store.remove_user(user_id)
        self.store.show_toast("User removed", "info")
