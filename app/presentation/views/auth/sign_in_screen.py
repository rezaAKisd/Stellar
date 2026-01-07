"""Sign In Screen - Authentication UI"""
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox
)
from qtpy.QtCore import Qt, Signal


class PasswordInput(QWidget):
    """Password input with show/hide toggle"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Password input field
        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.Password)
        self.input.setPlaceholderText("Enter your password")
        self.input.setObjectName("auth-input")
        layout.addWidget(self.input)

        # Show/hide toggle button (eye icon)
        self.toggle_btn = QPushButton("\U0001F441")  # Eye emoji
        self.toggle_btn.setObjectName("password-toggle")
        self.toggle_btn.setFixedSize(40, 40)
        self.toggle_btn.clicked.connect(self._toggle_visibility)
        layout.addWidget(self.toggle_btn)

        self._visible = False

    def _toggle_visibility(self):
        """Toggle password visibility"""
        self._visible = not self._visible
        if self._visible:
            self.input.setEchoMode(QLineEdit.Normal)
            self.toggle_btn.setText("\U0001F576")  # Sunglasses emoji (hide)
        else:
            self.input.setEchoMode(QLineEdit.Password)
            self.toggle_btn.setText("\U0001F441")  # Eye emoji (show)

    def text(self) -> str:
        """Get password text"""
        return self.input.text()

    def clear(self):
        """Clear password input"""
        self.input.clear()

    def setFocus(self):
        """Set focus to input field"""
        self.input.setFocus()


class SignInScreen(QWidget):
    """Sign In screen matching mockup design"""

    # Signals
    login_clicked = Signal(str, str, bool)  # username, password, remember

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # Main layout - center everything
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # Card container
        card = QWidget()
        card.setObjectName("auth-card")
        card.setFixedWidth(450)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(20)
        card_layout.setContentsMargins(40, 40, 40, 40)

        # Logo / App icon
        logo = QLabel()
        logo.setObjectName("auth-logo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setText("\U0001F4E5")  # Download box emoji as placeholder
        logo.setStyleSheet("font-size: 64px;")
        card_layout.addWidget(logo)

        # Title
        title = QLabel("Sign in")
        title.setObjectName("auth-title")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: 600; color: #1d1d1f;")
        card_layout.addWidget(title)

        card_layout.addSpacing(10)

        # Username label
        username_label = QLabel("Username")
        username_label.setStyleSheet("font-size: 14px; color: #3a3a3c; font-weight: 500;")
        card_layout.addWidget(username_label)

        # Username input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setObjectName("auth-input")
        self.username_input.setMinimumHeight(44)
        card_layout.addWidget(self.username_input)

        # Password label
        password_label = QLabel("Password")
        password_label.setStyleSheet("font-size: 14px; color: #3a3a3c; font-weight: 500;")
        card_layout.addWidget(password_label)

        # Password input with toggle
        self.password_input = PasswordInput()
        self.password_input.input.setMinimumHeight(44)
        card_layout.addWidget(self.password_input)

        # Remember me checkbox
        self.remember_checkbox = QCheckBox("Remember me on this device")
        self.remember_checkbox.setObjectName("auth-checkbox")
        card_layout.addWidget(self.remember_checkbox)

        card_layout.addSpacing(10)

        # Continue button
        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setObjectName("primary-button")
        self.continue_btn.setMinimumHeight(44)
        self.continue_btn.clicked.connect(self._on_continue)
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        card_layout.addWidget(self.continue_btn)

        # Error message
        self.error_label = QLabel()
        self.error_label.setObjectName("error-message")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        main_layout.addWidget(card)

        # Connect Enter key to login
        self.username_input.returnPressed.connect(self._on_continue)
        self.password_input.input.returnPressed.connect(self._on_continue)

    def _on_continue(self):
        """Handle continue button click"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        remember = self.remember_checkbox.isChecked()

        # Validation
        if not username:
            self.show_error("Please enter your username")
            self.username_input.setFocus()
            return

        if not password:
            self.show_error("Please enter your password")
            self.password_input.setFocus()
            return

        # Clear error and emit signal
        self.clear_error()
        self.login_clicked.emit(username, password, remember)

    def show_error(self, message: str):
        """Show error message"""
        self.error_label.setText(message)
        self.error_label.show()

    def clear_error(self):
        """Clear error message"""
        self.error_label.hide()
        self.error_label.clear()

    def set_loading(self, loading: bool):
        """Set loading state"""
        self.continue_btn.setEnabled(not loading)
        if loading:
            self.continue_btn.setText("Signing in...")
        else:
            self.continue_btn.setText("Continue")

    def clear_form(self):
        """Clear all form fields"""
        self.username_input.clear()
        self.password_input.clear()
        self.remember_checkbox.setChecked(False)
        self.clear_error()
