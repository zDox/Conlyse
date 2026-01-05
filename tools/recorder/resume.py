from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Optional

from conflict_interface.interface.hub_interface import HubInterface
from conflict_interface.interface.online_interface import OnlineInterface
from conflict_interface.replay.replay import Replay


def load_resume_metadata(metadata_path: Path) -> Optional[dict]:
    try:
        with open(metadata_path, "r") as f:
            meta = json.load(f)
        return meta.get("resume")
    except Exception:
        return None


def restore_online_interface_from_metadata(metadata_path: str) -> Optional[OnlineInterface]:
    """
    Restore an OnlineInterface from persisted resume metadata and replay file without full game join.
    """
    resume = load_resume_metadata(Path(metadata_path))
    if not resume:
        return None

    game_id = resume.get("game_id")
    replay_path = resume.get("replay_path")
    if not game_id or not replay_path:
        return None

    hub_itf = HubInterface()
    proxy = resume.get("proxy")
    if proxy:
        hub_itf.set_proxy(proxy)

    if resume.get("auth") is not None:
        hub_itf.api.auth = resume.get("auth")
    if resume.get("cookies"):
        hub_itf.api.session.cookies.update(resume.get("cookies"))

    game_itf = OnlineInterface(
        game_id=game_id,
        session=hub_itf.api.session,
        auth_details=deepcopy(hub_itf.api.auth),
        proxy=hub_itf.api.proxy,
        guest=True,
        replay_filepath=replay_path,
    )

    # Load last game state from replay
    replay = Replay(Path(replay_path), mode="a", game_id=game_id, player_id=resume.get("player_id"))
    replay.open()
    last_state = replay.storage.last_game_state or replay.storage.initial_game_state
    static_map = replay.storage.static_map_data
    if last_state:
        last_state.set_game(game_itf)
        game_itf.game_state = last_state
    if static_map:
        static_map.set_game(game_itf)
        game_itf.static_map_data = static_map
        if game_itf.game_state and game_itf.game_state.states.map_state:
            game_itf.game_state.states.map_state.map.set_static_map_data(static_map)
    replay.close()

    return game_itf

