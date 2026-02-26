from __future__ import annotations

from pathlib import Path

import httpx

from conlyse.logger import get_logger


logger = get_logger()


def download_to_file(url: str, dest_path: str, chunk_size: int = 64 * 1024) -> None:
    """Download the content at *url* to *dest_path*.

    Uses streaming HTTP to avoid loading the entire file into memory.
    Raises httpx.HTTPError on failure.
    """
    path = Path(dest_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading from {url} to {dest_path}")

    with httpx.stream("GET", url, follow_redirects=True, timeout=None) as response:
        response.raise_for_status()
        with path.open("wb") as f:
            for chunk in response.iter_bytes(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

    logger.info(f"Download completed: {dest_path}")

