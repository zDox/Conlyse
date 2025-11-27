import random
import time
from dataclasses import dataclass
from typing import List
import statistics

from conflict_interface.interface.replay_interface import ReplayInterface
from paths import TEST_DATA
from tools.recording_converter import RecordingConverter
from tools.recording_converter.enums import OperatingMode


@dataclass
class BenchmarkMetrics:
    """Stores metrics for a single benchmark run"""
    duration_ms: float
    patches_applied: int
    operations_applied: int
    ops_per_second: float
    ops_per_patch: float
    patches_per_second: float


@dataclass
class BenchmarkResults:
    """Aggregated results for multiple benchmark runs"""
    test_name: str
    iterations: int
    metrics: List[BenchmarkMetrics]

    @property
    def avg_duration_ms(self) -> float:
        return statistics.mean(m.duration_ms for m in self.metrics)

    @property
    def avg_ops_per_second(self) -> float:
        return statistics.mean(m.ops_per_second for m in self.metrics)

    @property
    def avg_patches_per_second(self) -> float:
        return statistics.mean(m.patches_per_second for m in self.metrics)

    @property
    def avg_ops_per_patch(self) -> float:
        return statistics.mean(m.ops_per_patch for m in self.metrics)

    @property
    def median_duration_ms(self) -> float:
        return statistics.median(m.duration_ms for m in self.metrics)

    @property
    def std_duration_ms(self) -> float:
        return statistics.stdev(m.duration_ms for m in self.metrics) if len(self.metrics) > 1 else 0.0

    @property
    def min_duration_ms(self) -> float:
        return min(m.duration_ms for m in self.metrics)

    @property
    def max_duration_ms(self) -> float:
        return max(m.duration_ms for m in self.metrics)


class ReplayBenchmark:
    def __init__(self):
        self.replay_interface: ReplayInterface | None = None
        self.recording_file_path = TEST_DATA / "test_recording"
        self.results: List[BenchmarkResults] = []

    def set_up(self):
        self.start_converter()
        self.replay_interface = ReplayInterface(TEST_DATA / "test_replay.bin")
        self.replay_interface.open()

    def start_converter(self):
        # Create converter for replay conversion (gmr mode)
        converter = RecordingConverter(
            self.recording_file_path,
            OperatingMode.rur
        )

        # Convert to replay
        success = converter.convert(
            output=TEST_DATA / "test_replay.bin",
            overwrite=True,
            game_id=1,  # optional
            player_id=1,  # optional
        )

        assert success

    def tear_down(self):
        # close
        self.replay_interface.close()

    def run_test(self):
        print("\n" + "=" * 80)
        print("REPLAY BENCHMARK SUITE")
        print("=" * 80 + "\n")

        self.test_next_patch()
        self.test_random_jump()

        self.print_summary()

    def test_next_patch(self, iterations=10):
        print(f"Running Next Patch Test ({iterations} iterations)...")
        metrics_list = []

        for i in range(iterations):
            self.replay_interface.jump_to(self.get_random_timestamp())
            self.replay_interface.replay.reset_op_counter()

            patches_applied = 0
            start_time = time.perf_counter()

            while self.replay_interface.jump_to_next_patch():
                patches_applied += 1

            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000

            operations_applied = self.replay_interface.replay.get_op_counter()

            # Calculate metrics
            ops_per_second = (operations_applied / duration_ms * 1000) if duration_ms > 0 else 0
            ops_per_patch = operations_applied / patches_applied if patches_applied > 0 else 0
            patches_per_second = (patches_applied / duration_ms * 1000) if duration_ms > 0 else 0

            metrics = BenchmarkMetrics(
                duration_ms=duration_ms,
                patches_applied=patches_applied,
                operations_applied=operations_applied,
                ops_per_second=ops_per_second,
                ops_per_patch=ops_per_patch,
                patches_per_second=patches_per_second
            )
            metrics_list.append(metrics)

            print(f"  Iteration {i + 1}/{iterations}: {duration_ms:.2f}ms, "
                  f"{patches_applied} patches, {operations_applied} ops")

        results = BenchmarkResults("Next Patch Test", iterations, metrics_list)
        self.results.append(results)
        self.print_results(results)

    def test_random_jump(self, iterations=10):
        print(f"\nRunning Random Jump Test ({iterations} iterations)...")
        metrics_list = []

        for i in range(iterations):
            self.replay_interface.replay.reset_op_counter()
            random_ts = self.get_random_timestamp()
            patches_applied = len(
                self.replay_interface.replay.storage.patch_graph.find_patch_path(
                    self.replay_interface.last_patch_time, random_ts
                )
            )

            start_time = time.perf_counter()
            self.replay_interface.jump_to(random_ts)
            end_time = time.perf_counter()

            duration_ms = (end_time - start_time) * 1000
            operations_applied = self.replay_interface.replay.get_op_counter()

            # Calculate metrics
            ops_per_second = (operations_applied / duration_ms * 1000) if duration_ms > 0 else 0
            ops_per_patch = operations_applied / patches_applied if patches_applied > 0 else 0
            patches_per_second = (patches_applied / duration_ms * 1000) if duration_ms > 0 else 0

            metrics = BenchmarkMetrics(
                duration_ms=duration_ms,
                patches_applied=patches_applied,
                operations_applied=operations_applied,
                ops_per_second=ops_per_second,
                ops_per_patch=ops_per_patch,
                patches_per_second=patches_per_second
            )
            metrics_list.append(metrics)

            print(f"  Iteration {i + 1}/{iterations}: {duration_ms:.2f}ms, "
                  f"{patches_applied} patches, {operations_applied} ops")

        results = BenchmarkResults("Random Jump Test", iterations, metrics_list)
        self.results.append(results)
        self.print_results(results)

    def print_results(self, results: BenchmarkResults):
        print(f"\n{results.test_name} Results:")
        print("-" * 60)
        print(f"  Iterations:              {results.iterations}")
        print(f"  Average Duration:        {results.avg_duration_ms:.2f} ms")
        print(f"  Median Duration:         {results.median_duration_ms:.2f} ms")
        print(f"  Std Deviation:           {results.std_duration_ms:.2f} ms")
        print(f"  Min Duration:            {results.min_duration_ms:.2f} ms")
        print(f"  Max Duration:            {results.max_duration_ms:.2f} ms")
        print(f"  Avg Ops/Second:          {results.avg_ops_per_second:,.0f}")
        print(f"  Avg Patches/Second:      {results.avg_patches_per_second:.1f}")
        print(f"  Avg Ops/Patch:           {results.avg_ops_per_patch:.1f}")
        print("-" * 60)

    def print_summary(self):
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        for results in self.results:
            print(f"\n{results.test_name}:")
            print(f"  ⏱️  Average: {results.avg_duration_ms:.2f} ms "
                  f"(min: {results.min_duration_ms:.2f}, max: {results.max_duration_ms:.2f})")
            print(f"  ⚡ Throughput: {results.avg_ops_per_second:,.0f} ops/sec, "
                  f"{results.avg_patches_per_second:.1f} patches/sec")
            print(f"  📊 Efficiency: {results.avg_ops_per_patch:.1f} ops/patch")

        print("\n" + "=" * 80 + "\n")

    def get_random_timestamp(self):
        return random.choice(self.replay_interface.get_timestamps())

if __name__ == "__main__":
    b = ReplayBenchmark()
    b.set_up()
    b.run_test()
    b.print_summary()