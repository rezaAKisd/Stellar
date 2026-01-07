"""Central Application Store - Single source of truth"""
from qtpy.QtCore import QObject, Signal
from typing import Optional, Dict
from dataclasses import replace

from .models_ui import (
    AppUiState, ConnectionState, HighlightRowState, UserRowState,
    UserDetailState, UserHighlightCardState, ToastMessage,
    ViewMode, StatusType, AuthScreen, AuthState, SignInState, TwoFactorState
)
from ..domain.entities import HighlightProject
from ..application.dtos import HighlightProjectDTO, UserHighlightDTO


class AppStore(QObject):
    """Centralized application state store"""

    # Signals
    state_changed = Signal()
    toast_added = Signal(str, str)  # message, type
    auth_changed = Signal()  # Emitted when auth state changes

    def __init__(self):
        super().__init__()
        self._state = AppUiState()
        self._projects: Dict[str, HighlightProject] = {}  # Domain entities cache

    @property
    def state(self) -> AppUiState:
        """Get current state (immutable)"""
        return self._state

    def get_project(self, project_id: str) -> Optional[HighlightProject]:
        """Get domain project entity"""
        return self._projects.get(project_id)

    def set_connection_state(self, is_connected: bool, session_present: bool):
        """Update connection state"""
        status_text = "Connected" if is_connected else "Not connected"
        self._state.connection = ConnectionState(
            is_connected=is_connected,
            session_present=session_present,
            status_text=status_text
        )
        self.state_changed.emit()

    def add_link_project(self, project_dto: HighlightProjectDTO, project: HighlightProject):
        """Add a new link-based project"""
        row_state = self._dto_to_row_state(project_dto)
        self._state.link_projects.append(row_state)
        self._projects[project.id] = project
        self.state_changed.emit()

    def update_link_project(self, project_id: str, project: HighlightProject):
        """Update an existing link project"""
        for idx, row in enumerate(self._state.link_projects):
            if row.id == project_id:
                self._state.link_projects[idx] = self._project_to_row_state(project)
                self._projects[project_id] = project
                self.state_changed.emit()
                break

    def remove_link_project(self, project_id: str):
        """Remove a link project"""
        self._state.link_projects = [
            p for p in self._state.link_projects if p.id != project_id
        ]
        if project_id in self._projects:
            del self._projects[project_id]
        self.state_changed.emit()

    def add_user(self, username: str, display_name: str, user_id: str):
        """Add a new user"""
        user_state = UserRowState(
            id=user_id,
            username=username,
            display_name=display_name
        )
        self._state.users.append(user_state)
        self.state_changed.emit()

    def remove_user(self, user_id: str):
        """Remove a user"""
        self._state.users = [u for u in self._state.users if u.id != user_id]
        self.state_changed.emit()

    def open_user_detail(self, username: str):
        """Open user detail view"""
        self._state.user_detail = UserDetailState(
            is_open=True,
            username=username,
            highlights=[],
            is_loading=True
        )
        self._state.current_view = ViewMode.USER_DETAIL
        self.state_changed.emit()

    def close_user_detail(self):
        """Close user detail view"""
        self._state.user_detail = UserDetailState(is_open=False)
        self._state.current_view = ViewMode.MAIN
        self.state_changed.emit()

    def set_user_highlights(self, highlights: list[UserHighlightDTO]):
        """Set highlights for current user detail"""
        card_states = [
            UserHighlightCardState(
                id=h.id,
                name=h.name,
                cover_url=h.cover_url,
                item_count=h.item_count,
                highlight_id=h.highlight_id,
                project_id=h.project_id
            )
            for h in highlights
        ]
        self._state.user_detail.highlights = card_states
        self._state.user_detail.is_loading = False
        self.state_changed.emit()

    def update_user_highlight(self, highlight_id: str, project: HighlightProject):
        """Update a specific user highlight card"""
        for idx, card in enumerate(self._state.user_detail.highlights):
            if card.highlight_id == highlight_id or card.project_id == project.id:
                updated_card = replace(
                    card,
                    status=self._map_download_status(project.download_status),
                    download_progress=project.download_progress,
                    export_progress=project.export_progress,
                    project_id=project.id,
                    folder_path=project.folder_path
                )
                self._state.user_detail.highlights[idx] = updated_card
                self._projects[project.id] = project
                self.state_changed.emit()
                break

    def show_toast(self, message: str, toast_type: str = "info"):
        """Show a toast notification"""
        self.toast_added.emit(message, toast_type)

    def set_auth_screen(self, screen: AuthScreen):
        """Set current authentication screen"""
        self._state.auth.current_screen = screen
        self.auth_changed.emit()
        self.state_changed.emit()

    def set_sign_in_loading(self, is_loading: bool):
        """Set loading state for sign-in screen"""
        self._state.auth.sign_in.is_loading = is_loading
        self.state_changed.emit()

    def set_sign_in_error(self, error: Optional[str]):
        """Set error message for sign-in screen"""
        self._state.auth.sign_in.error_message = error
        self.state_changed.emit()

    def set_2fa_loading(self, is_loading: bool):
        """Set loading state for 2FA screen"""
        self._state.auth.two_factor.is_loading = is_loading
        self.state_changed.emit()

    def set_2fa_error(self, error: Optional[str]):
        """Set error message for 2FA screen"""
        self._state.auth.two_factor.error_message = error
        self.state_changed.emit()

    def store_2fa_credentials(self, username: str, password: str):
        """Store credentials temporarily for 2FA verification"""
        self._state.auth.two_factor.username = username
        self._state.auth.two_factor.password = password
        self.state_changed.emit()

    def set_authenticated(self, username: str):
        """Set user as authenticated and transition to main view"""
        self._state.auth.is_authenticated = True
        self._state.auth.username = username
        self._state.auth.current_screen = AuthScreen.AUTHENTICATED
        self._state.current_user = username
        self._state.current_view = ViewMode.MAIN
        self.auth_changed.emit()
        self.state_changed.emit()

    def logout(self):
        """Logout user and reset to auth screen"""
        self._state.auth = AuthState()  # Reset auth state
        self._state.current_view = ViewMode.AUTH
        self._state.current_user = None
        self._state.status_text = "Offline"
        self.auth_changed.emit()
        self.state_changed.emit()

    def update_status_bar(self, status_text: str, active_downloads: int):
        """Update status bar information"""
        self._state.status_text = status_text
        self._state.active_downloads = active_downloads
        self.state_changed.emit()

    def _dto_to_row_state(self, dto: HighlightProjectDTO) -> HighlightRowState:
        """Convert DTO to row state"""
        return HighlightRowState(
            id=dto.id,
            title=dto.title,
            source=dto.source,
            folder_path=dto.folder_path,
            item_count=dto.item_count,
            status=StatusType[dto.download_status.upper()],
            download_progress=dto.download_progress,
            export_progress=dto.export_progress,
            error_message=dto.error_message,
            has_downloads=dto.has_downloads,
            has_exports=dto.has_exports
        )

    def _project_to_row_state(self, project: HighlightProject) -> HighlightRowState:
        """Convert domain project to row state"""
        status = self._map_download_status(project.download_status)
        if project.export_status.value == "building":
            status = StatusType.BUILDING
        elif project.export_status.value == "exported":
            status = StatusType.EXPORTED

        return HighlightRowState(
            id=project.id,
            title=project.title,
            source=project.source,
            folder_path=project.folder_path,
            item_count=project.item_count,
            status=status,
            download_progress=project.download_progress,
            export_progress=project.export_progress,
            error_message=project.error_message,
            has_downloads=project.has_downloads,
            has_exports=project.has_exports
        )

    def _map_download_status(self, status) -> StatusType:
        """Map domain status to UI status"""
        mapping = {
            "idle": StatusType.IDLE,
            "downloading": StatusType.DOWNLOADING,
            "downloaded": StatusType.DOWNLOADED,
            "error": StatusType.ERROR
        }
        return mapping.get(status.value, StatusType.IDLE)
