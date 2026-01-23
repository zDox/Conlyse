import gc
import random
import time
import matplotlib.pyplot as plt
import numpy as np

from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.patch_graph import PatchGraph
from paths import TEST_DATA


def benchmark_jump(ritf, from_time, to_time, create_long_patches=True):
    """Benchmark a single jump operation."""
    # Warmup
    ritf.jump_to(from_time, create_long_patches=False)

    # Calculate operations
    ops = PatchGraph.cost(ritf._replay.storage.patch_graph.find_patch_path(from_time, to_time))

    gc.collect()

    # Measure jump time
    t1 = time.perf_counter()
    ritf.jump_to(to_time, create_long_patches=create_long_patches)
    t2 = time.perf_counter()

    jump_time = t2 - t1
    ops_per_sec = ops / jump_time if jump_time > 0 else 0

    return ops, jump_time, ops_per_sec


def benchmark_next_jump(ritf, from_time):
    """Benchmark a jump to next patch."""
    # Warmup
    ritf.jump_to(from_time, create_long_patches=False)

    next_time = ritf.get_next_timestamp()
    if next_time is None:
        return None, None, None

    ops = PatchGraph.cost(ritf._replay.storage.patch_graph.find_patch_path(from_time, next_time))

    gc.collect()

    t1 = time.perf_counter()
    ritf.jump_to_next_patch()
    t2 = time.perf_counter()

    jump_time = t2 - t1
    ops_per_sec = ops / jump_time if jump_time > 0 else 0

    return ops, jump_time, ops_per_sec


def benchmark_prev_jump(ritf, from_time):
    """Benchmark a jump to previous patch."""
    # Warmup
    ritf.jump_to(from_time, create_long_patches=False)

    prev_time = ritf.get_previous_timestamp()
    if prev_time is None:
        return None, None, None

    ops = PatchGraph.cost(ritf._replay.storage.patch_graph.find_patch_path(from_time, prev_time))

    gc.collect()

    t1 = time.perf_counter()
    ritf.jump_to_previous_patch()
    t2 = time.perf_counter()

    jump_time = t2 - t1
    ops_per_sec = ops / jump_time if jump_time > 0 else 0

    return ops, jump_time, ops_per_sec


