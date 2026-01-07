"""Authentication API routes"""
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas import (
    LoginRequest,
    LoginResponse,
    Verify2FARequest,
    TokenResponse,
    UserResponse,
    MessageResponse
)
from ..dependencies import get_instagram_gateway
from ...core.security import create_access_token, get_current_user
from ...core.config import settings
from ...app.application.auth_use_cases import (
    LoginUseCase,
    Verify2FAUseCase,
    LogoutUseCase,
    RestoreSessionUseCase,
    CheckAuthStatusUseCase
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    instagram_gateway = Depends(get_instagram_gateway)
):
    """
    Login with Instagram credentials.

    Returns JWT token if successful, or needs_2fa flag if 2FA is required.
    """
    try:
        logger.info(f"Login attempt for user: {request.username}")

        # Execute login use case
        login_uc = LoginUseCase(instagram_gateway)
        result = await login_uc.execute(request.username, request.password, False)

        if result.success:
            # Create JWT token
            access_token = create_access_token(
                data={"sub": result.username},
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )

            logger.info(f"Login successful for user: {result.username}")
            return LoginResponse(
                access_token=access_token,
                token_type="bearer",
                username=result.username,
                needs_2fa=False
            )

        elif result.needs_2fa:
            logger.info(f"2FA required for user: {request.username}")
            return LoginResponse(
                access_token="",
                token_type="bearer",
                username=request.username,
                needs_2fa=True
            )

        else:
            logger.warning(f"Login failed for user: {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.error_message or "Invalid credentials"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/verify-2fa", response_model=TokenResponse)
async def verify_2fa(
    request: Verify2FARequest,
    instagram_gateway = Depends(get_instagram_gateway)
):
    """
    Verify 2FA code and complete authentication.

    Returns JWT token if verification is successful.
    """
    try:
        logger.info(f"2FA verification attempt for user: {request.username}")

        # Execute 2FA verification use case
        verify_uc = Verify2FAUseCase(instagram_gateway)
        result = await verify_uc.execute(
            request.username,
            request.password,
            request.code,
            request.trust_device
        )

        if result.success:
            # Create JWT token
            access_token = create_access_token(
                data={"sub": result.username},
                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )

            logger.info(f"2FA verification successful for user: {result.username}")
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                username=result.username
            )

        else:
            logger.warning(f"2FA verification failed for user: {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.error_message or "Invalid verification code"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA verification error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"2FA verification failed: {str(e)}"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: str = Depends(get_current_user),
    instagram_gateway = Depends(get_instagram_gateway)
):
    """
    Logout and clear session.

    Requires authentication.
    """
    try:
        logger.info(f"Logout request for user: {current_user}")

        # Execute logout use case
        logout_uc = LogoutUseCase(instagram_gateway)
        await logout_uc.execute()

        logger.info(f"Logout successful for user: {current_user}")
        return MessageResponse(message="Logged out successfully")

    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: str = Depends(get_current_user),
    instagram_gateway = Depends(get_instagram_gateway)
):
    """
    Get current authenticated user information.

    Requires authentication.
    """
    try:
        # Check if user is still authenticated with Instagram
        check_uc = CheckAuthStatusUseCase(instagram_gateway)
        result = check_uc.execute()

        return UserResponse(
            username=current_user,
            is_authenticated=result.is_authenticated
        )

    except Exception as e:
        logger.error(f"Get user info error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )


@router.post("/restore-session", response_model=UserResponse)
async def restore_session(
    instagram_gateway = Depends(get_instagram_gateway)
):
    """
    Attempt to restore a saved Instagram session.

    Returns user info if session is valid, otherwise returns unauthenticated status.
    """
    try:
        logger.info("Session restoration attempt")

        # Execute restore session use case
        restore_uc = RestoreSessionUseCase(instagram_gateway)
        result = await restore_uc.execute()

        if result.success and result.username:
            logger.info(f"Session restored for user: {result.username}")
            return UserResponse(
                username=result.username,
                is_authenticated=True
            )
        else:
            logger.info("No valid session to restore")
            return UserResponse(
                username="",
                is_authenticated=False
            )

    except Exception as e:
        logger.error(f"Session restoration error: {str(e)}", exc_info=True)
        return UserResponse(
            username="",
            is_authenticated=False
        )
