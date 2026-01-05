"""Login header widget"""
import logging
import sys
from enum import Enum
from qtpy.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton
)
from qtpy.QtCore import Signal, Qt

from .loading_spinner import LoadingSpinner

logger = logging.getLogger(__name__)


class LoginState(Enum):
    """Login UI states"""
    LOGGED_OUT = "logged_out"
    LOGGING_IN = "logging_in"
    LOGGED_IN = "logged_in"
    ERROR = "error"


class DebugButton(QPushButton):
    """Button with mouse event debugging"""

    def __init__(self, text):
        super().__init__(text)

    def mousePressEvent(self, event):
        print(f"\n[BUTTON MOUSE] Mouse press detected on login button!", file=sys.stderr)
        print(f"[BUTTON MOUSE] Button: {event.button()}", file=sys.stderr)
        print(f"[BUTTON MOUSE] Position: {event.pos()}", file=sys.stderr)
        print(f"[BUTTON MOUSE] Is enabled: {self.isEnabled()}", file=sys.stderr)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        print(f"[BUTTON MOUSE] Mouse release detected on login button!", file=sys.stderr)
        super().mouseReleaseEvent(event)


class LoginHeader(QWidget):
    """Header with login form matching wireframe design"""

    login_clicked = Signal(str, str, str)  # username, password, 2fa
    logout_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("login-header")
        self._setup_ui()

        # Debug: Log button state after setup
        import sys
        print(f"\n[HEADER INIT] Login button enabled: {self.login_btn.isEnabled()}", file=sys.stderr)
        print(f"[HEADER INIT] Login button visible: {self.login_btn.isVisible()}", file=sys.stderr)
        logger.info(f"Login button enabled: {self.login_btn.isEnabled()}")
        logger.info(f"Login button visible: {self.login_btn.isVisible()}")

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 10)
        main_layout.setSpacing(10)

        # Top row: Brand + Login form
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)

        # Brand
        brand = QLabel("MyHighlights")
        brand.setObjectName("brand")
        top_layout.addWidget(brand)

        top_layout.addStretch()

        # Username field
        username_label = QLabel("Username")
        username_label.setObjectName("field-label")
        top_layout.addWidget(username_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setFixedWidth(140)
        self.username_input.setObjectName("login-input")
        top_layout.addWidget(self.username_input)

        # Password field
        password_label = QLabel("Password")
        password_label.setObjectName("field-label")
        top_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedWidth(140)
        self.password_input.setObjectName("login-input")
        self.password_input.returnPressed.connect(self._on_login_clicked)
        top_layout.addWidget(self.password_input)

        # 2FA Code field
        twofa_label = QLabel("2FA Code (optional)")
        twofa_label.setObjectName("field-label")
        top_layout.addWidget(twofa_label)

        self.twofa_input = QLineEdit()
        self.twofa_input.setPlaceholderText("000000")
        self.twofa_input.setFixedWidth(100)
        self.twofa_input.setMaxLength(6)
        self.twofa_input.setObjectName("login-input")
        self.twofa_input.returnPressed.connect(self._on_login_clicked)
        top_layout.addWidget(self.twofa_input)

        # Login button
        self.login_btn = QPushButton("Log In")
        self.login_btn.setObjectName("login-btn")
        self.login_btn.clicked.connect(self._on_login_clicked)
        top_layout.addWidget(self.login_btn)

        # Loading spinner (hidden by default)
        self.login_spinner = LoadingSpinner("Logging in...", size=30)
        self.login_spinner.hide()
        top_layout.addWidget(self.login_spinner)

        # Logout button
        self.logout_btn = QPushButton("Log Out")
        self.logout_btn.setObjectName("logout-btn")
        self.logout_btn.clicked.connect(self.logout_clicked.emit)
        self.logout_btn.hide()
        top_layout.addWidget(self.logout_btn)

        # Status indicator
        self.status_label = QLabel("● Logged out")
        self.status_label.setObjectName("status-label")
        top_layout.addWidget(self.status_label)

        main_layout.addLayout(top_layout)

        # Session message
        self.session_message = QLabel("Your session will be saved so you won't need to log in again.")
        self.session_message.setObjectName("session-message")
        self.session_message.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.session_message)

    def _on_login_clicked(self):
        """Handle login button click"""
        import sys
        print("=" * 60, file=sys.stderr)
        print("LOGIN BUTTON CLICKED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        logger.info("=" * 60)
        logger.info("LOGIN BUTTON CLICKED")
        logger.info("=" * 60)

        username = self.username_input.text().strip()
        password = self.password_input.text()
        twofa = self.twofa_input.text().strip()

        print(f"Username: {username}", file=sys.stderr)
        print(f"Password length: {len(password)}", file=sys.stderr)
        print(f"2FA code provided: {bool(twofa)}", file=sys.stderr)

        logger.info(f"Username: {username}")
        logger.info(f"Password length: {len(password)}")
        logger.info(f"2FA code provided: {bool(twofa)}")

        if username and password:
            print("✓ Username and password provided", file=sys.stderr)
            logger.info("✓ Username and password provided")
            # Convert empty 2FA to None
            twofa_code = twofa if twofa else None

            print("Emitting login_clicked signal...", file=sys.stderr)
            logger.info("Emitting login_clicked signal...")

            try:
                self.login_clicked.emit(username, password, twofa_code or "")
                print("Signal emitted successfully", file=sys.stderr)
                logger.info("Signal emitted successfully")
            except Exception as e:
                print(f"ERROR emitting signal: {e}", file=sys.stderr)
                logger.error(f"ERROR emitting signal: {e}", exc_info=True)
        else:
            print("✗ Missing username or password", file=sys.stderr)
            logger.warning("✗ Missing username or password")
            if not username:
                print("  - Username is empty", file=sys.stderr)
                logger.warning("  - Username is empty")
            if not password:
                print("  - Password is empty", file=sys.stderr)
                logger.warning("  - Password is empty")

    def set_state(self, state: LoginState, username: str = "", error: str = ""):
        """Update UI based on login state"""
        # Hide all state-specific widgets first
        self.login_btn.hide()
        self.login_spinner.hide()
        self.logout_btn.hide()

        if state == LoginState.LOGGED_OUT:
            # Show login form
            self.status_label.setText("● Logged out")
            self.status_label.setProperty("logged_in", False)
            self.login_btn.show()
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)
            self.twofa_input.setEnabled(True)
            self.password_input.clear()
            self.twofa_input.clear()

        elif state == LoginState.LOGGING_IN:
            # Show spinner, disable inputs
            self.status_label.setText("● Logging in...")
            self.status_label.setProperty("logged_in", False)
            self.login_spinner.show()
            self.username_input.setEnabled(False)
            self.password_input.setEnabled(False)
            self.twofa_input.setEnabled(False)

        elif state == LoginState.LOGGED_IN:
            # Show logged in state
            self.status_label.setText(f"● Logged in as @{username}" if username else "● Logged in")
            self.status_label.setProperty("logged_in", True)
            self.logout_btn.show()
            self.username_input.setEnabled(False)
            self.password_input.setEnabled(False)
            self.twofa_input.setEnabled(False)

        elif state == LoginState.ERROR:
            # Show error, enable retry
            self.status_label.setText(f"● {error}")
            self.status_label.setProperty("logged_in", False)
            self.login_btn.show()
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)
            self.twofa_input.setEnabled(True)
            # Keep credentials, only clear 2FA
            self.twofa_input.clear()

        # Refresh stylesheet
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    # Backward compatibility methods
    def set_logged_in(self, logged_in: bool, username: str = ""):
        """Update UI for login state (backward compatible)"""
        if logged_in:
            self.set_state(LoginState.LOGGED_IN, username)
        else:
            self.set_state(LoginState.LOGGED_OUT)

    def set_error(self, error_message: str):
        """Show error message (backward compatible)"""
        self.set_state(LoginState.ERROR, error=error_message)
