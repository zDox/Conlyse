"""
Performance benchmark for Replay system.

This benchmark tests various performance aspects of the replay system:
- Loading time and memory usage
- Calculate patches (forward, backward, and random time travel)
- Client time operations (set_client_time benchmark)

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
from typing import Any, List, Tuple
from datetime import datetime, timezone

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
            f"Duration: {self.duration:.4f} seconds",
            f"Operations: {self.operations}",
            f"Ops/sec: {self.ops_per_second:.2f}",
            f"Memory Before: {self.format_size(self.memory_before)}",
            f"Memory After: {self.format_size(self.memory_after)}",
            f"Memory Delta: {self.format_size(self.memory_delta)}",
            f"Memory Peak: {self.format_size(self.memory_peak)}",
        ]

        if self.operations > 0:
            time_per_op = (self.duration / self.operations) * 1000
            lines.append(f"Time/operation: {time_per_op:.4f} ms")

        if self.details:
            lines.append("\nDetails:")
            for key, value in self.details.items():
                lines.append(f"  {key}: {value}")

        return '\n'.join(lines)


class ReplayBenchmark:
    """Comprehensive benchmark suite for Replay system."""

    def __init__(self, replay_file: str, quick_mode: bool = False):
        self.replay_file = replay_file
        self.quick_mode = quick_mode
        self.results: List[BenchmarkResult] = []

    def run_benchmark(self, name: str, func, *args, **kwargs) -> Tuple[BenchmarkResult, Any]:
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

    def benchmark_calculate_patches(self, replay: Replay) -> BenchmarkResult:
        """Benchmark patch calculation: forward, backward, and random time travel."""
        timestamps = replay.get_timestamps()

        if len(timestamps) < 2:
            result = BenchmarkResult("Calculate Patches")
            result.details['status'] = 'skipped'
            result.details['reason'] = 'insufficient timestamps'
            return result

        import random

        def calculate_patches():
            stats = {
                'forward_patches': 0,
                'backward_patches': 0,
                'random_patches': 0,
                'forward_jumps': 0,
                'backward_jumps': 0,
                'random_jumps': 0
            }

            # Forward time travel
            current_ts = replay._start_time
            for ts in timestamps:
                patches = replay._find_patch_path(current_ts, ts)
                stats['forward_patches'] += len(patches)
                stats['forward_jumps'] += 1
                current_ts = ts

            # Backward time travel
            current_ts = timestamps[-1] if timestamps else replay._start_time
            for ts in reversed(timestamps[:-1]):
                patches = replay._find_patch_path(current_ts, ts)
                stats['backward_patches'] += len(patches)
                stats['backward_jumps'] += 1
                current_ts = ts

            # Jump back to start
            patches = replay._find_patch_path(current_ts, replay._start_time)
            stats['backward_patches'] += len(patches)
            stats['backward_jumps'] += 1

            # Random access
            num_random_jumps = 100 if self.quick_mode else 1000
            num_random_jumps = min(num_random_jumps, len(timestamps) * 10)

            for _ in range(num_random_jumps):
                start = random.choice(timestamps)
                end = random.choice(timestamps)
                patches = replay._find_patch_path(start, end)
                stats['random_patches'] += len(patches)
                stats['random_jumps'] += 1

            return stats

        result, stats = self.run_benchmark("Calculate Patches", calculate_patches)

        if stats:
            total_jumps = stats['forward_jumps'] + stats['backward_jumps'] + stats['random_jumps']
            total_patches = stats['forward_patches'] + stats['backward_patches'] + stats['random_patches']

            result.operations = total_jumps
            result.details['total_patches_calculated'] = total_patches
            result.details['total_jumps'] = total_jumps
            result.details['avg_patches_per_jump'] = total_patches / total_jumps if total_jumps else 0
            result.details['forward_jumps'] = stats['forward_jumps']
            result.details['forward_patches'] = stats['forward_patches']
            result.details['backward_jumps'] = stats['backward_jumps']
            result.details['backward_patches'] = stats['backward_patches']
            result.details['random_jumps'] = stats['random_jumps']
            result.details['random_patches'] = stats['random_patches']

        return result

    def benchmark_client_time(self, replay: Replay, ritf: ReplayInterface) -> BenchmarkResult:
        """Benchmark set_client_time operations."""
        timestamps = replay.get_timestamps()

        if len(timestamps) < 2:
            result = BenchmarkResult("Client Time Operations")
            result.details['status'] = 'skipped'
            result.details['reason'] = 'insufficient timestamps'
            return result

        import random

        def client_time_ops():
            stats = {
                'set_time_calls': 0,
                'forward_moves': 0,
                'backward_moves': 0,
                'random_moves': 0
            }

            # Forward sequential moves
            for ts in timestamps:
                dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
                ritf.jump_to(dt)
                stats['set_time_calls'] += 1
                stats['forward_moves'] += 1

            # Backward sequential moves
            for ts in reversed(timestamps):
                dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
                ritf.jump_to(dt)
                stats['set_time_calls'] += 1
                stats['backward_moves'] += 1

            # Random moves
            num_random = 50 if self.quick_mode else len(timestamps)//2
            num_random = min(num_random, len(timestamps))

            for _ in range(num_random):
                ts = random.choice(timestamps)
                dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
                ritf.jump_to(dt)
                stats['set_time_calls'] += 1
                stats['random_moves'] += 1

            return stats

        result, stats = self.run_benchmark("Client Time Operations", client_time_ops)

        if stats:
            result.operations = stats['set_time_calls']
            result.details['total_set_time_calls'] = stats['set_time_calls']
            result.details['forward_moves'] = stats['forward_moves']
            result.details['backward_moves'] = stats['backward_moves']
            result.details['random_moves'] = stats['random_moves']

        return result

    def benchmark_initial_state_load(self, replay: Replay) -> BenchmarkResult:
        """Benchmark loading the initial game state from disk."""
        def load_initial_state():
            return replay.load_initial_game_state()

        result, state = self.run_benchmark("Load Initial Game State", load_initial_state)
        result.operations = 1

        if state:
            result.details['state_size'] = len(str(state))

        return result

    def benchmark_static_map_data(self, replay: Replay) -> BenchmarkResult:
        """Benchmark loading static map data."""
        def load_static_data():
            return replay.load_static_map_data()

        result, data = self.run_benchmark("Load Static Map Data", load_static_data)
        result.operations = 1

        if data:
            result.details['data_size'] = len(str(data))

        return result

    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all benchmarks in sequence."""
        print(f"Starting benchmark suite for: {self.replay_file}")
        print(f"File size: {Path(self.replay_file).stat().st_size / (1024 * 1024):.2f} MB")
        print(f"Mode: {'Quick' if self.quick_mode else 'Full'}\n")

        ritf = ReplayInterface(self.replay_file)
        ritf.open()

        # Load replay
        load_result, replay = self.benchmark_load()
        print(load_result)

        if not replay or load_result.details.get('status') == 'failed':
            print("\nFailed to load replay. Stopping benchmarks.")
            return self.results

        try:
            # Run all benchmarks
            print(self.benchmark_initial_state_load(replay))
            print(self.benchmark_static_map_data(replay))
            print(self.benchmark_calculate_patches(replay))
            print(self.benchmark_client_time(replay, ritf))
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

        print(f"Total Benchmarks: {len(self.results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {len(self.results) - successful}")
        print(f"Total Time: {total_duration:.4f} seconds")

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
    python replay_benchmark.py replay.db --quick
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
    benchmark = ReplayBenchmark(args.replay_file, quick_mode=args.quick)
    benchmark.run_all_benchmarks()

    return 0


if __name__ == "__main__":
    sys.exit(main())