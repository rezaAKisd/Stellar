"""Authentication Use Cases - Business logic for authentication"""
import logging
from typing import Optional

from ..domain.interfaces import IInstagramGateway, IFileStorage
from .dtos import LoginResultDTO, AuthStatusDTO

logger = logging.getLogger(__name__)


class LoginUseCase:
    """Use case for logging in with username and password"""

    def __init__(self, instagram_gateway: IInstagramGateway, file_storage: IFileStorage):
        self.instagram = instagram_gateway
        self.storage = file_storage

    async def execute(
        self,
        username: str,
        password: str,
        remember_device: bool = False
    ) -> LoginResultDTO:
        """
        Execute login use case.

        Args:
            username: Instagram username
            password: Instagram password
            remember_device: Whether to remember the device

        Returns:
            LoginResultDTO with login result
        """
        try:
            logger.info(f"Attempting login for user: {username}")

            # Attempt login
            success, error_message, needs_2fa = await self.instagram.login(
                username, password, None
            )

            if success:
                logger.info(f"Login successful for user: {username}")
                return LoginResultDTO(
                    success=True,
                    needs_2fa=False,
                    username=username
                )
            elif needs_2fa:
                logger.info(f"2FA required for user: {username}")
                return LoginResultDTO(
                    success=False,
                    needs_2fa=True,
                    error_message="Two-factor authentication required",
                    username=username
                )
            else:
                logger.warning(f"Login failed for user {username}: {error_message}")
                return LoginResultDTO(
                    success=False,
                    needs_2fa=False,
                    error_message=error_message or "Login failed"
                )

        except Exception as e:
            logger.error(f"Login error for user {username}: {str(e)}")
            return LoginResultDTO(
                success=False,
                needs_2fa=False,
                error_message=f"Login error: {str(e)}"
            )


class Verify2FAUseCase:
    """Use case for verifying two-factor authentication code"""

    def __init__(self, instagram_gateway: IInstagramGateway, file_storage: IFileStorage):
        self.instagram = instagram_gateway
        self.storage = file_storage

    async def execute(
        self,
        username: str,
        password: str,
        verification_code: str,
        trust_device: bool = False
    ) -> LoginResultDTO:
        """
        Execute 2FA verification use case.

        Args:
            username: Instagram username
            password: Instagram password
            verification_code: 6-digit 2FA code
            trust_device: Whether to trust this device

        Returns:
            LoginResultDTO with verification result
        """
        try:
            logger.info(f"Attempting 2FA verification for user: {username}")

            # Attempt login with verification code
            success, error_message, needs_2fa = await self.instagram.login(
                username, password, verification_code
            )

            if success:
                logger.info(f"2FA verification successful for user: {username}")
                return LoginResultDTO(
                    success=True,
                    needs_2fa=False,
                    username=username
                )
            else:
                logger.warning(f"2FA verification failed for user {username}: {error_message}")
                return LoginResultDTO(
                    success=False,
                    needs_2fa=needs_2fa,
                    error_message=error_message or "Invalid verification code"
                )

        except Exception as e:
            logger.error(f"2FA verification error for user {username}: {str(e)}")
            return LoginResultDTO(
                success=False,
                needs_2fa=False,
                error_message=f"Verification error: {str(e)}"
            )


class LogoutUseCase:
    """Use case for logging out"""

    def __init__(self, instagram_gateway: IInstagramGateway, file_storage: IFileStorage):
        self.instagram = instagram_gateway
        self.storage = file_storage

    async def execute(self) -> bool:
        """
        Execute logout use case.

        Returns:
            True if logout was successful
        """
        try:
            logger.info("Logging out")
            await self.instagram.logout()
            logger.info("Logout successful")
            return True
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return False


class RestoreSessionUseCase:
    """Use case for restoring a saved session"""

    def __init__(self, instagram_gateway: IInstagramGateway, file_storage: IFileStorage):
        self.instagram = instagram_gateway
        self.storage = file_storage

    async def execute(self) -> LoginResultDTO:
        """
        Execute session restoration use case.

        Returns:
            LoginResultDTO with restoration result
        """
        try:
            logger.info("Attempting to restore session")

            # Attempt to restore session
            success, error_message = await self.instagram.restore_session()

            if success:
                logger.info("Session restored successfully")
                # Get username from session if available
                # For now, we'll use a placeholder
                return LoginResultDTO(
                    success=True,
                    needs_2fa=False,
                    username="restored_user"  # TODO: Get actual username from session
                )
            else:
                logger.info(f"Session restoration failed: {error_message}")
                return LoginResultDTO(
                    success=False,
                    needs_2fa=False,
                    error_message=error_message or "No saved session found"
                )

        except Exception as e:
            logger.error(f"Session restoration error: {str(e)}")
            return LoginResultDTO(
                success=False,
                needs_2fa=False,
                error_message=f"Session restoration error: {str(e)}"
            )


class CheckAuthStatusUseCase:
    """Use case for checking current authentication status"""

    def __init__(self, instagram_gateway: IInstagramGateway):
        self.instagram = instagram_gateway

    def execute(self) -> AuthStatusDTO:
        """
        Execute authentication status check.

        Returns:
            AuthStatusDTO with current auth status
        """
        try:
            is_auth = self.instagram.is_authenticated()
            return AuthStatusDTO(
                is_authenticated=is_auth,
                username=None,  # TODO: Get username if authenticated
                session_valid=is_auth
            )
        except Exception as e:
            logger.error(f"Auth status check error: {str(e)}")
            return AuthStatusDTO(
                is_authenticated=False,
                username=None,
                session_valid=False
            )