def main():
    num_samples = 50  # Number of random samples to collect

    # Data storage
    random_long_data = {'ops': [], 'time': [], 'ops_per_sec': []}
    random_data = {'ops': [], 'time': [], 'ops_per_sec': []}
    next_data = {'ops': [], 'time': [], 'ops_per_sec': []}
    prev_data = {'ops': [], 'time': [], 'ops_per_sec': []}

    ritf = ReplayInterface(file_path=TEST_DATA / "test_replay_10626234.bin", player_id=1, game_id=12345)

    print("Collecting random jump samples (with long patches)...")
    for i in range(num_samples):
        ritf.close()
        ritf.open(mode="r")

        timestamps = ritf.get_timestamps()
        from_time = random.choice(timestamps)
        to_time = random.choice(timestamps)

        ops, jump_time, ops_per_sec = benchmark_jump(ritf, from_time, to_time, create_long_patches=True)

        random_long_data['ops'].append(ops)
        random_long_data['time'].append(jump_time * 1000)  # Convert to ms
        random_long_data['ops_per_sec'].append(ops_per_sec)

        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{num_samples} samples collected")

    print("\nCollecting random jump samples (without long patches)...")
    for i in range(num_samples):
        ritf.close()
        ritf.open(mode="r")

        timestamps = ritf.get_timestamps()
        from_time = random.choice(timestamps)
        to_time = random.choice(timestamps)

        ops, jump_time, ops_per_sec = benchmark_jump(ritf, from_time, to_time, create_long_patches=False)

        random_data['ops'].append(ops)
        random_data['time'].append(jump_time * 1000)  # Convert to ms
        random_data['ops_per_sec'].append(ops_per_sec)

        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{num_samples} samples collected")

    print("\nCollecting next jump samples...")
    ritf.close()
    ritf.open(mode="r")
    timestamps = ritf.get_timestamps()
    for i in range(min(num_samples, len(timestamps) - 1)):
        from_time = random.choice(timestamps[:-1])  # Ensure there's a next timestamp

        ops, jump_time, ops_per_sec = benchmark_next_jump(ritf, from_time)

        if ops is not None:
            next_data['ops'].append(ops)
            next_data['time'].append(jump_time * 1_000_000)  # Convert to µs
            next_data['ops_per_sec'].append(ops_per_sec)

        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{num_samples} samples collected")

    print("\nCollecting previous jump samples...")
    for i in range(min(num_samples, len(timestamps) - 1)):
        from_time = random.choice(timestamps[1:])  # Ensure there's a previous timestamp

        ops, jump_time, ops_per_sec = benchmark_prev_jump(ritf, from_time)

        if ops is not None:
            prev_data['ops'].append(ops)
            prev_data['time'].append(jump_time * 1_000_000)  # Convert to µs
            prev_data['ops_per_sec'].append(ops_per_sec)

        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{num_samples} samples collected")

    ritf.close()

    # Create visualizations
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Replay Interface Performance Analysis', fontsize=16, fontweight='bold')

    # Random jumps with long patches - Time
    ax = axes[0, 0]
    ax.scatter(random_long_data['ops'], random_long_data['time'], alpha=0.6, s=50)
    ax.set_xlabel('Operations')
    ax.set_ylabel('Time (ms)')
    ax.set_title('Random Jump Time (with long patches)')
    ax.grid(True, alpha=0.3)
    z = np.polyfit(random_long_data['ops'], random_long_data['time'], 1)
    p = np.poly1d(z)
    ax.plot(sorted(random_long_data['ops']), p(sorted(random_long_data['ops'])),
            "r--", alpha=0.8, label=f'Trend: {z[0]:.2e}x + {z[1]:.2f}')
    ax.legend()

    # Random jumps without long patches - Time
    ax = axes[0, 1]
    ax.scatter(random_data['ops'], random_data['time'], alpha=0.6, s=50, color='orange')
    ax.set_xlabel('Operations')
    ax.set_ylabel('Time (ms)')
    ax.set_title('Random Jump Time (without long patches)')
    ax.grid(True, alpha=0.3)
    z = np.polyfit(random_data['ops'], random_data['time'], 1)
    p = np.poly1d(z)
    ax.plot(sorted(random_data['ops']), p(sorted(random_data['ops'])),
            "r--", alpha=0.8, label=f'Trend: {z[0]:.2e}x + {z[1]:.2f}')
    ax.legend()

    # Next jump - Time
    ax = axes[1, 0]
    ax.scatter(next_data['ops'], next_data['time'], alpha=0.6, s=50, color='green')
    ax.set_xlabel('Operations')
    ax.set_ylabel('Time (µs)')
    ax.set_title('Next Patch Jump Time')
    ax.grid(True, alpha=0.3)
    if len(next_data['ops']) > 1:
        z = np.polyfit(next_data['ops'], next_data['time'], 1)
        p = np.poly1d(z)
        ax.plot(sorted(next_data['ops']), p(sorted(next_data['ops'])),
                "r--", alpha=0.8, label=f'Trend: {z[0]:.2e}x + {z[1]:.2f}')
        ax.legend()

    # Previous jump - Time
    ax = axes[1, 1]
    ax.scatter(prev_data['ops'], prev_data['time'], alpha=0.6, s=50, color='purple')
    ax.set_xlabel('Operations')
    ax.set_ylabel('Time (µs)')
    ax.set_title('Previous Patch Jump Time')
    ax.grid(True, alpha=0.3)
    if len(prev_data['ops']) > 1:
        z = np.polyfit(prev_data['ops'], prev_data['time'], 1)
        p = np.poly1d(z)
        ax.plot(sorted(prev_data['ops']), p(sorted(prev_data['ops'])),
                "r--", alpha=0.8, label=f'Trend: {z[0]:.2e}x + {z[1]:.2f}')
        ax.legend()

    plt.tight_layout()
    plt.savefig('replay_performance_time.png', dpi=300, bbox_inches='tight')
    print("\nSaved: replay_performance_time.png")

    # Create throughput visualization
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Replay Interface Throughput Analysis', fontsize=16, fontweight='bold')

    # Random jumps with long patches - Ops/sec
    ax = axes[0, 0]
    ax.scatter(random_long_data['ops'], random_long_data['ops_per_sec'], alpha=0.6, s=50)
    ax.set_xlabel('Operations')
    ax.set_ylabel('Operations per Second')
    ax.set_title('Random Jump Throughput (with long patches)')
    ax.grid(True, alpha=0.3)

    # Random jumps without long patches - Ops/sec
    ax = axes[0, 1]
    ax.scatter(random_data['ops'], random_data['ops_per_sec'], alpha=0.6, s=50, color='orange')
    ax.set_xlabel('Operations')
    ax.set_ylabel('Operations per Second')
    ax.set_title('Random Jump Throughput (without long patches)')
    ax.grid(True, alpha=0.3)

    # Next jump - Ops/sec
    ax = axes[1, 0]
    ax.scatter(next_data['ops'], next_data['ops_per_sec'], alpha=0.6, s=50, color='green')
    ax.set_xlabel('Operations')
    ax.set_ylabel('Operations per Second')
    ax.set_title('Next Patch Jump Throughput')
    ax.grid(True, alpha=0.3)

    # Previous jump - Ops/sec
    ax = axes[1, 1]
    ax.scatter(prev_data['ops'], prev_data['ops_per_sec'], alpha=0.6, s=50, color='purple')
    ax.set_xlabel('Operations')
    ax.set_ylabel('Operations per Second')
    ax.set_title('Previous Patch Jump Throughput')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('replay_performance_throughput.png', dpi=300, bbox_inches='tight')
    print("Saved: replay_performance_throughput.png")

    # Print summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)

    print("\nRandom Jump (with long patches):")
    print(f"  Ops range: {min(random_long_data['ops'])} - {max(random_long_data['ops'])}")
    print(f"  Time range: {min(random_long_data['time']):.2f} - {max(random_long_data['time']):.2f} ms")
    print(f"  Avg throughput: {np.mean(random_long_data['ops_per_sec']):.0f} ops/sec")

    print("\nRandom Jump (without long patches):")
    print(f"  Ops range: {min(random_data['ops'])} - {max(random_data['ops'])}")
    print(f"  Time range: {min(random_data['time']):.2f} - {max(random_data['time']):.2f} ms")
    print(f"  Avg throughput: {np.mean(random_data['ops_per_sec']):.0f} ops/sec")

    print("\nNext Patch Jump:")
    print(f"  Ops range: {min(next_data['ops'])} - {max(next_data['ops'])}")
    print(f"  Time range: {min(next_data['time']):.2f} - {max(next_data['time']):.2f} µs")
    print(f"  Avg throughput: {np.mean(next_data['ops_per_sec']):.0f} ops/sec")

    print("\nPrevious Patch Jump:")
    print(f"  Ops range: {min(prev_data['ops'])} - {max(prev_data['ops'])}")
    print(f"  Time range: {min(prev_data['time']):.2f} - {max(prev_data['time']):.2f} µs")
    print(f"  Avg throughput: {np.mean(prev_data['ops_per_sec']):.0f} ops/sec")


if __name__ == "__main__":
    test_start = time.perf_counter()
    main()
    test_end = time.perf_counter()
    print(f"\nTotal time: {test_end - test_start:.2f}s")