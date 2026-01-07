"""Main Window ViewModel - Updated for new auth system"""
from qtpy.QtCore import QObject, Signal

from ..store import AppStore
from ...infrastructure.container import DependencyContainer


class MainViewModel(QObject):
    """ViewModel for main window orchestration"""

    def __init__(self, store: AppStore, container: DependencyContainer):
        super().__init__()
        self.store = store
        self.container = container

        # Listen to store changes
        self.store.state_changed.connect(self._on_state_changed)
        self.store.auth_changed.connect(self._on_auth_changed)

    def _on_state_changed(self):
        """Handle store state changes"""
        # Update any main window state as needed
        pass

    def _on_auth_changed(self):
        """Handle authentication state changes"""
        if self.store.state.auth.is_authenticated:
            self._update_connection_status()

    def _update_connection_status(self):
        """Update status bar with connection info"""
        is_auth = self.container.instagram_gateway.is_authenticated()
        status = "Online" if is_auth else "Offline"

        # Count active downloads
        active = len([p for p in self.store.state.link_projects if p.is_busy])

        self.store.update_status_bar(status, active)
