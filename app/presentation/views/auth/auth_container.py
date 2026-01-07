"""Authentication Container - Routes between auth screens"""
import asyncio
from qtpy.QtWidgets import QWidget, QStackedWidget, QVBoxLayout
from .sign_in_screen import SignInScreen
from .two_factor_screen import TwoFactorScreen
from ...viewmodels.auth_vm import AuthViewModel
from ...models_ui import AuthScreen


class AuthContainerView(QWidget):
    """Container for authentication screens with routing"""

    def __init__(self, auth_vm: AuthViewModel, parent=None):
        super().__init__(parent)
        self.auth_vm = auth_vm
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup UI layout with stacked widget for screen routing"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for auth screens
        self.stack = QStackedWidget()

        # Sign In screen
        self.sign_in_screen = SignInScreen()
        self.stack.addWidget(self.sign_in_screen)

        # 2FA screen
        self.two_factor_screen = TwoFactorScreen()
        self.stack.addWidget(self.two_factor_screen)

        layout.addWidget(self.stack)

        # Start with sign in
        self.stack.setCurrentWidget(self.sign_in_screen)

    def _connect_signals(self):
        """Connect signals between screens and ViewModel"""
        # Sign In screen
        self.sign_in_screen.login_clicked.connect(self._on_login)

        # 2FA screen
        self.two_factor_screen.verify_clicked.connect(self._on_verify_2fa)
        self.two_factor_screen.back_clicked.connect(self._on_back_to_signin)

        # Store state changes
        self.auth_vm.store.auth_changed.connect(self._on_auth_changed)
        self.auth_vm.store.state_changed.connect(self._on_state_changed)

    def _on_login(self, username: str, password: str, remember: bool):
        """Handle login button click"""
        # Create async task
        asyncio.create_task(
            self.auth_vm.attempt_login(username, password, remember)
        )

    def _on_verify_2fa(self, code: str, trust: bool):
        """Handle 2FA verification"""
        # Create async task
        asyncio.create_task(
            self.auth_vm.verify_2fa(code, trust)
        )

    def _on_back_to_signin(self):
        """Go back to sign-in screen from 2FA"""
        self.auth_vm.go_back_to_sign_in()

    def _on_auth_changed(self):
        """Handle authentication state changes"""
        screen = self.auth_vm.store.state.auth.current_screen

        if screen == AuthScreen.SIGN_IN:
            self.stack.setCurrentWidget(self.sign_in_screen)
            # Reset 2FA screen when going back
            self.two_factor_screen.reset()

        elif screen == AuthScreen.TWO_FACTOR:
            self.stack.setCurrentWidget(self.two_factor_screen)

    def _on_state_changed(self):
        """Handle general state changes to update UI"""
        auth_state = self.auth_vm.store.state.auth

        # Update sign in screen
        self.sign_in_screen.set_loading(auth_state.sign_in.is_loading)
        if auth_state.sign_in.error_message:
            self.sign_in_screen.show_error(auth_state.sign_in.error_message)
        else:
            self.sign_in_screen.clear_error()

        # Update 2FA screen
        self.two_factor_screen.set_loading(auth_state.two_factor.is_loading)
        if auth_state.two_factor.error_message:
            self.two_factor_screen.show_error(auth_state.two_factor.error_message)
        else:
            self.two_factor_screen.clear_error()
