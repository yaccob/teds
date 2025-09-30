#!/usr/bin/env python3
"""
Performance benchmark for optimized TeDS cache system.

This script measures the improved cache performance with:
1. Preemptive multi-pointer caching
2. Direct pointer access optimization
3. Reduced dependency tracking overhead
"""

import json
import statistics
import time
from pathlib import Path

from teds_core.cache import TedsSchemaCache
from teds_core.refs import (
    build_validator_for_ref,
    collect_examples,
    resolve_schema_node,
)


class OptimizedCacheBenchmark:
    def __init__(self):
        self.demo_dir = Path(__file__).parent / "demo"
        self.sample_schema = self.demo_dir / "sample_schemas.yaml"
        self.public_schema = self.demo_dir / "public_schemas.yaml"

        # Common schema pointers to test
        self.test_pointers = [
            "#/components/schemas/User",
            "#/components/schemas/Email",
            "#/components/schemas/Product",
            "#/components/schemas/Tag",
            "#/components/schemas/Contact",
            "#/components/schemas/OrderLine",
        ]

        self.results = {}

    def benchmark_optimized_cache(self, iterations: int = 100) -> dict[str, float]:
        """Benchmark optimized cache implementation."""
        print(
            f"\n=== Optimized Cache Implementation Benchmark ({iterations} iterations) ==="
        )

        # Clear cache first
        with TedsSchemaCache() as cache:
            cache.clear()

        durations = {
            "first_access": [],
            "subsequent_same": [],
            "subsequent_different": [],
            "validator_build": [],
            "examples_collect": [],
        }

        for i in range(iterations):
            if i % 20 == 0:
                print(f"Iteration {i+1}/{iterations}")

            # Test first access (triggers preemptive caching)
            with TedsSchemaCache() as cache:
                cache.clear()
                start = time.perf_counter()
                schema, _ = resolve_schema_node(
                    self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
                )
                end = time.perf_counter()
                durations["first_access"].append(end - start)

                # Test subsequent access to same pointer (should be cache hit)
                start = time.perf_counter()
                schema, _ = resolve_schema_node(
                    self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
                )
                end = time.perf_counter()
                durations["subsequent_same"].append(end - start)

                # Test access to different pointer (should benefit from preemptive caching)
                start = time.perf_counter()
                schema, _ = resolve_schema_node(
                    self.demo_dir, f"sample_schemas.yaml{self.test_pointers[1]}", cache
                )
                end = time.perf_counter()
                durations["subsequent_different"].append(end - start)

            # Test validator building with optimized cache
            with TedsSchemaCache() as cache:
                start = time.perf_counter()
                build_validator_for_ref(
                    self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
                )
                end = time.perf_counter()
                durations["validator_build"].append(end - start)

            # Test examples collection with optimized cache
            with TedsSchemaCache() as cache:
                start = time.perf_counter()
                collect_examples(
                    self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
                )
                end = time.perf_counter()
                durations["examples_collect"].append(end - start)

        # Calculate statistics
        stats = {}
        for operation, times in durations.items():
            stats[operation] = {
                "mean": statistics.mean(times) * 1000,  # Convert to ms
                "median": statistics.median(times) * 1000,
                "stdev": statistics.stdev(times) * 1000 if len(times) > 1 else 0,
                "min": min(times) * 1000,
                "max": max(times) * 1000,
            }

        return stats

    def benchmark_preemptive_caching_benefit(
        self, iterations: int = 50
    ) -> dict[str, dict[str, float]]:
        """Measure the benefit of preemptive caching by accessing multiple pointers."""
        print(
            f"\n=== Preemptive Caching Benefit Benchmark ({iterations} iterations) ==="
        )

        results = {}

        for i, pointer in enumerate(self.test_pointers):
            print(f"Testing pointer {i+1}/{len(self.test_pointers)}: {pointer}")
            durations = []

            # Clear cache, access first pointer (triggers preemptive caching)
            # Then measure access to current pointer
            for _ in range(iterations):
                with TedsSchemaCache() as cache:
                    cache.clear()

                    # Trigger preemptive caching by accessing first pointer
                    resolve_schema_node(
                        self.demo_dir,
                        f"sample_schemas.yaml{self.test_pointers[0]}",
                        cache,
                    )

                    # Now measure access to current pointer (should be preemptively cached)
                    start = time.perf_counter()
                    schema, _ = resolve_schema_node(
                        self.demo_dir, f"sample_schemas.yaml{pointer}", cache
                    )
                    end = time.perf_counter()
                    durations.append(end - start)

            results[pointer] = {
                "mean": statistics.mean(durations) * 1000,
                "median": statistics.median(durations) * 1000,
                "stdev": statistics.stdev(durations) * 1000
                if len(durations) > 1
                else 0,
            }

        return results

    def benchmark_cache_memory_efficiency(self) -> dict[str, int]:
        """Measure cache memory efficiency and pointer count."""
        print("\n=== Cache Memory Efficiency Benchmark ===")

        with TedsSchemaCache() as cache:
            cache.clear()

            # Access first pointer to trigger preemptive caching
            resolve_schema_node(
                self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
            )

            stats = cache.get_stats()
            print("After first access:")
            print(f"  Cached files: {stats['cached_files']}")
            print(f"  Cached pointers: {stats['cached_pointers']}")
            print(f"  Cache size: {stats['cache_size_bytes']} bytes")

            # Access remaining pointers
            for pointer in self.test_pointers[1:]:
                resolve_schema_node(
                    self.demo_dir, f"sample_schemas.yaml{pointer}", cache
                )

            final_stats = cache.get_stats()
            print("After all accesses:")
            print(f"  Cached files: {final_stats['cached_files']}")
            print(f"  Cached pointers: {final_stats['cached_pointers']}")
            print(f"  Cache size: {final_stats['cache_size_bytes']} bytes")

            return {
                "initial_pointers": stats["cached_pointers"],
                "final_pointers": final_stats["cached_pointers"],
                "initial_size": stats["cache_size_bytes"],
                "final_size": final_stats["cache_size_bytes"],
            }

    def run_full_benchmark(self) -> dict:
        """Run all optimized benchmarks and return results."""
        print("🚀 Starting Optimized TeDS Cache Performance Benchmark")
        print(f"Test schemas: {self.sample_schema}, {self.public_schema}")

        results = {
            "optimized_cache": self.benchmark_optimized_cache(),
            "preemptive_benefit": self.benchmark_preemptive_caching_benefit(),
            "memory_efficiency": self.benchmark_cache_memory_efficiency(),
        }

        return results

    def print_results(self, results: dict):
        """Print formatted benchmark results."""
        print("\n" + "=" * 60)
        print("📊 OPTIMIZED BENCHMARK RESULTS SUMMARY")
        print("=" * 60)

        print("\n🔥 Optimized Cache Performance:")
        for operation, stats in results["optimized_cache"].items():
            print(
                f"  {operation:20} | Mean: {stats['mean']:6.2f}ms | Median: {stats['median']:6.2f}ms | StdDev: {stats['stdev']:6.2f}ms"
            )

        print("\n🎯 Preemptive Caching Benefits:")
        for pointer, stats in results["preemptive_benefit"].items():
            short_name = pointer.split("/")[-1]
            print(
                f"  {short_name:20} | Mean: {stats['mean']:6.2f}ms | Median: {stats['median']:6.2f}ms"
            )

        print("\n💾 Memory Efficiency:")
        mem = results["memory_efficiency"]
        print(f"  Initial pointers:  {mem['initial_pointers']:3d}")
        print(f"  Final pointers:    {mem['final_pointers']:3d}")
        print(
            f"  Pointer growth:    {mem['final_pointers'] - mem['initial_pointers']:3d}"
        )
        print(
            f"  Size efficiency:   {mem['final_size'] / mem['final_pointers']:.1f} bytes/pointer"
        )

        print("\n" + "=" * 60)


def main():
    benchmark = OptimizedCacheBenchmark()
    results = benchmark.run_full_benchmark()
    benchmark.print_results(results)

    # Save results to file
    results_file = Path(__file__).parent / "benchmark_results_optimized.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to: {results_file}")


if __name__ == "__main__":
    main()
