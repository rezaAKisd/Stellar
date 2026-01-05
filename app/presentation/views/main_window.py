"""Main Application Window"""
from qtpy.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QStackedWidget,
    QLabel, QMessageBox
)
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QFont

from .widgets.header_bar import HeaderBar
from .tabs.tab_by_link import TabByLink
from .tabs.tab_by_username import TabByUsername
from .pages.user_detail_page import UserDetailPage
from ..viewmodels.main_vm import MainViewModel
from ..viewmodels.link_tab_vm import LinkTabViewModel
from ..viewmodels.username_tab_vm import UsernameTabViewModel
from ..viewmodels.user_detail_vm import UserDetailViewModel
from ..store import AppStore
from ..models_ui import ViewMode


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
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.store = AppStore()
        self._setup_viewmodels()
        self._setup_ui()
        self._connect_signals()
        self._apply_stylesheet()

    def _setup_viewmodels(self):
        """Initialize ViewModels"""
        self.main_vm = MainViewModel(self.store)
        self.link_tab_vm = LinkTabViewModel(self.store)
        self.username_tab_vm = UsernameTabViewModel(self.store)
        self.user_detail_vm = UserDetailViewModel(self.store)

    def _setup_ui(self):
        """Setup UI components"""
        self.setWindowTitle("Highlight Studio")
        self.setMinimumSize(1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        self.header = HeaderBar()
        layout.addWidget(self.header)

        # Stacked widget for main view / user detail view
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        # Main tabs page
        self.tabs_widget = QTabWidget()
        self.tabs_widget.setObjectName("main-tabs")

        # Tab 1: By Link
        self.link_tab = TabByLink(self.link_tab_vm)
        self.tabs_widget.addTab(self.link_tab, "By Highlight Link")

        # Tab 2: By Username
        self.username_tab = TabByUsername(self.username_tab_vm)
        self.tabs_widget.addTab(self.username_tab, "By Username")

        self.stacked_widget.addWidget(self.tabs_widget)

        # User detail page
        self.user_detail_page = UserDetailPage(self.user_detail_vm)
        self.stacked_widget.addWidget(self.user_detail_page)

    def _connect_signals(self):
        """Connect signals"""
        # Header actions
        self.header.connect_clicked.connect(self._on_connect)
        self.header.use_existing_clicked.connect(self._on_use_existing)
        self.header.disconnect_clicked.connect(self.main_vm.disconnect_session)

        # Main ViewModel
        self.main_vm.connection_changed.connect(self.header.update_connection_status)

        # Store state changes
        self.store.state_changed.connect(self._on_store_state_changed)

        # Toast notifications
        self.store.toast_added.connect(self._show_toast)

        # User detail page back button
        self.user_detail_page.back_clicked.connect(self.user_detail_vm.go_back)

        # Username tab open user
        self.username_tab_vm.users_changed.connect(self._check_auto_open_user)

    def _on_connect(self):
        """Handle connect action"""
        session_token = self.header.get_last_session_token()
        if session_token:
            self.main_vm.connect_session(session_token)

    def _on_use_existing(self):
        """Handle use existing session"""
        session_token = self.header.get_last_session_token()
        if session_token:
            self.main_vm.connect_session(session_token)

    def _on_store_state_changed(self):
        """Handle store state changes - update view"""
        view_mode = self.store.state.current_view

        if view_mode == ViewMode.MAIN:
            self.stacked_widget.setCurrentWidget(self.tabs_widget)
        elif view_mode == ViewMode.USER_DETAIL:
            self.stacked_widget.setCurrentWidget(self.user_detail_page)
            username = self.store.state.user_detail.username
            if username:
                self.user_detail_page.show_user(username)

    def _check_auto_open_user(self, users):
        """Auto-open user detail when a new user is added"""
        # This is called when users list changes
        # We can implement auto-navigation here if desired
        pass

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
            with open("assets/theme.qss", "r") as f:
                stylesheet = f.read()
                self.setStyleSheet(stylesheet)
        except FileNotFoundError:
            # Fallback if theme file doesn't exist
            print("Warning: theme.qss not found, using default styling")
