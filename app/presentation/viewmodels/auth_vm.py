"""Authentication ViewModel - Coordinates authentication flow"""
import logging
from qtpy.QtCore import QObject, Signal

from ..store import AppStore
from ..models_ui import AuthScreen
from ...application.auth_use_cases import (
    LoginUseCase,
    Verify2FAUseCase,
    LogoutUseCase,
    RestoreSessionUseCase
)
from ...infrastructure.container import DependencyContainer

logger = logging.getLogger(__name__)


class AuthViewModel(QObject):
    """ViewModel for authentication flow"""

    # Signals
    login_success = Signal(str)  # username
    needs_2fa = Signal(str, str)  # username, password
    login_error = Signal(str)  # error message

    def __init__(self, store: AppStore, container: DependencyContainer):
        """
        Initialize AuthViewModel.

        Args:
            store: Centralized application store
            container: Dependency injection container
        """
        super().__init__()
        self.store = store
        self.container = container

        # Initialize use cases
        self.login_uc = LoginUseCase(
            container.instagram_gateway,
            container.file_storage
        )
        self.verify_2fa_uc = Verify2FAUseCase(
            container.instagram_gateway,
            container.file_storage
        )
        self.logout_uc = LogoutUseCase(
            container.instagram_gateway,
            container.file_storage
        )
        self.restore_session_uc = RestoreSessionUseCase(
            container.instagram_gateway,
            container.file_storage
        )

    async def attempt_login(self, username: str, password: str, remember: bool):
        """
        Attempt to login with username and password.

        Args:
            username: Instagram username
            password: Instagram password
            remember: Whether to remember the device
        """
        logger.info(f"Attempting login for user: {username}")

        # Clear any previous errors
        self.store.set_sign_in_error(None)

        # Set loading state
        self.store.set_sign_in_loading(True)

        try:
            # Execute login use case
            result = await self.login_uc.execute(username, password, remember)

            # Clear loading state
            self.store.set_sign_in_loading(False)

            if result.success:
                logger.info(f"Login successful for user: {username}")
                self.store.set_authenticated(result.username)
                self.login_success.emit(result.username)

            elif result.needs_2fa:
                logger.info(f"2FA required for user: {username}")
                # Store credentials for 2FA verification
                self.store.store_2fa_credentials(username, password)
                # Transition to 2FA screen
                self.store.set_auth_screen(AuthScreen.TWO_FACTOR)
                self.needs_2fa.emit(username, password)

            else:
                logger.warning(f"Login failed: {result.error_message}")
                self.store.set_sign_in_error(result.error_message)
                self.login_error.emit(result.error_message)

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            self.store.set_sign_in_loading(False)
            error_msg = f"Login error: {str(e)}"
            self.store.set_sign_in_error(error_msg)
            self.login_error.emit(error_msg)

    async def verify_2fa(self, code: str, trust: bool):
        """
        Verify two-factor authentication code.

        Args:
            code: 6-digit verification code
            trust: Whether to trust this device
        """
        logger.info("Attempting 2FA verification")

        # Get stored credentials from state
        username = self.store.state.auth.two_factor.username
        password = self.store.state.auth.two_factor.password

        if not username or not password:
            logger.error("No stored credentials for 2FA verification")
            self.store.set_2fa_error("Session expired. Please sign in again.")
            return

        # Clear any previous errors
        self.store.set_2fa_error(None)

        # Set loading state
        self.store.set_2fa_loading(True)

        try:
            # Execute 2FA verification use case
            result = await self.verify_2fa_uc.execute(
                username, password, code, trust
            )

            # Clear loading state
            self.store.set_2fa_loading(False)

            if result.success:
                logger.info("2FA verification successful")
                self.store.set_authenticated(result.username)
                self.login_success.emit(result.username)

            else:
                logger.warning(f"2FA verification failed: {result.error_message}")
                self.store.set_2fa_error(result.error_message)

        except Exception as e:
            logger.error(f"2FA verification error: {str(e)}")
            self.store.set_2fa_loading(False)
            error_msg = f"Verification error: {str(e)}"
            self.store.set_2fa_error(error_msg)

    def go_back_to_sign_in(self):
        """Go back to sign-in screen from 2FA"""
        logger.info("Returning to sign-in screen")
        self.store.set_auth_screen(AuthScreen.SIGN_IN)
        self.store.set_2fa_error(None)

    async def restore_session(self):
        """
        Attempt to restore a saved session on app start.
        """
        logger.info("Attempting to restore session")

        try:
            result = await self.restore_session_uc.execute()

            if result.success:
                logger.info(f"Session restored for user: {result.username}")
                self.store.set_authenticated(result.username)
            else:
                logger.info("No saved session or session invalid")
                # Stay on auth screen

        except Exception as e:
            logger.error(f"Session restoration error: {str(e)}")
            # Stay on auth screen

    async def logout(self):
        """Logout the current user"""
        logger.info("Logging out")

        try:
            await self.logout_uc.execute()
            self.store.logout()
            logger.info("Logout successful")

        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            # Force logout in store even if service logout failed
            self.store.logout()
