#!/usr/bin/env python
"""
Records 10 raw game-state responses for a scenario_id=5975 game, 1/minute,
threading state_ids/time_stamps between polls the way ServerObserver's
ObservationSession does (rather than 10 independent full snapshots). Also
captures the game's static map data as plain beautified JSON.

Usage: record_game_responses.py <version> --out-dir <dir> --static-map-dir <dir>
Prints {"dir": "<dir>"} on the last line of stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

from conflict_interface.api.hub_types.hub_game_state_enum import HubGameState
from conflict_interface.data_types.newest.custom_types import HashMap, LinkedList
from conflict_interface.data_types.newest.game_api_types.game_state_action import GameStateAction
from conflict_interface.data_types.newest.game_api_types.login_action import DEFAULT_LOGIN_ACTION
from conflict_interface.data_types.newest.to_json import dump_any
from conflict_interface.data_types.newest.version import VERSION as DATATYPE_VERSION
from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.logger_config import setup_library_logger

NUM_RESPONSES = 10
POLL_INTERVAL_SECONDS = 60


def _load_credentials() -> tuple[str, str, str, str]:
    keys = ["TEST_ACCOUNT_USERNAME", "TEST_ACCOUNT_PASSWORD", "TEST_ACCOUNT_EMAIL", "TEST_PROXY_URL"]
    values = [os.getenv(k) for k in keys]
    if all(v is not None for v in values):
        return tuple(values)  # type: ignore[return-value]
    missing = [k for k, v in zip(keys, values) if v is None]
    raise RuntimeError(f"Missing required environment variables for test credentials: {', '.join(missing)}")


def _pick_game_id(hub: HubInterface) -> int:
    games = hub.get_global_games(state=HubGameState.READY_TO_JOIN, scenario_id=5975)
    if not games:
        raise RuntimeError("No READY_TO_JOIN global games found for scenario_id=5975.")
    return games[0].game_id


def _poll(game_interface, state_ids: Dict[str, str], time_stamps: Dict[str, str]) -> Dict[str, Any]:
    add_state_ids_on_sent = bool(state_ids) and bool(time_stamps)
    game_state_action = GameStateAction(
        state_type=0,
        state_id="0",
        add_state_ids_on_sent=add_state_ids_on_sent,
        option=None,
        state_ids=HashMap(state_ids) if add_state_ids_on_sent else None,
        time_stamps=HashMap(time_stamps) if add_state_ids_on_sent else None,
        actions=LinkedList([DEFAULT_LOGIN_ACTION]),
    )
    json_action = dump_any(game_state_action)
    return game_interface.game_api.make_game_server_request(json_action)


def _update_ids_from_response(
    response_json: Dict[str, Any], state_ids: Dict[str, str], time_stamps: Dict[str, str]
) -> None:
    result = response_json.get("result")
    if not isinstance(result, dict):
        return
    states = result.get("states")
    if not isinstance(states, dict):
        return
    for key, state in states.items():
        if not isinstance(state, dict):
            continue
        if "stateID" in state:
            state_ids[key] = str(state["stateID"])
        if "timeStamp" in state:
            time_stamps[key] = str(state["timeStamp"])


def _record_static_map_data(real_game, static_map_dir: Path) -> str:
    map_id = real_game.game_api.map_id
    static_map_json = real_game.game_api.get_static_map_data(
        map_id, session=real_game.game_api.session, proxy=real_game.game_api.proxy
    )
    static_map_dir.mkdir(parents=True, exist_ok=True)
    static_map_path = static_map_dir / f"{map_id}_{DATATYPE_VERSION}.json"
    with static_map_path.open("w", encoding="utf-8") as f:
        json.dump(static_map_json, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"Wrote {static_map_path}", file=sys.stderr)
    return map_id


def record(version: int, out_dir: Path, static_map_dir: Path) -> None:
    username, password, _email, _proxy_url = _load_credentials()

    hub = HubInterface()
    hub.login(username, password)

    game_id = _pick_game_id(hub)
    real_game = hub.join_game(game_id, guest=False)

    if not real_game.is_country_selected():
        print("Selecting random country", file=sys.stderr)
        real_game.select_country(country_id=-1, team_id=-1, random_country_team=True)

    map_id = _record_static_map_data(real_game, static_map_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    state_ids: Dict[str, str] = {}
    time_stamps: Dict[str, str] = {}

    for i in range(1, NUM_RESPONSES + 1):
        sent_state_ids = dict(state_ids)
        sent_time_stamps = dict(time_stamps)

        response_json = _poll(real_game, sent_state_ids, sent_time_stamps)

        record_entry = {
            "timestamp": int(time.time()),
            "map_id": map_id,
            "state_ids": sent_state_ids,
            "time_stamps": sent_time_stamps,
            "response": response_json,
        }
        out_path = out_dir / f"response_{i:02d}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(record_entry, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"Wrote {out_path}", file=sys.stderr)

        _update_ids_from_response(response_json, state_ids, time_stamps)

        if i < NUM_RESPONSES:
            time.sleep(POLL_INTERVAL_SECONDS)


def main() -> int:
    setup_library_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument("version", type=int)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--static-map-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    static_map_dir = Path(args.static_map_dir)
    record(args.version, out_dir, static_map_dir)

    print(json.dumps({"dir": str(out_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
