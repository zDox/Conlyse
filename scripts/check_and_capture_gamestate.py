#!/usr/bin/env python
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import requests

from conflict_interface.data_types.newest.game_api_types.login_action import DEFAULT_LOGIN_ACTION
from conflict_interface.data_types.newest.game_api_types.login_action import LoginAction
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.api.hub_types.hub_game_state_enum import HubGameState
from conflict_interface.data_types.newest.game_api_types.game_state_action import GameStateAction
from conflict_interface.data_types.newest.custom_types import HashMap, LinkedList, DateTimeMillisecondsInt
from conflict_interface.data_types.newest.to_json import dump_any
from conflict_interface.logger_config import setup_library_logger

CONFLICT_DATA_REPO = "zDox/ConflictData"
FULL_TESTDATA_DIR = "FullTestData"


def _load_credentials() -> tuple[str, str, str, str]:
    """
    Mirror test credential loading: prefer env vars, otherwise raise.
    """
    keys = ["TEST_ACCOUNT_USERNAME", "TEST_ACCOUNT_PASSWORD", "TEST_ACCOUNT_EMAIL", "TEST_PROXY_URL"]
    values = [os.getenv(k) for k in keys]
    if all(v is not None for v in values):
        # type: ignore[return-value]
        return tuple(values)  # (username, password, email, proxy_url)
    missing = [k for k, v in zip(keys, values) if v is None]
    raise RuntimeError(f"Missing required environment variables for test credentials: {', '.join(missing)}")


def _pick_game_id(hub: HubInterface) -> int:
    """
    Choose a game id similar to tests:
    - Prefer one of the user's running games (not ended).
    - Otherwise, pick a global READY_TO_JOIN game for a known scenario.
    """
    my_games = hub.get_my_games(end_of_game=False)
    if my_games:
        return my_games[0].game_id

    games = hub.get_global_games(state=HubGameState.READY_TO_JOIN, scenario_id=5975)
    if not games:
        raise RuntimeError("No suitable games found (no active my games and no READY_TO_JOIN global games).")
    return games[0].game_id


def conflict_data_file_exists(version: int, token: str | None) -> bool:
    """
    Check via GitHub API whether FullTestData/full_test_data_1_v{version}.json exists in ConflictData.
    """
    filename = f"full_test_data_1_v{version}.json"
    url = f"https://api.github.com/repos/{CONFLICT_DATA_REPO}/contents/{FULL_TESTDATA_DIR}/{filename}"
    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    return False



def capture_raw_gamestate(game_interface) -> Dict[str, Any]:
    """
    Issue a GameStateAction via the underlying GameApi and return the raw server JSON.
    This uses the same action type as normal updates but never parses the result.
    """
    game_state_action = GameStateAction(
        state_type=0,
        state_id="0",
        add_state_ids_on_sent=True,
        option=None,
        state_ids=None,
        time_stamps=None,
        actions=LinkedList([DEFAULT_LOGIN_ACTION]),
    )

    json_action = dump_any(game_state_action)
    response_json = game_interface.game_api.make_game_server_request(json_action)
    return response_json


def write_response_to_temp(version: int, response_json: Dict[str, Any]) -> Path:
    tmpdir = Path(tempfile.mkdtemp(prefix="conflict_full_testdata_"))
    out_path = tmpdir / f"full_test_data_1_v{version}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(response_json, f, ensure_ascii=False, separators=(",", ":"))
    return out_path


def main() -> int:
    github_token = os.getenv("CONFLICT_DATA_TOKEN")

    username, password, _email, proxy_url = _load_credentials()
    proxy = {"https": proxy_url} if proxy_url else None

    hub = HubInterface(proxy=proxy)
    hub.login(username, password)

    game_id = _pick_game_id(hub)

    # 1) Guest join to detect client version
    guest_game = hub.join_game(game_id, guest=True)
    client_version = guest_game.game_api.client_version
    print(f"Detected client_version={client_version}", file=sys.stderr)

    # 2) Check ConflictData for existing file
    if conflict_data_file_exists(client_version, github_token):
        print("no_change")
        return 0
    print("Change required, capturing new game state")

    # 3) Real join and random country selection
    real_game = hub.join_game(game_id, guest=False)

    if not real_game.is_country_selected():
        print("Selecting random country")
        real_game.select_country(country_id=-1, team_id=-1, random_country_team=True)

    # 4) Capture raw gamestate JSON directly from GameApi
    response_json = capture_raw_gamestate(real_game)
    out_path = write_response_to_temp(client_version, response_json)

    result = {"version": client_version, "file": str(out_path)}
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

