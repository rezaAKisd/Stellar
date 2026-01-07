"""App Header - Main application header with logo, settings, and user profile"""
from qtpy.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QMenu, QAction
)
from qtpy.QtCore import Signal, Qt


class UserProfileMenu(QMenu):
    """User profile dropdown menu"""

    profile_clicked = Signal()
    preferences_clicked = Signal()
    sign_out_clicked = Signal()

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.setObjectName("profile-menu")
        self._setup_actions()

    def _setup_actions(self):
        """Setup menu actions"""
        # Profile action
        profile_action = QAction("Profile", self)
        profile_action.triggered.connect(self.profile_clicked.emit)
        self.addAction(profile_action)

        # Preferences action
        prefs_action = QAction("Preferences", self)
        prefs_action.triggered.connect(self.preferences_clicked.emit)
        self.addAction(prefs_action)

        # Separator
        self.addSeparator()

        # Sign out action
        signout_action = QAction("Sign out", self)
        signout_action.setObjectName("menu-danger")
        signout_action.triggered.connect(self.sign_out_clicked.emit)
        self.addAction(signout_action)


class AppHeader(QWidget):
    """Main dashboard header with logo, settings, user profile"""

    settings_clicked = Signal()
    profile_clicked = Signal()
    preferences_clicked = Signal()
    sign_out_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = ""
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI layout"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # Left: Logo + Title
        logo_label = QLabel("\U0001F4E5")  # Download box emoji as placeholder
        logo_label.setObjectName("header-logo")
        logo_label.setStyleSheet("font-size: 24px;")
        layout.addWidget(logo_label)

        title = QLabel("Video Downloader")
        title.setObjectName("header-title")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #1d1d1f;")
        layout.addWidget(title)

        layout.addStretch()

        # Right: Settings icon + User profile dropdown
        self.settings_btn = QPushButton("\u2699")  # Gear emoji
        self.settings_btn.setObjectName("icon-button")
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setStyleSheet(
            "font-size: 20px; background-color: transparent; "
            "border: none; border-radius: 8px;"
        )
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.settings_btn)

        # User profile button
        self.profile_btn = QPushButton("U")
        self.profile_btn.setObjectName("profile-button")
        self.profile_btn.setFixedSize(40, 40)
        self.profile_btn.setStyleSheet(
            "background-color: #007aff; color: white; "
            "border: none; border-radius: 20px; "
            "font-size: 16px; font-weight: 600;"
        )
        self.profile_btn.setCursor(Qt.PointingHandCursor)
        self.profile_btn.clicked.connect(self._show_profile_menu)
        layout.addWidget(self.profile_btn)

    def set_user(self, username: str):
        """Set current user and update profile button"""
        self.username = username
        # Set initials
        if username:
            initial = username[0].upper()
            self.profile_btn.setText(initial)
        else:
            self.profile_btn.setText("U")

    def _show_profile_menu(self):
        """Show profile dropdown menu"""
        menu = UserProfileMenu(self.username, self)
        menu.profile_clicked.connect(self.profile_clicked.emit)
        menu.preferences_clicked.connect(self.preferences_clicked.emit)
        menu.sign_out_clicked.connect(self.sign_out_clicked.emit)

        # Show menu below button
        pos = self.profile_btn.mapToGlobal(
            self.profile_btn.rect().bottomLeft()
        )
        menu.exec_(pos)
