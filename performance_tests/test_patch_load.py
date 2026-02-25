"""Quick test to see if patches are loading correctly."""
from conflict_interface.replay.replaysegment import ReplaySegment

replay_file = r"..\examples\replay.db"

print("Opening replay...")
replay = ReplaySegment(replay_file, mode='r')
replay.open()

print(f"Timestamps: {len(replay.get_timestamps())}")
print(f"Game state timestamps: {len(replay.get_game_state_timestamps())}")

# Check internal state
print(f"_patches dict: {len(replay._patches)}")
print(f"_timestamps list: {len(replay._timestamps)}")

# Try to access patches
if replay._patches:
    first_key = list(replay._patches.keys())[0]
    print(f"First patch key: {first_key}")
else:
    print("No patches in memory!")

# Check if we can jump
try:
    timestamps = replay.get_timestamps()
    if len(timestamps) >= 2:
        patches = replay._find_patch_path(replay._start_time, timestamps[0])
        print(f"Successfully jumped, got {len(patches)} patches")
except Exception as e:
    print(f"Error jumping: {e}")

replay.close()

