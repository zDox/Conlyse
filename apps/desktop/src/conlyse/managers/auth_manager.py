from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from conlyse.api import ApiClient, ApiError, AuthError, NetworkError, PermissionError
from conlyse.logger import get_logger

if TYPE_CHECKING:
    from conlyse.app import App


logger = get_logger()


@dataclass
class AuthTokens:
    access_token: str
    refresh_token: str


@dataclass
class UserProfile:
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    is_email_verified: bool
    totp_enabled: bool
    email_2fa_enabled: bool


@dataclass
class LoginResult:
    success: bool
    two_fa_required: bool = False
    two_fa_pending_token: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class TwoFAVerifyResult:
    success: bool
    error_message: Optional[str] = None


class AuthManager:
    """Manages authentication and user session state for the desktop client."""

    def __init__(self, app: App):
        self.app = app
        self._api: ApiClient = app.api_client

        self._tokens: Optional[AuthTokens] = None
        self._user: Optional[UserProfile] = None
        self._pending_two_fa_token: Optional[str] = None
        self._subscription_tier: Optional[str] = None
        self._is_pro: bool = False

    # --------------------------------------------------------------------- State

    @property
    def is_authenticated(self) -> bool:
        return self._tokens is not None and self._user is not None

    @property
    def current_user(self) -> Optional[UserProfile]:
        return self._user

    @property
    def pending_two_fa(self) -> bool:
        return self._pending_two_fa_token is not None

    @property
    def subscription_tier(self) -> Optional[str]:
        return self._subscription_tier

    @property
    def is_pro(self) -> bool:
        return self._is_pro

    # ----------------------------------------------------------------- Internals

    def _set_tokens(self, access_token: str, refresh_token: str) -> None:
        self._tokens = AuthTokens(access_token=access_token, refresh_token=refresh_token)
        self._api.set_access_token(access_token)
        logger.info("Authentication tokens updated.")

    def _clear_state(self) -> None:
        self._tokens = None
        self._user = None
        self._pending_two_fa_token = None
        self._api.set_access_token(None)
        logger.info("Authentication state cleared.")

    def _fetch_user_profile(self) -> None:
        """Fetch the current user's profile from the API and cache it."""
        try:
            data: Dict[str, Any] = self._api.get("/auth/me", requires_auth=True)
        except (ApiError, NetworkError, AuthError) as exc:
            logger.error(f"Failed to fetch user profile: {exc}")
            # If auth fails here, treat it as logged out.
            if isinstance(exc, AuthError):
                self._clear_state()
            raise

        self._user = UserProfile(
            id=data["id"],
            email=data["email"],
            username=data["username"],
            role=str(data["role"]),
            is_active=bool(data["is_active"]),
            is_email_verified=bool(data["is_email_verified"]),
            totp_enabled=bool(data["totp_enabled"]),
            email_2fa_enabled=bool(data["email_2fa_enabled"]),
        )
        logger.info("User profile loaded from API.")

    def refresh_subscription_status(self) -> None:
        """Fetch and cache the user's subscription status."""
        if not self._tokens:
            self._subscription_tier = None
            self._is_pro = False
            return

        try:
            data: Dict[str, Any] = self._api.get("/subscription/status", requires_auth=True)
        except (NetworkError, ApiError, AuthError, PermissionError) as exc:
            logger.error(f"Failed to fetch subscription status: {exc}")
            # Do not clear auth on subscription failures; treat as unknown tier.
            self._subscription_tier = None
            self._is_pro = False
            return

        self._subscription_tier = str(data.get("tier"))
        self._is_pro = bool(data.get("is_pro"))
        logger.info("Subscription status updated from API.")

    # -------------------------------------------------------------- Public API

    def login(self, username: str, password: str, device_name: str = "", device_info: Optional[str] = None) -> LoginResult:
        """Perform password login. Returns either success or a 2FA pending token."""
        payload: Dict[str, Any] = {
            "username": username,
            "password": password,
            "device_name": device_name,
            "device_info": device_info,
        }
        try:
            data: Dict[str, Any] = self._api.post("/auth/login", json=payload)
        except (NetworkError, ApiError, AuthError) as exc:
            logger.error(f"Login failed: {exc}")
            return LoginResult(success=False, error_message=str(exc))

        # 2FA required path
        if data.get("two_fa_required"):
            token = data.get("two_fa_pending_token")
            self._pending_two_fa_token = token
            logger.info("Login requires 2FA verification.")
            return LoginResult(success=False, two_fa_required=True, two_fa_pending_token=token)

        # Direct token response path
        access = data.get("access_token")
        refresh = data.get("refresh_token")
        if not access or not refresh:
            logger.error("Login response missing tokens.")
            return LoginResult(success=False, error_message="Login response missing tokens.")

        self._set_tokens(access, refresh)
        try:
            self._fetch_user_profile()
        except Exception:
            # Error already logged; present a generic message to the caller.
            return LoginResult(success=False, error_message="Login succeeded but failed to load user profile.")

        self._pending_two_fa_token = None
        # Also load subscription status for gating features.
        self.refresh_subscription_status()
        return LoginResult(success=True)

    def complete_two_fa(self, code: str, device_name: str = "", device_info: Optional[str] = None) -> TwoFAVerifyResult:
        """Complete a 2FA login using the pending token and verification code."""
        if not self._pending_two_fa_token:
            return TwoFAVerifyResult(success=False, error_message="No 2FA login is pending.")

        payload: Dict[str, Any] = {
            "two_fa_pending_token": self._pending_two_fa_token,
            "code": code,
            "device_name": device_name,
            "device_info": device_info,
        }
        try:
            data: Dict[str, Any] = self._api.post("/auth/2fa/verify", json=payload)
        except (NetworkError, ApiError, AuthError) as exc:
            logger.error(f"2FA verification failed: {exc}")
            return TwoFAVerifyResult(success=False, error_message=str(exc))

        access = data.get("access_token")
        refresh = data.get("refresh_token")
        if not access or not refresh:
            logger.error("2FA verification response missing tokens.")
            return TwoFAVerifyResult(success=False, error_message="2FA verification response missing tokens.")

        self._set_tokens(access, refresh)
        try:
            self._fetch_user_profile()
        except Exception:
            return TwoFAVerifyResult(success=False, error_message="2FA succeeded but failed to load user profile.")

        self._pending_two_fa_token = None
        # Also load subscription status for gating features.
        self.refresh_subscription_status()
        return TwoFAVerifyResult(success=True)

    def refresh_tokens(self) -> bool:
        """Attempt to refresh tokens using the stored refresh token."""
        if not self._tokens:
            return False

        payload = {"refresh_token": self._tokens.refresh_token}
        try:
            data: Dict[str, Any] = self._api.post("/auth/refresh", json=payload)
        except (NetworkError, ApiError, AuthError) as exc:
            logger.error(f"Token refresh failed: {exc}")
            self._clear_state()
            return False

        access = data.get("access_token")
        refresh = data.get("refresh_token")
        if not access or not refresh:
            logger.error("Refresh response missing tokens.")
            self._clear_state()
            return False

        self._set_tokens(access, refresh)
        return True

    def logout(self) -> None:
        """Log out from the current session and clear local state."""
        if self._tokens is not None:
            payload = {"refresh_token": self._tokens.refresh_token}
            try:
                # Ignore body; API responds with 204.
                self._api.post("/auth/logout", json=payload, expects_body=False, requires_auth=False)
            except (NetworkError, ApiError) as exc:
                # On logout failures, we still clear local state – server-side session
                # might be stale or already revoked.
                logger.warning(f"Logout request failed: {exc}")
        self._clear_state()

    # ------------------------------------------------------ Device management

    def list_devices(self) -> List[Dict[str, Any]]:
        """Return a list of active devices for the current user."""
        try:
            return self._api.get("/auth/devices", requires_auth=True)
        except (NetworkError, ApiError, AuthError, PermissionError) as exc:
            logger.error(f"Failed to list devices: {exc}")
            raise

    def revoke_device(self, device_id: int) -> None:
        """Revoke a specific device session."""
        path = f"/auth/devices/{device_id}"
        try:
            self._api.delete(path, requires_auth=True, expects_body=False)
        except (NetworkError, ApiError, AuthError, PermissionError) as exc:
            logger.error(f"Failed to revoke device {device_id}: {exc}")
            raise

