import bisect
import time

from matplotlib import pyplot as plt

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.long_patch import create_long_patch
from conflict_interface.replay.patch_graph import PatchGraph
from paths import TEST_DATA

COLUMN_MAPPING = {
        "PlayerID": "player_id",
        "TeamName": None,  # Computed from team_id
        "Name": "name",
        "CapitalName": None,  # Computed from capital_id
        "NationName": "nation_name",
        "ComputerPlayer": "computer_player",
        "NativeComputer": "native_computer",
        "UserName": "user_name",
        "Defeated": "defeated",
        "Retired": "retired",
        "Playing": "playing",
        "Taken": "taken",
        "Faction": "faction",
        "Available": "available",
        "PremiumUser": "premium_user",
        "AccumulatedVictoryPoints": "accumulated_victory_points",
        "DailyVictoryPoints": "daily_victory_points",
        "TerroristCountry": "terrorist_country",
        "Banned": "banned",
        "VictoryPoints": "victory_points",
    }

def benchmark_across_indices(start_idx=2000, end_idx=7000, step=100, runs=10):
    """
    Benchmark ops/sec across different target indices.
    Measures total time (build_time + additional_jump_time) / ops_before
    """
    import gc

    print("=" * 80)
    print("BENCHMARKING ACROSS INDICES")
    print("=" * 80)

    ritf = ReplayInterface(TEST_DATA / "test_replay_game_10631784.bin", player_id=0, game_id=12345)
    ritf.open('r')
    ritf.register_province_trigger(["owner_id", "resource_production", "morale"])
    trigger_attributes = [
        attr_name for attr_name in COLUMN_MAPPING.values()
        if attr_name is not None
    ]
    ritf.register_player_trigger(trigger_attributes)

    indices = list(range(start_idx, end_idx + 1, step))
    results = {
        'indices': [],
        'ops_per_sec': [],
        'ops_before': [],
        'ops_after': [],
        'build_time_ms': [],
        'apply_time_ms': [],
        'total_time_ms': [],
        'default_time_ms': []
    }

    for target_idx in indices:
        print(f"\nBenchmarking idx={target_idx}...", end=' ')
        from_time = ritf._replay.get_start_time()
        to_time = ritf._time_stamps_cache[target_idx]

        patch_path = ritf._replay.storage.patch_graph.find_patch_path(
            from_time,
            to_time
        )

        patch_graph = ritf._replay.storage.patch_graph
        path_tree = ritf._replay.storage.path_tree
        # Warmup
        _ = create_long_patch(from_time, to_time, patch_graph, path_tree)
        gc.collect()

        build_times = []
        apply_times = []
        total_times = []
        default_times = []

        for _ in range(runs):
            # Time with long_patch
            ritf.jump_to(from_time, create_long_patches=False)
            t1 = time.perf_counter()
            node = create_long_patch(from_time, to_time, patch_graph, path_tree)
            t2 = time.perf_counter()
            ritf._apply_patches_and_update_state([node], to_time)
            ritf.current_timestamp_index = bisect.bisect_left(ritf._time_stamps_cache, to_time)
            t3 = time.perf_counter()
            build_times.append((t2 - t1) * 1000)
            apply_times.append((t3 - t2) * 1000)
            total_times.append((t3 - t1) * 1000)
            gc.collect()

            ## Time normal jump
            #ritf.jump_to(from_time, create_long_patches=False)
            #t1 = time.perf_counter()
            #ritf.jump_to(to_time, create_long_patches=False)
            #t2 = time.perf_counter()
            #default_times.append((t2 - t1)*1000)
            #gc.collect()



        min_build_time = min(build_times)
        min_apply_time = min(apply_times)
        min_total_time = min(total_times)
        #min_default_time = min(default_times)

        ops_before = PatchGraph.cost(patch_path)
        ops_after = len(node.op_types)
        ops_per_sec = (ops_before / min_total_time) * 1000 if min_build_time > 0 else 0

        results['indices'].append(ops_before)
        results['ops_per_sec'].append(ops_per_sec)
        results['ops_before'].append(ops_before)
        results['ops_after'].append(ops_after)
        results['build_time_ms'].append(min_build_time)
        #results['default_time_ms'].append(min_default_time)
        results['apply_time_ms'].append(min_apply_time)
        results['total_time_ms'].append(min_total_time)

        print(f"{ops_per_sec:,.0f} ops/sec ({min_total_time:.2f}ms total)")

    # Create visualization
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))

    # Plot 1: Ops/sec vs Index
    ax1.plot(results['indices'], results['ops_per_sec'], 'b-', linewidth=2, marker='o')
    ax1.set_xlabel('Target Index')
    ax1.set_ylabel('Operations/Second')
    ax1.set_title('Total Performance: (build_time + apply_time) / ops_before')
    ax1.grid(True, alpha=0.3)
    ax1.ticklabel_format(axis='y', style='plain')

    # Plot 2: Time breakdown
    ax2.plot(results['indices'], results['build_time_ms'], 'g-', linewidth=2, marker='s', label='Build Time')
    #ax2.plot(results['indices'], results['default_time_ms'], 'y-', linewidth=2, marker='x', label='Default Time')
    ax2.plot(results['indices'], results['apply_time_ms'], 'b-', linewidth=2, marker='^', label='Apply Time')
    ax2.plot(results['indices'], results['total_time_ms'], 'r-', linewidth=2, marker='o', label='Total Time')

    ax2.set_xlabel('Target Index')
    ax2.set_ylabel('Time (ms)')
    ax2.set_title('Time Breakdown')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Operations
    ax3.plot(results['indices'], results['ops_before'], 'r-', linewidth=2, marker='o', label='Ops Before')
    ax3.plot(results['indices'], results['ops_after'], 'g-', linewidth=2, marker='s', label='Ops After')
    ax3.set_xlabel('Target Index')
    ax3.set_ylabel('Number of Operations')
    ax3.set_title('Operation Count Reduction')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('benchmark_results.png', dpi=150, bbox_inches='tight')
    print(f"\n✓ Graph saved to 'benchmark_results.png'")
    plt.show()

    return results

if __name__ == '__main__':
    print(benchmark_across_indices(start_idx=1, end_idx=1840, step=25, runs=3))
