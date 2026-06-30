#!/usr/bin/env python
"""
Checks whether the live game client has published a new clientVersion that
ConflictData has neither a `v{N}/` folder nor an in-flight PR branch for yet.
Prints `{"version": N}` on the last line if a new version was found,
otherwise prints `no_change`.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict

import requests

from conflict_interface.api.hub_types.hub_game_state_enum import HubGameState
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger

CONFLICT_DATA_REPO = "zDox/ConflictData"


def _load_credentials() -> tuple[str, str, str, str]:
    keys = ["TEST_ACCOUNT_USERNAME", "TEST_ACCOUNT_PASSWORD", "TEST_ACCOUNT_EMAIL", "TEST_PROXY_URL"]
    values = [os.getenv(k) for k in keys]
    if all(v is not None for v in values):
        return tuple(values)  # type: ignore[return-value]
    missing = [k for k, v in zip(keys, values) if v is None]
    raise RuntimeError(f"Missing required environment variables for test credentials: {', '.join(missing)}")


def _pick_game_id(hub: HubInterface) -> int:
    my_games = hub.get_my_games(end_of_game=False)
    if my_games:
        return my_games[0].game_id

    games = hub.get_global_games(state=HubGameState.READY_TO_JOIN, scenario_id=5975)
    if not games:
        raise RuntimeError("No suitable games found (no active my games and no READY_TO_JOIN global games).")
    return games[0].game_id


def _github_get(url: str, token: str | None) -> requests.Response:
    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.get(url, headers=headers, timeout=30)


def version_folder_exists(version: int, token: str | None) -> bool:
    url = f"https://api.github.com/repos/{CONFLICT_DATA_REPO}/contents/v{version}"
    resp = _github_get(url, token)
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    return False


def version_branch_exists(version: int, token: str | None) -> bool:
    url = f"https://api.github.com/repos/{CONFLICT_DATA_REPO}/branches/add-version-data-v{version}"
    resp = _github_get(url, token)
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    return False


def main() -> int:
    setup_library_logger()
    github_token = os.getenv("CONFLICT_DATA_TOKEN")

    username, password, _email, proxy_url = _load_credentials()

    hub = HubInterface()
    hub.login(username, password)

    game_id = _pick_game_id(hub)

    guest_game = hub.join_game(game_id, guest=True)
    client_version = guest_game.game_api.client_version
    print(f"Detected client_version={client_version}", file=sys.stderr)

    if version_folder_exists(client_version, github_token) or version_branch_exists(client_version, github_token):
        print("no_change")
        return 0

    print(json.dumps({"version": client_version}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
