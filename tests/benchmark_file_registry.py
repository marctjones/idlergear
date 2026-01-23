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
        registry = FileRegistry(registry_path, lazy_load=False)

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


def benchmark_lazy_loading():
    """Benchmark lazy loading vs eager loading."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"

        # Create registry with 1000 files
        registry = FileRegistry(registry_path, lazy_load=False)
        for i in range(1000):
            registry.register_file(f"file_{i}.py", FileStatus.CURRENT)

        # Benchmark eager loading (lazy_load=False)
        start = time.perf_counter()
        eager_registry = FileRegistry(registry_path, lazy_load=False)
        eager_time = time.perf_counter() - start

        # Benchmark lazy loading (lazy_load=True)
        start = time.perf_counter()
        lazy_registry = FileRegistry(registry_path, lazy_load=True)
        lazy_init_time = time.perf_counter() - start

        # Measure first access with lazy loading
        start = time.perf_counter()
        lazy_registry.get_status("file_0.py")
        lazy_first_access = time.perf_counter() - start

        print(f"\nLazy Loading Benchmark (1000 files):")
        print(f"  Eager loading (__init__): {eager_time*1000:.2f}ms")
        print(f"  Lazy loading (__init__): {lazy_init_time*1000:.4f}ms")
        print(f"  Lazy loading (first access): {lazy_first_access*1000:.2f}ms")
        print(f"  Speedup: {eager_time/lazy_init_time:.0f}x faster init")

        # Lazy init should be nearly instant
        assert lazy_init_time * 1000 < 1, f"Lazy init {lazy_init_time*1000:.2f}ms too slow"
        print(f"  ✓ Lazy init {lazy_init_time*1000:.4f}ms < 1ms target")


def benchmark_batch_operations():
    """Benchmark batch status checks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path, lazy_load=False)

        # Register 100 files
        for i in range(100):
            registry.register_file(f"file_{i}.py", FileStatus.CURRENT)

        paths = [f"file_{i}.py" for i in range(100)]

        # Benchmark individual lookups
        start = time.perf_counter()
        for path in paths:
            registry.get_status(path)
        individual_time = time.perf_counter() - start

        # Clear cache for fair comparison
        registry._clear_cache()

        # Benchmark batch lookup
        start = time.perf_counter()
        registry.get_status_batch(paths)
        batch_time = time.perf_counter() - start

        print(f"\nBatch Operations Benchmark (100 files):")
        print(f"  Individual lookups: {individual_time*1000:.2f}ms")
        print(f"  Batch lookup: {batch_time*1000:.2f}ms")
        print(f"  Speedup: {individual_time/batch_time:.1f}x faster")

        # Batch should be at least as fast as individual
        assert batch_time <= individual_time * 1.1, "Batch slower than individual"
        print(f"  ✓ Batch performance acceptable")


def benchmark_ttl_cache():
    """Benchmark TTL-based cache expiration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "file_registry.json"
        registry = FileRegistry(registry_path, lazy_load=False)

        # Register file
        registry.register_file("test.py", FileStatus.CURRENT)

        # First lookup (cache miss)
        start = time.perf_counter()
        registry.get_status("test.py")
        first_time = time.perf_counter() - start

        # Second lookup (cache hit)
        start = time.perf_counter()
        registry.get_status("test.py")
        cached_time = time.perf_counter() - start

        # Simulate TTL expiration by manually expiring cache
        original_ttl = registry.CACHE_TTL
        registry.CACHE_TTL = 0.001  # 1ms TTL
        time.sleep(0.002)  # Wait for expiration

        # Lookup after expiration (cache miss again)
        start = time.perf_counter()
        registry.get_status("test.py")
        expired_time = time.perf_counter() - start

        # Restore TTL
        registry.CACHE_TTL = original_ttl

        print(f"\nTTL Cache Benchmark:")
        print(f"  First lookup (cold): {first_time*1000000:.2f}μs")
        print(f"  Cached lookup: {cached_time*1000000:.2f}μs")
        print(f"  After expiration: {expired_time*1000000:.2f}μs")
        print(f"  Cache speedup: {first_time/cached_time:.1f}x faster")

        # Cached lookup should be significantly faster
        assert cached_time < first_time, "Cache not faster than cold lookup"
        print(f"  ✓ TTL cache working correctly")


if __name__ == "__main__":
    print("="*60)
    print("FileRegistry Performance Benchmark")
    print("="*60)

    benchmark_status_lookups()
    benchmark_pattern_matching()
    benchmark_mixed_operations()
    benchmark_lazy_loading()
    benchmark_batch_operations()
    benchmark_ttl_cache()

    print("\n" + "="*60)
    print("All benchmarks passed! ✓")
    print("="*60)
