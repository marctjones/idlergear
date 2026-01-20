"""Performance benchmark for FileRegistry."""

import tempfile
import time
from pathlib import Path

from idlergear.file_registry import FileRegistry, FileStatus


def benchmark_status_lookups():
    """Benchmark status lookups with caching."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Register 100 files
        for i in range(100):
            registry.register_file(f"file_{i}.py", FileStatus.CURRENT)

        # Add some patterns
        registry.add_pattern("*.bak", FileStatus.DEPRECATED)
        registry.add_pattern("archive/**/*", FileStatus.ARCHIVED)
        registry.add_pattern("tmp_*.txt", FileStatus.PROBLEMATIC)

        # Benchmark: First lookup (cold cache)
        start = time.perf_counter()
        for i in range(1000):
            registry.get_status(f"file_{i % 100}.py")
        cold_time = time.perf_counter() - start

        # Clear cache to test warm lookup
        registry._clear_cache()

        # Benchmark: Warm cache
        start = time.perf_counter()
        # First pass populates cache
        for i in range(100):
            registry.get_status(f"file_{i}.py")
        populate_time = time.perf_counter() - start

        # Second pass uses cache
        start = time.perf_counter()
        for i in range(1000):
            registry.get_status(f"file_{i % 100}.py")
        warm_time = time.perf_counter() - start

        print(f"\nStatus Lookup Benchmark (1000 lookups):")
        print(f"  Cold cache: {cold_time*1000:.2f}ms ({cold_time*1000/1000:.4f}ms per lookup)")
        print(f"  Cache populate (100): {populate_time*1000:.2f}ms")
        print(f"  Warm cache: {warm_time*1000:.2f}ms ({warm_time*1000/1000:.4f}ms per lookup)")
        print(f"  Speedup: {cold_time/warm_time:.1f}x faster")

        # Verify overhead is < 10ms per 1000 lookups
        assert warm_time * 1000 < 10, f"Overhead {warm_time*1000:.2f}ms exceeds 10ms target"
        print(f"  ✓ Overhead {warm_time*1000:.2f}ms < 10ms target")


def benchmark_pattern_matching():
    """Benchmark pattern matching with regex caching."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        # Add patterns
        registry.add_pattern("*.bak", FileStatus.DEPRECATED)
        registry.add_pattern("archive/**/*", FileStatus.ARCHIVED)
        registry.add_pattern("src/**/*.py", FileStatus.CURRENT)

        # Benchmark pattern matching
        test_paths = [
            "file.bak",
            "dir/file.bak",
            "archive/old.csv",
            "archive/deep/path/data.json",
            "src/module.py",
            "src/subdir/test.py",
            "unknown.txt",
        ]

        start = time.perf_counter()
        for _ in range(1000):
            for path in test_paths:
                registry.get_status(path)
        elapsed = time.perf_counter() - start

        print(f"\nPattern Matching Benchmark (7000 pattern matches):")
        print(f"  Total time: {elapsed*1000:.2f}ms")
        print(f"  Per match: {elapsed*1000/7000:.4f}ms")

        # Verify overhead
        assert elapsed * 1000 < 50, f"Pattern matching {elapsed*1000:.2f}ms too slow"
        print(f"  ✓ Overhead {elapsed*1000:.2f}ms acceptable")


def benchmark_mixed_operations():
    """Benchmark mixed read/write operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path)

        start = time.perf_counter()

        # Mixed operations
        for i in range(50):
            registry.register_file(f"file_{i}.py", FileStatus.CURRENT)
            registry.get_status(f"file_{i}.py")

        for i in range(10):
            registry.deprecate_file(f"file_{i}.py", successor=f"file_v2_{i}.py")

        for i in range(50):
            registry.get_status(f"file_{i}.py")

        elapsed = time.perf_counter() - start

        print(f"\nMixed Operations Benchmark:")
        print(f"  50 registers + 10 deprecates + 50 lookups: {elapsed*1000:.2f}ms")
        print(f"  Per operation: {elapsed*1000/110:.4f}ms")


if __name__ == "__main__":
    print("="*60)
    print("FileRegistry Performance Benchmark")
    print("="*60)

    benchmark_status_lookups()
    benchmark_pattern_matching()
    benchmark_mixed_operations()

    print("\n" + "="*60)
    print("All benchmarks passed! ✓")
    print("="*60)
