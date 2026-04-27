from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from urllib.parse import urlparse

import httpx

from conlyse.logger import get_logger
from conlyse.utils.downloads import download_to_file
from conlyse.version import __version__ as CONLYSE_VERSION

if TYPE_CHECKING:
    from conlyse.app import App


logger = get_logger()

GITHUB_REPO = "zDox/Conlyse"
GITHUB_RELEASES_LATEST_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    download_url: str
    platform: str


class UpdateManager:
    """Checks for and downloads Conlyse desktop updates via GitHub Releases."""

    def __init__(self, app: App):
        self.app = app

        self._current_version: str = CONLYSE_VERSION
        self._last_info: Optional[UpdateInfo] = None
        self._last_error: Optional[str] = None

    # ----------------------------------------------------------------- Properties

    @property
    def current_version(self) -> str:
        return self._current_version

    @property
    def last_info(self) -> Optional[UpdateInfo]:
        return self._last_info

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def has_update(self) -> bool:
        return (
            self._last_info is not None
            and self._last_info.latest_version != self._last_info.current_version
        )

    # ------------------------------------------------------------------ Internals

    def _platform_slug(self) -> str:
        """Return the platform identifier used to match release asset names."""
        import platform

        system = platform.system().lower()
        if system.startswith("win"):
            return "windows"
        if system == "darwin":
            return "macos"
        return "linux"

    # ---------------------------------------------------------------- Public API

    def check_for_updates(self) -> Optional[UpdateInfo]:
        """Query GitHub Releases for the latest available desktop version."""
        self._last_error = None
        platform_slug = self._platform_slug()

        try:
            response = httpx.get(
                GITHUB_RELEASES_LATEST_URL,
                headers={"Accept": "application/vnd.github+json"},
                timeout=10.0,
                follow_redirects=True,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            message = f"Failed to check for updates: {exc}"
            logger.error(message)
            self._last_error = message
            self._last_info = None
            return None

        tag_name: str = str(data.get("tag_name", "")).strip()
        # Release tags are expected to follow the "vX.Y.Z" convention; strip the
        # leading "v" so the version string is plain semver (e.g. "1.2.3").
        latest_version = tag_name.lstrip("v")
        if not latest_version:
            message = "GitHub release response missing tag_name."
            logger.error(message)
            self._last_error = message
            self._last_info = None
            return None

        assets: list = data.get("assets", [])
        url = ""
        for asset in assets:
            asset_name: str = str(asset.get("name", "")).lower()
            # Match the platform slug only at word boundaries (delimited by -, _, . or
            # start/end of the filename stem) to avoid false positives such as
            # "non-windows-build" matching "windows".
            if re.search(r"(?<![a-z])" + re.escape(platform_slug) + r"(?![a-z])", asset_name):
                url = str(asset.get("browser_download_url", "")).strip()
                break

        if not url:
            message = f"No release asset found for platform '{platform_slug}' in release {latest_version}."
            logger.error(message)
            self._last_error = message
            self._last_info = None
            return None

        self._last_info = UpdateInfo(
            current_version=self._current_version,
            latest_version=latest_version,
            download_url=url,
            platform=platform_slug,
        )
        logger.info(
            f"Update check: current={self._current_version}, latest={latest_version}, platform={platform_slug}"
        )
        return self._last_info

    def download_latest(self, dest_dir: Optional[str] = None) -> Optional[str]:
        """Download the latest available installer/binary. Returns path or None on failure."""
        self._last_error = None

        info = self._last_info or self.check_for_updates()
        if info is None:
            # _last_error is already set.
            return None

        url = info.download_url
        parsed = urlparse(url)
        filename = Path(parsed.path).name or f"conlyse_{info.latest_version}_{info.platform}.bin"

        target_dir = Path(dest_dir) if dest_dir is not None else Path("app_data") / "updates"
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_path = str(target_dir / filename)

        try:
            download_to_file(url, dest_path)
        except Exception as exc:
            message = f"Failed to download update: {exc}"
            logger.error(message)
            self._last_error = message
            return None

        logger.info(f"Update downloaded to {dest_path}")
        return dest_path

