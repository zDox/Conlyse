from datetime import timedelta

from conflict_interface.utils.helper import unix_ms_to_datetime
from conflict_interface.utils.helper import unix_to_datetime
from tools.replay_debug import command


@command(
    name="check-timestamps",
    description="Check and validate timestamps in the replay",
    usage="check-timestamps"
)
def cmd_check_timestamps(cli):
    """
    Checks if the time between from_timestamp and to_timestamp in a patch
    is the same as the timestamp in the previous game state and the next game state.
    """
    if not cli.ritf:
        print("Error: Replay not opened.")
        return
    ritf = cli.ritf
    print("Checking timestamps in replay...")
    saved_timestamp = ritf.current_time
    ritf.jump_to(ritf.start_time)

    previous_timestamp = ritf.current_time
    current_timestamp = ritf.get_next_timestamp()

    current_state_timestamp = unix_ms_to_datetime(int(ritf.game_state.time_stamp))

    max_diff: timedelta = timedelta(0)
    max_context = None

    while current_timestamp:
        # Calculate patch delta and patch boundaries
        patches = ritf.replay.storage.patch_graph.find_patch_path(previous_timestamp, current_timestamp)
        if not patches:
            print(f"No patches found between {previous_timestamp} and {current_timestamp}")
            previous_timestamp = current_timestamp
            current_timestamp = ritf.get_next_timestamp()
            continue
        if len(patches) != 1:
            print(f"Multiple patches found between {previous_timestamp} and {current_timestamp}")
            previous_timestamp = current_timestamp
            current_timestamp = ritf.get_next_timestamp()
            continue

        patch = patches[0]
        patch_from_dt = unix_to_datetime(patch.from_timestamp)
        patch_to_dt = unix_to_datetime(patch.to_timestamp)
        patch_delta: timedelta = patch_to_dt - patch_from_dt

        # Jump to the next patch (advances game state)
        ritf.jump_to_next_patch()

        # Calculate state delta and gaps between states and patch boundaries
        previous_state_timestamp = current_state_timestamp
        current_state_timestamp = unix_ms_to_datetime(int(ritf.game_state.time_stamp))
        state_delta: timedelta = current_state_timestamp - previous_state_timestamp

        start_gap: timedelta = patch_from_dt - previous_state_timestamp
        end_gap: timedelta = current_state_timestamp - patch_to_dt

        diff = abs(start_gap) + abs(end_gap)
        if diff > max_diff:
            max_diff = diff
            max_context = {
                "patch": patch,
                "patch_delta": patch_delta,
                "state_delta": state_delta,
                "start_gap": start_gap,
                "end_gap": end_gap,
                "previous_state_ts": previous_state_timestamp,
                "current_state_ts": current_state_timestamp,
                "previous_timestamp": patch_from_dt,
                "current_timestamp": patch_to_dt,
            }

        previous_timestamp = current_timestamp
        current_timestamp = ritf.get_next_timestamp()

    if not max_context:
        print("No valid patch/state comparisons were made.")
    else:
        p = max_context
        patch = p["patch"]
        print("Largest start/end gap discrepancy found:")
        print(f"  Patch from {patch.from_timestamp} to {patch.to_timestamp} (delta: {p['patch_delta']})")
        print(f"  Game states from {p['previous_state_ts']} to {p['current_state_ts']} (delta: {p['state_delta']})")
        print(f"  Start gap (prev state -> patch.from): {p['start_gap']}")
        print(f"  End gap (patch.to -> next state): {p['end_gap']}")
        print(f"  Difference in seconds: {max_diff.total_seconds()}")

    ritf.jump_to(saved_timestamp)