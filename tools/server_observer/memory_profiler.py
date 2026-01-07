"""
Memory profiling utilities for ServerObserver.
"""
import gc
import sys
import time
import tracemalloc
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import psutil

EXCLUDED_MODULE_PREFIXES = (
    "sys",
    "importlib",
    "types",
    "typing",
    "inspect",
    "ast",
    "enum",
    "numpy",
    "matplotlib",
    "lxml",
)

class MemoryProfiler:
    """
    Profile memory usage with multiple approaches.
    """

    def __init__(self, enable_tracemalloc: bool = True):
        self.process = psutil.Process()
        self.enable_tracemalloc = enable_tracemalloc
        self.snapshots = []
        self._rss_baseline = None

        if enable_tracemalloc:
            tracemalloc.start()

    def reset_tracemalloc_baseline(self):
        """
        Reset tracemalloc so future snapshots exclude import-time allocations.
        """
        if not self.enable_tracemalloc:
            return
        tracemalloc.clear_traces()

    def set_rss_baseline(self):
        """Freeze current RSS as baseline (e.g. after imports)."""
        self._rss_baseline = self.get_process_memory_mb()

    def get_relative_rss_mb(self) -> float:
        """RSS delta relative to baseline."""
        if self._rss_baseline is None:
            return 0.0
        return self.get_process_memory_mb() - self._rss_baseline

    def get_process_memory_mb(self) -> float:
        """Get current process memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024

    def get_memory_breakdown(self) -> Dict[str, float]:
        """Get detailed memory breakdown."""
        mem_info = self.process.memory_info()
        return {
            "rss_mb": mem_info.rss / 1024 / 1024,  # Resident Set Size (actual RAM usage)
            "vms_mb": mem_info.vms / 1024 / 1024,  # Virtual Memory Size
            "percent": self.process.memory_percent(),
        }

    def take_snapshot(self, label: str = None):
        """Take a tracemalloc snapshot."""
        if not self.enable_tracemalloc:
            return

        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append((label or f"snapshot_{len(self.snapshots)}", snapshot))

    def compare_snapshots(self, idx1: int = -2, idx2: int = -1) -> List[Tuple[str, int, int]]:
        """
        Compare two snapshots and return top memory differences.

        Returns:
            List of (filename:lineno, size_diff_kb, count_diff)
        """
        if len(self.snapshots) < 2:
            return []

        label1, snap1 = self.snapshots[idx1]
        label2, snap2 = self.snapshots[idx2]

        top_stats = snap2.compare_to(snap1, 'lineno')

        results = []
        for stat in top_stats[:20]:  # Top 20 differences
            results.append((
                f"{stat.traceback.format()[0]}",
                stat.size_diff / 1024,  # KB
                stat.count_diff
            ))

        return results

    def print_snapshot_comparison(self, idx1: int = -2, idx2: int = -1):
        """Print comparison between two snapshots."""
        if len(self.snapshots) < 2:
            print("Need at least 2 snapshots to compare")
            return

        label1, _ = self.snapshots[idx1]
        label2, _ = self.snapshots[idx2]

        print(f"\n{'=' * 80}")
        print(f"Memory difference: {label1} -> {label2}")
        print(f"{'=' * 80}")

        results = self.compare_snapshots(idx1, idx2)
        for location, size_diff_kb, count_diff in results:
            if abs(size_diff_kb) < 1:  # Skip tiny differences
                continue
            sign = "+" if size_diff_kb > 0 else ""
            print(f"{sign}{size_diff_kb:>10.1f} KB | {sign}{count_diff:>6} blocks | {location}")

    def get_top_memory_objects(self, limit: int = 20) -> List[Tuple[str, int, int]]:
        """
        Get the top memory-consuming objects by type.

        Returns:
            List of (type_name, count, total_size_kb)
        """
        gc.collect()

        type_stats = defaultdict(lambda: {"count": 0, "size": 0})

        for obj in gc.get_objects():
            try:
                obj_type = type(obj)
                module = getattr(obj_type, "__module__", "")
                if module.startswith(EXCLUDED_MODULE_PREFIXES):
                    continue

                size = sys.getsizeof(obj)
                name = obj_type.__name__
                type_stats[name]["count"] += 1
                type_stats[name]["size"] += size
            except Exception:
                continue

        # Sort by total size
        sorted_stats = sorted(
            type_stats.items(),
            key=lambda x: x[1]["size"],
            reverse=True
        )

        return [
            (name, stats["count"], stats["size"] / 1024)
            for name, stats in sorted_stats[:limit]
        ]

    def print_top_objects(self, limit: int = 20):
        """Print the top memory-consuming object types."""
        print(f"\n{'=' * 80}")
        print(f"Top {limit} Memory-Consuming Object Types")
        print(f"{'=' * 80}")
        print(f"{'Type':<30} {'Count':>10} {'Total KB':>15}")
        print(f"{'-' * 80}")

        for obj_type, count, size_kb in self.get_top_memory_objects(limit):
            print(f"{obj_type:<30} {count:>10,} {size_kb:>15,.1f}")

    def get_large_objects(self, min_size_kb: float = 100) -> List[Tuple[str, float, str]]:
        """
        Find individual large objects.

        Returns:
            List of (type_name, size_kb, repr_string)
        """
        gc.collect()
        large_objects = []

        for obj in gc.get_objects():
            try:
                module = getattr(type(obj), "__module__", "")
                if module.startswith(EXCLUDED_MODULE_PREFIXES):
                    continue
                size = sys.getsizeof(obj)
                if size / 1024 >= min_size_kb:
                    obj_type = type(obj).__name__
                    obj_repr = repr(obj)[:100]  # Truncate repr
                    large_objects.append((obj_type, size / 1024, obj_repr))
            except:
                continue

        # Sort by size
        large_objects.sort(key=lambda x: x[1], reverse=True)
        return large_objects[:50]  # Top 50

    def print_large_objects(self, min_size_kb: float = 1):
        """Print individual large objects."""
        print(f"\n{'=' * 80}")
        print(f"Large Objects (>{min_size_kb} KB each)")
        print(f"{'=' * 80}")
        print(f"{'Type':<30} {'Size KB':>15} {'Preview':<30}")
        print(f"{'-' * 80}")

        for obj_type, size_kb, obj_repr in self.get_large_objects(min_size_kb):
            print(f"{obj_type:<30} {size_kb:>15,.1f} {obj_repr:<30}")

    def get_tracemalloc_top(self, limit: int = 20) -> List[Tuple[str, float]]:
        """Get top memory allocations from tracemalloc."""
        if not self.enable_tracemalloc:
            return []

        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')

        return [
            (str(stat), stat.size / 1024)
            for stat in top_stats[:limit]
        ]

    def print_tracemalloc_top(self, limit: int = 20):
        """Print top memory allocations."""
        print(f"\n{'=' * 80}")
        print(f"Top {limit} Memory Allocations (tracemalloc)")
        print(f"{'=' * 80}")

        for location, size_kb in self.get_tracemalloc_top(limit):
            print(f"{size_kb:>10,.1f} KB | {location}")

    def full_report(self):
        """Print a comprehensive memory report."""
        print("\n" + "=" * 80)
        print("MEMORY PROFILER REPORT")
        print("=" * 80)

        # Overall stats
        mem = self.get_memory_breakdown()
        print(f"\nProcess Memory:")
        print(f"  RSS (Actual RAM): {mem['rss_mb']:.1f} MB")
        print(f"  RSS (delta): {self.get_relative_rss_mb():+.1f} MB")
        print(f"  VMS (Virtual):    {mem['vms_mb']:.1f} MB")
        print(f"  Percent of RAM:   {mem['percent']:.1f}%")

        # Top object types
        self.print_top_objects(20)

        # Large individual objects
        self.print_large_objects(1)

        # Tracemalloc info
        if self.enable_tracemalloc:
            self.print_tracemalloc_top(20)

    def stop(self):
        """Stop tracemalloc."""
        if self.enable_tracemalloc:
            tracemalloc.stop()


def profile_function(func):
    """Decorator to profile a function's memory usage."""

    def wrapper(*args, **kwargs):
        profiler = MemoryProfiler(enable_tracemalloc=True)

        mem_before = profiler.get_process_memory_mb()
        profiler.take_snapshot(f"before_{func.__name__}")

        result = func(*args, **kwargs)

        profiler.take_snapshot(f"after_{func.__name__}")
        mem_after = profiler.get_process_memory_mb()

        print(f"\n{'=' * 80}")
        print(f"Memory Profile: {func.__name__}")
        print(f"{'=' * 80}")
        print(f"Memory before: {mem_before:.1f} MB")
        print(f"Memory after:  {mem_after:.1f} MB")
        print(f"Difference:    {mem_after - mem_before:+.1f} MB")

        profiler.print_snapshot_comparison()
        profiler.stop()

        return result

    return wrapper


