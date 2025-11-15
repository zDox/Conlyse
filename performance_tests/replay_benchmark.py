"""
Performance benchmark for Replay system.

This benchmark tests various performance aspects of the replay system:
- Loading time and memory usage
- Forward time travel (sequential patch application)
- Backward time travel (reverse patch application)
- Random access (jumping to arbitrary timestamps)
- Patch retrieval and application overhead

Usage:
    python replay_benchmark.py <replay_file.db>

Example:
    python replay_benchmark.py ../examples/replay.db
"""
import argparse
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any
from typing import List
from typing import Tuple

from conflict_interface.interface.game_interface import GameInterface
from conflict_interface.interface.replay_interface import ReplayInterface
from conflict_interface.replay.replay import Replay


class BenchmarkResult:
    """Store and format benchmark results."""

    def __init__(self, name: str):
        self.name = name
        self.duration: float = 0.0
        self.memory_before: int = 0
        self.memory_after: int = 0
        self.memory_peak: int = 0
        self.operations: int = 0
        self.details: dict = {}

    @property
    def memory_delta(self) -> int:
        """Memory change in bytes."""
        return self.memory_after - self.memory_before

    @property
    def ops_per_second(self) -> float:
        """Operations per second."""
        return self.operations / self.duration if self.duration > 0 else 0

    def format_size(self, bytes_size: int) -> str:
        """Format bytes as human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if abs(bytes_size) < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} TB"

    def __str__(self) -> str:
        lines = [
            f"\n{'=' * 80}",
            f"Benchmark: {self.name}",
            f"{'=' * 80}",
            f"Duration:          {self.duration:.4f} seconds",
            f"Operations:        {self.operations}",
            f"Ops/sec:           {self.ops_per_second:.2f}",
            f"Memory Before:     {self.format_size(self.memory_before)}",
            f"Memory After:      {self.format_size(self.memory_after)}",
            f"Memory Delta:      {self.format_size(self.memory_delta)}",
            f"Memory Peak:       {self.format_size(self.memory_peak)}",
        ]

        if self.operations > 0:
            time_per_op = (self.duration / self.operations) * 1000
            lines.append(f"Time/operation:    {time_per_op:.4f} ms")

        if self.details:
            lines.append("\nDetails:")
            for key, value in self.details.items():
                lines.append(f"  {key}: {value}")

        return '\n'.join(lines)


class ReplayBenchmark:
    """Comprehensive benchmark suite for Replay system."""

    def __init__(self, replay_file: str):
        self.replay_file = replay_file
        self.results: List[BenchmarkResult] = []

    def run_benchmark(self, name: str, func, *args, **kwargs) -> tuple[BenchmarkResult, Any | None]:
        """Run a single benchmark with timing and memory tracking."""
        result = BenchmarkResult(name)

        # Start memory tracking
        tracemalloc.start()
        result.memory_before = tracemalloc.get_traced_memory()[0]

        # Run benchmark
        start_time = time.perf_counter()
        try:
            func_result = func(*args, **kwargs)
            result.details['status'] = 'success'
        except Exception as e:
            result.details['status'] = 'failed'
            result.details['error'] = str(e)
            func_result = None

        end_time = time.perf_counter()
        result.duration = end_time - start_time

        # Capture memory usage
        current, peak = tracemalloc.get_traced_memory()
        result.memory_after = current
        result.memory_peak = peak
        tracemalloc.stop()

        self.results.append(result)
        return result, func_result

    def benchmark_load(self) -> Tuple[BenchmarkResult, Replay]:
        """Benchmark loading a replay file."""
        def load_replay():
            replay = Replay(self.replay_file, mode='r')
            replay.open()
            return replay

        result, replay = self.run_benchmark("Load Replay File", load_replay)

        if replay:
            # Get number of patches from database
            cursor = replay.db.conn.execute("SELECT COUNT(*) FROM patches")
            patch_count = cursor.fetchone()[0]

            result.operations = 1  # Opening is 1 operation
            result.details['timestamps'] = len(replay.get_timestamps())
            result.details['game_state_snapshots'] = len(replay.get_game_state_timestamps())
            result.details['total_patches_in_db'] = patch_count
            result.details['game_id'] = replay.game_id
            result.details['player_id'] = replay.player_id
            if replay.start_time:
                result.details['start_time'] = replay.start_time.isoformat()
            if replay.last_time:
                result.details['last_time'] = replay.last_time.isoformat()

        return result, replay

    def benchmark_forward_time_travel(self, replay: Replay) -> BenchmarkResult:
        """Benchmark sequential forward time travel through all timestamps."""
        timestamps = replay.get_timestamps()
        if not timestamps:
            result = BenchmarkResult("Forward Time Travel")
            result.details['status'] = 'skipped'
            result.details['reason'] = 'no timestamps'
            return result

        def forward_travel():
            current_ts = replay._start_time
            patch_count = 0

            for ts in timestamps:
                patches = replay._jump_from_to(current_ts, ts)
                patch_count += len(patches)
                current_ts = ts

            return patch_count

        result, patch_count = self.run_benchmark("Forward Time Travel", forward_travel)
        result.operations = len(timestamps)
        result.details['patches_applied'] = patch_count
        result.details['avg_patches_per_jump'] = patch_count / len(timestamps) if timestamps else 0

        return result

    def benchmark_backward_time_travel(self, replay: Replay) -> BenchmarkResult:
        """Benchmark sequential backward time travel through all timestamps."""
        timestamps = replay.get_timestamps()
        if not timestamps:
            result = BenchmarkResult("Backward Time Travel")
            result.details['status'] = 'skipped'
            result.details['reason'] = 'no timestamps'
            return result

        def backward_travel():
            current_ts = timestamps[-1] if timestamps else replay._start_time
            patch_count = 0

            for ts in reversed(timestamps[:-1]):
                patches = replay._jump_from_to(current_ts, ts)
                patch_count += len(patches)
                current_ts = ts

            # Jump back to start
            patches = replay._jump_from_to(current_ts, replay._start_time)
            patch_count += len(patches)

            return patch_count

        result, patch_count = self.run_benchmark("Backward Time Travel", backward_travel)
        result.operations = len(timestamps)
        result.details['patches_applied'] = patch_count
        result.details['avg_patches_per_jump'] = patch_count / len(timestamps) if timestamps else 0

        return result

    def benchmark_random_access(self, replay: Replay, num_jumps: int = 100) -> BenchmarkResult:
        """Benchmark random access to timestamps."""
        timestamps = replay.get_timestamps()
        if len(timestamps) < 2:
            result = BenchmarkResult("Random Access")
            result.details['status'] = 'skipped'
            result.details['reason'] = 'insufficient timestamps'
            return result

        import random

        def random_access():
            # Create random pairs of timestamps
            jump_pairs = []
            for _ in range(min(num_jumps, len(timestamps) * len(timestamps))):
                start = random.choice(timestamps)
                end = random.choice(timestamps)
                jump_pairs.append((start, end))

            patch_count = 0
            for start, end in jump_pairs:
                patches = replay._jump_from_to(start, end)
                patch_count += len(patches)

            return len(jump_pairs), patch_count

        result, (jumps, patch_count) = self.run_benchmark("Random Access", random_access)
        result.operations = jumps
        result.details['jumps'] = jumps
        result.details['patches_applied'] = patch_count
        result.details['avg_patches_per_jump'] = patch_count / jumps if jumps else 0

        return result

    def benchmark_patch_retrieval(self, replay: Replay, num_retrievals: int = 1000) -> BenchmarkResult:
        """Benchmark patch retrieval from database."""
        # Get patch keys from database
        cursor = replay.db.conn.execute("SELECT from_timestamp, to_timestamp FROM patches LIMIT ?", (num_retrievals,))
        patch_keys = cursor.fetchall()

        if not patch_keys:
            result = BenchmarkResult("Patch Retrieval")
            result.details['status'] = 'skipped'
            result.details['reason'] = 'no patches'
            return result

        import random

        def retrieve_patches():
            count = 0
            sample_size = min(num_retrievals, len(patch_keys))
            for _ in range(sample_size):
                key = random.choice(patch_keys)
                patch = replay.get_patch(key[0], key[1])
                if patch:
                    count += 1
            return count

        result, count = self.run_benchmark("Patch Retrieval", retrieve_patches)
        result.operations = count

        cursor = replay.db.conn.execute("SELECT COUNT(*) FROM patches")
        total_patches = cursor.fetchone()[0]
        result.details['total_patches'] = total_patches

        return result

    def benchmark_initial_state_load(self, replay: Replay, ritf) -> BenchmarkResult:
        """Benchmark loading the initial game state from disk."""
        def load_initial_state():
            return replay.load_initial_game_state(ritf)

        result, state = self.run_benchmark("Load Initial Game State", load_initial_state)
        result.operations = 1

        if state:
            result.details['state_size'] = len(str(state))

        return result

    def benchmark_static_map_data(self, replay: Replay, itf: GameInterface) -> BenchmarkResult:
        """Benchmark loading static map data."""
        def load_static_data():
            return replay.load_static_map_data(itf)

        result, data = self.run_benchmark("Load Static Map Data", load_static_data)
        result.operations = 1

        if data:
            result.details['data_size'] = len(str(data))

        return result

    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all benchmarks in sequence."""
        print(f"Starting benchmark suite for: {self.replay_file}")
        print(f"File size: {Path(self.replay_file).stat().st_size / (1024 * 1024):.2f} MB\n")
        ritf = ReplayInterface(self.replay_file)
        # Load replay
        load_result, replay = self.benchmark_load()
        print(load_result)

        if not replay or load_result.details.get('status') == 'failed':
            print("\nFailed to load replay. Stopping benchmarks.")
            return self.results

        try:
            # Run all benchmarks
            print(self.benchmark_initial_state_load(replay, ritf))
            print(self.benchmark_static_map_data(replay, ritf))
            print(self.benchmark_forward_time_travel(replay))
            print(self.benchmark_backward_time_travel(replay))
            print(self.benchmark_random_access(replay))
            print(self.benchmark_patch_retrieval(replay))

        finally:
            replay.close()

        # Print summary
        self.print_summary()

        return self.results

    def print_summary(self):
        """Print overall benchmark summary."""
        print(f"\n{'=' * 80}")
        print("BENCHMARK SUMMARY")
        print(f"{'=' * 80}")

        total_duration = sum(r.duration for r in self.results)
        successful = sum(1 for r in self.results if r.details.get('status') != 'failed')

        print(f"Total Benchmarks:  {len(self.results)}")
        print(f"Successful:        {successful}")
        print(f"Failed:            {len(self.results) - successful}")
        print(f"Total Time:        {total_duration:.4f} seconds")

        print(f"\n{'Benchmark':<40} {'Duration':<15} {'Ops/sec':<15}")
        print(f"{'-' * 40} {'-' * 15} {'-' * 15}")

        for result in self.results:
            if result.details.get('status') != 'skipped':
                print(f"{result.name:<40} {result.duration:<15.4f} {result.ops_per_second:<15.2f}")

        print(f"{'=' * 80}\n")


def main():
    """Main entry point for the benchmark."""
    parser = argparse.ArgumentParser(
        description='Benchmark replay file performance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python replay_benchmark.py ../examples/replay.db
  python replay_benchmark.py C:\\path\\to\\replay.db
        """
    )
    parser.add_argument(
        'replay_file',
        help='Path to the replay database file (.db)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run a quick benchmark with fewer iterations'
    )

    args = parser.parse_args()

    # Check if file exists
    if not Path(args.replay_file).exists():
        print(f"Error: Replay file not found: {args.replay_file}", file=sys.stderr)
        return 1

    # Run benchmarks
    benchmark = ReplayBenchmark(args.replay_file)
    benchmark.run_all_benchmarks()

    return 0


if __name__ == "__main__":
    sys.exit(main())

