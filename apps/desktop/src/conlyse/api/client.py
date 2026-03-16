from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class ApiConfig:
    """Configuration options for the Conlyse API client."""

    base_url: str
    timeout_seconds: float = 10.0


class ApiError(Exception):
    """Base exception for API related errors."""


class NetworkError(ApiError):
    """Raised when a network error occurs while talking to the API."""


class AuthError(ApiError):
    """Raised for authentication or authorization related failures."""


class PermissionError(ApiError):
    """Raised when the user lacks permission for a given API call."""


class ApiClient:
    """HTTP client for talking to the Conlyse services/api backend.

    This class is intentionally minimal; higher level managers (e.g. AuthManager)
    will use it to implement specific flows like login, 2FA, and downloads.
    """

    def __init__(self, config: ApiConfig):
        self._config = config
        # Access token is attached automatically to authenticated requests.
        self._access_token: Optional[str] = None

        # Simple connectivity status tracking.
        self._last_ok: Optional[bool] = None
        self._last_error: Optional[str] = None

        # A single shared underlying HTTP client keeps connections pooled.
        self._client = httpx.Client(
            base_url=self._config.base_url.rstrip("/"),
            timeout=self._config.timeout_seconds,
            headers={
                "Accept": "application/json",
            },
        )

    @property
    def last_ok(self) -> Optional[bool]:
        """Whether the last request completed successfully (True/False) or is unknown (None)."""
        return self._last_ok

    @property
    def last_error(self) -> Optional[str]:
        """Text representation of the last error, if any."""
        return self._last_error

    @property
    def base_url(self) -> str:
        return self._config.base_url

    def set_access_token(self, token: Optional[str]) -> None:
        """Set or clear the current access token used for authenticated requests."""
        self._access_token = token

    # --- Low-level request helpers -------------------------------------------------

    def _build_headers(self, requires_auth: bool) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if requires_auth and self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _handle_response(self, response: httpx.Response, expects_body: bool = True) -> Any:
        if response.status_code in (401, 403):
            # Distinguish between auth vs permission where possible.
            if response.status_code == 401:
                raise AuthError("Authentication failed or token expired.")
            raise PermissionError("You do not have permission to perform this action.")

        if 400 <= response.status_code < 600:
            # Try to surface API-provided error messages when present.
            try:
                payload = response.json()
                message = payload.get("detail") or payload.get("message") or str(payload)
            except Exception:
                message = response.text
            raise ApiError(f"API request failed with status {response.status_code}: {message}")

        if not expects_body:
            return None

        # Default: parse JSON body.
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError("Failed to parse JSON response from API.") from exc

    def get(self, path: str, *, requires_auth: bool = False, params: Optional[Dict[str, Any]] = None) -> Any:
        """Perform a GET request against the API."""
        try:
            response = self._client.get(
                path,
                params=params,
                headers=self._build_headers(requires_auth=requires_auth),
            )
        except httpx.RequestError as exc:
            self._last_ok = False
            self._last_error = str(exc)
            raise NetworkError(f"Network error while calling API: {exc}") from exc

        try:
            result = self._handle_response(response)
        except ApiError as exc:
            self._last_ok = False
            self._last_error = str(exc)
            raise
        else:
            self._last_ok = True
            self._last_error = None
            return result

    def post(
        self,
        path: str,
        *,
        requires_auth: bool = False,
        json: Optional[Dict[str, Any]] = None,
        expects_body: bool = True,
    ) -> Any:
        """Perform a POST request against the API."""
        try:
            response = self._client.post(
                path,
                json=json,
                headers=self._build_headers(requires_auth=requires_auth),
            )
        except httpx.RequestError as exc:
            self._last_ok = False
            self._last_error = str(exc)
            raise NetworkError(f"Network error while calling API: {exc}") from exc

        try:
            result = self._handle_response(response, expects_body=expects_body)
        except ApiError as exc:
            self._last_ok = False
            self._last_error = str(exc)
            raise
        else:
            self._last_ok = True
            self._last_error = None
            return result

    def delete(
        self,
        path: str,
        *,
        requires_auth: bool = False,
        expects_body: bool = False,
    ) -> Any:
        """Perform a DELETE request against the API."""
        try:
            response = self._client.delete(
                path,
                headers=self._build_headers(requires_auth=requires_auth),
            )
        except httpx.RequestError as exc:
            self._last_ok = False
            self._last_error = str(exc)
            raise NetworkError(f"Network error while calling API: {exc}") from exc

        try:
            result = self._handle_response(response, expects_body=expects_body)
        except ApiError as exc:
            self._last_ok = False
            self._last_error = str(exc)
            raise
        else:
            self._last_ok = True
            self._last_error = None
            return result

    def close(self) -> None:
        """Close the underlying HTTP client and free resources."""
        self._client.close()