# Integration with ServerObserver
class MonitoredServerObserver:
    """
    Wrapper to add memory monitoring to ServerObserver.
    """

    def __init__(self, observer, report_interval: int = 10):
        self.observer = observer
        self.profiler = MemoryProfiler(enable_tracemalloc=True)  # Low overhead
        self.report_interval = report_interval
        self.iteration_count = 0
        self.memory_history = []

    def _check_memory(self):
        """Check and log memory usage."""
        mem = self.profiler.get_memory_breakdown()
        self.memory_history.append(mem)

        print(f"\n[Memory Check - Iteration {self.iteration_count}]")
        print(f"  RSS: {mem['rss_mb']:.1f} MB")
        print(f"  Running games: {len(self.observer._running_game_ids)}")
        print(f"  Known games: {len(self.observer._known_games)}")

        if len(self.memory_history) > 1:
            prev = self.memory_history[-2]
            diff = mem['rss_mb'] - prev['rss_mb']
            print(f"  Change: {diff:+.1f} MB")

            if diff > 50:  # Significant increase
                print(f"  ⚠️  WARNING: Large memory increase detected!")

    def run(self, iterations: int = None):
        """Run with memory monitoring."""
        # Initial snapshot
        print("Starting memory monitoring...")
        self.profiler.take_snapshot("start")
        self.profiler.set_rss_baseline()
        self.profiler.reset_tracemalloc_baseline()

        # Monkey-patch the observer's run cycle
        original_process_finished = self.observer._process_finished

        def monitored_process_finished():
            original_process_finished()
            self.iteration_count += 1

            if self.iteration_count % self.report_interval == 0:
                self._check_memory()

        self.observer._process_finished = monitored_process_finished

        try:
            return self.observer.run(iterations)
        finally:
            print("\n" + "=" * 80)
            print("FINAL MEMORY REPORT")
            print("=" * 80)
            self.profiler.full_report()

            # Memory history
            if len(self.memory_history) > 1:
                print(f"\nMemory History:")
                print(f"  Start:  {self.memory_history[0]['rss_mb']:.1f} MB")
                print(f"  End:    {self.memory_history[-1]['rss_mb']:.1f} MB")
                print(f"  Change: {self.memory_history[-1]['rss_mb'] - self.memory_history[0]['rss_mb']:+.1f} MB")
                print(f"  Peak:   {max(m['rss_mb'] for m in self.memory_history):.1f} MB")

