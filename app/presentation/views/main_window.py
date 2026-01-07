"""Main Application Window - Restructured with Authentication"""
import asyncio
from pathlib import Path
from qtpy.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QStackedWidget,
    QLabel
)
from qtpy.QtCore import Qt, QTimer

from .auth.auth_container import AuthContainerView
from .widgets.app_header import AppHeader
from .widgets.status_bar import StatusBar
from .tabs.tab_by_link import TabByLink
from .tabs.tab_by_username import TabByUsername
from .pages.user_detail_page import UserDetailPage
from ..viewmodels.auth_vm import AuthViewModel
from ..viewmodels.main_vm import MainViewModel
from ..viewmodels.link_tab_vm import LinkTabViewModel
from ..viewmodels.username_tab_vm import UsernameTabViewModel
from ..viewmodels.user_detail_vm import UserDetailViewModel
from ..store import AppStore
from ..models_ui import ViewMode
from ...infrastructure.container import DependencyContainer


class ToastWidget(QLabel):
    """Toast notification widget"""

    def __init__(self, message: str, toast_type: str, parent=None):
        super().__init__(message, parent)
        self.setObjectName("toast")
        self.setProperty("type", toast_type)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(300)
        self.setMaximumWidth(500)
        self.setWordWrap(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Auto-hide after 3 seconds
        QTimer.singleShot(3000, self.close)


class MainWindow(QMainWindow):
    """Main application window with authentication routing"""

    def __init__(self):
        super().__init__()

        # Initialize dependency container
        session_dir = Path.home() / ".stellar" / "session"
        data_dir = Path.home() / ".stellar" / "data"
        self.container = DependencyContainer(session_dir, data_dir)

        # Initialize store
        self.store = AppStore()

        # Setup ViewModels
        self._setup_viewmodels()

        # Setup UI
        self._setup_ui()

        # Connect signals
        self._connect_signals()

        # Apply stylesheet
        self._apply_stylesheet()

    def showEvent(self, event):
        """Called when window is shown - schedule session restoration"""
        super().showEvent(event)
        # Schedule session restoration after event loop is running
        from qtpy.QtCore import QTimer
        QTimer.singleShot(100, lambda: asyncio.create_task(self.auth_vm.restore_session()))

    def _setup_viewmodels(self):
        """Initialize ViewModels with dependency container"""
        self.auth_vm = AuthViewModel(self.store, self.container)
        self.main_vm = MainViewModel(self.store, self.container)
        self.link_tab_vm = LinkTabViewModel(self.store, self.container)
        self.username_tab_vm = UsernameTabViewModel(self.store, self.container)
        self.user_detail_vm = UserDetailViewModel(self.store, self.container)

    def _setup_ui(self):
        """Setup UI with authentication routing"""
        self.setWindowTitle("Video Downloader")
        self.setMinimumSize(1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Root stacked widget: Auth view <-> Main app view
        self.root_stack = QStackedWidget()

        # Auth view
        self.auth_view = AuthContainerView(self.auth_vm)
        self.root_stack.addWidget(self.auth_view)

        # Main app view
        self.main_app_view = self._create_main_app_view()
        self.root_stack.addWidget(self.main_app_view)

        layout.addWidget(self.root_stack)

        # Start with auth view
        self.root_stack.setCurrentWidget(self.auth_view)

    def _create_main_app_view(self):
        """Create the main authenticated app view"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App header
        self.app_header = AppHeader()
        layout.addWidget(self.app_header)

        # Content stack: Tabs <-> User detail
        self.content_stack = QStackedWidget()

        # Tabs page
        self.tabs_widget = QTabWidget()
        self.tabs_widget.setObjectName("main-tabs")

        # Tab 1: Direct Link / ID
        self.link_tab = TabByLink(self.link_tab_vm)
        self.tabs_widget.addTab(self.link_tab, "Direct Link / ID")

        # Tab 2: Username / Playlists
        self.username_tab = TabByUsername(self.username_tab_vm)
        self.tabs_widget.addTab(self.username_tab, "Username / Playlists")

        self.content_stack.addWidget(self.tabs_widget)

        # User detail page
        self.user_detail_page = UserDetailPage(self.user_detail_vm)
        self.content_stack.addWidget(self.user_detail_page)

        layout.addWidget(self.content_stack)

        # Status bar
        self.status_bar = StatusBar()
        layout.addWidget(self.status_bar)

        return container

    def _connect_signals(self):
        """Connect all signals"""
        # Auth state changes
        self.store.auth_changed.connect(self._on_auth_changed)

        # Store state changes
        self.store.state_changed.connect(self._on_state_changed)

        # App header actions
        self.app_header.settings_clicked.connect(self._on_settings)
        self.app_header.profile_clicked.connect(self._on_profile)
        self.app_header.preferences_clicked.connect(self._on_preferences)
        self.app_header.sign_out_clicked.connect(self._on_sign_out)

        # Toast notifications
        self.store.toast_added.connect(self._show_toast)

        # User detail page back button
        self.user_detail_page.back_clicked.connect(self.user_detail_vm.go_back)

    def _on_auth_changed(self):
        """Handle authentication changes - switch between auth and main views"""
        if self.store.state.auth.is_authenticated:
            # Switch to main app
            self.root_stack.setCurrentWidget(self.main_app_view)

            # Update header with username
            username = self.store.state.current_user
            if username:
                self.app_header.set_user(username)

            # Update status bar
            self._update_status_bar()

        else:
            # Switch to auth
            self.root_stack.setCurrentWidget(self.auth_view)

    def _on_state_changed(self):
        """Handle view mode changes within main app"""
        if not self.store.state.auth.is_authenticated:
            return  # Don't handle if not authenticated

        view_mode = self.store.state.current_view

        if view_mode == ViewMode.MAIN:
            self.content_stack.setCurrentWidget(self.tabs_widget)

        elif view_mode == ViewMode.USER_DETAIL:
            self.content_stack.setCurrentWidget(self.user_detail_page)
            username = self.store.state.user_detail.username
            if username:
                self.user_detail_page.show_user(username)

        # Update status bar
        self._update_status_bar()

    def _update_status_bar(self):
        """Update status bar with current state"""
        state = self.store.state

        # Update connection status
        is_auth = self.container.instagram_gateway.is_authenticated()
        status = "Online" if is_auth else "Offline"
        self.status_bar.update_status(is_auth, status)

        # Update active downloads count
        active = len([p for p in state.link_projects if p.is_busy])
        self.status_bar.update_downloads(active)

        # Set version
        self.status_bar.set_version(state.app_version)

    def _on_settings(self):
        """Handle settings button click"""
        # TODO: Implement settings dialog
        self.store.show_toast("Settings coming soon", "info")

    def _on_profile(self):
        """Handle profile menu click"""
        # TODO: Implement profile page
        self.store.show_toast("Profile coming soon", "info")

    def _on_preferences(self):
        """Handle preferences menu click"""
        # TODO: Implement preferences dialog
        self.store.show_toast("Preferences coming soon", "info")

    def _on_sign_out(self):
        """Handle sign out"""
        asyncio.create_task(self.auth_vm.logout())

    def _show_toast(self, message: str, toast_type: str):
        """Show toast notification"""
        toast = ToastWidget(message, toast_type, self)

        # Position at bottom center
        toast_width = 400
        toast_height = 60
        x = (self.width() - toast_width) // 2
        y = self.height() - 100

        toast.setGeometry(x, y, toast_width, toast_height)
        toast.show()

    def _apply_stylesheet(self):
        """Load and apply QSS stylesheet"""
        try:
            # Try multiple possible locations
            stylesheet_paths = [
                Path("assets/theme.qss"),
                Path("app/assets/theme.qss"),
                Path(__file__).parent.parent.parent.parent / "assets" / "theme.qss"
            ]

            for path in stylesheet_paths:
                if path.exists():
                    with open(path, "r") as f:
                        stylesheet = f.read()
                        self.setStyleSheet(stylesheet)
                    print(f"Loaded stylesheet from: {path}")
                    return

            print("Warning: theme.qss not found, using default styling")

        except Exception as e:
            print(f"Error loading stylesheet: {e}")
