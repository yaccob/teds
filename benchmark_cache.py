#!/usr/bin/env python3
"""
Performance benchmark for TeDS cache system.

This script measures cache performance for different schema access patterns
to identify bottlenecks and validate optimizations.
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


class CacheBenchmark:
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

    def time_operation(self, operation_name: str, func, *args, **kwargs) -> float:
        """Time a single operation and return duration in seconds."""
        start = time.perf_counter()
        _ = func(*args, **kwargs)  # Execute function, ignore result
        end = time.perf_counter()
        duration = end - start
        print(f"  {operation_name}: {duration*1000:.2f}ms")
        return duration

    def benchmark_current_cache(self, iterations: int = 100) -> dict[str, float]:
        """Benchmark current cache implementation."""
        print(
            f"\n=== Current Cache Implementation Benchmark ({iterations} iterations) ==="
        )

        # Clear cache first
        with TedsSchemaCache() as cache:
            cache.clear()

        durations = {
            "cold_start": [],
            "warm_cache": [],
            "validator_build": [],
            "examples_collect": [],
        }

        for i in range(iterations):
            if i % 20 == 0:
                print(f"Iteration {i+1}/{iterations}")

            # Test cold start (cache miss)
            with TedsSchemaCache() as cache:
                cache.clear()
                start = time.perf_counter()
                schema, _ = resolve_schema_node(
                    self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
                )
                end = time.perf_counter()
                durations["cold_start"].append(end - start)

            # Test warm cache (cache hit)
            with TedsSchemaCache() as cache:
                # Warm up cache
                resolve_schema_node(
                    self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
                )

                # Measure warm access
                start = time.perf_counter()
                schema, _ = resolve_schema_node(
                    self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
                )
                end = time.perf_counter()
                durations["warm_cache"].append(end - start)

            # Test validator building
            with TedsSchemaCache() as cache:
                start = time.perf_counter()
                build_validator_for_ref(
                    self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
                )
                end = time.perf_counter()
                durations["validator_build"].append(end - start)

            # Test examples collection
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

    def benchmark_multiple_pointers(
        self, iterations: int = 50
    ) -> dict[str, dict[str, float]]:
        """Benchmark accessing multiple different pointers."""
        print(f"\n=== Multiple Pointers Benchmark ({iterations} iterations) ===")

        results = {}

        for pointer in self.test_pointers:
            print(f"Testing pointer: {pointer}")
            durations = []

            for _ in range(iterations):
                with TedsSchemaCache() as cache:
                    cache.clear()  # Force cache miss each time
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
                "min": min(durations) * 1000,
                "max": max(durations) * 1000,
            }

        return results

    def benchmark_cache_overhead(
        self, iterations: int = 100
    ) -> dict[str, dict[str, float]]:
        """Compare cached vs non-cached operations."""
        print(f"\n=== Cache Overhead Benchmark ({iterations} iterations) ===")

        # Without cache
        no_cache_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            schema, _ = resolve_schema_node(
                self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", None
            )
            end = time.perf_counter()
            no_cache_times.append(end - start)

        # With cache (cold)
        cold_cache_times = []
        for _ in range(iterations):
            with TedsSchemaCache() as cache:
                cache.clear()
                start = time.perf_counter()
                schema, _ = resolve_schema_node(
                    self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
                )
                end = time.perf_counter()
                cold_cache_times.append(end - start)

        # With cache (warm)
        warm_cache_times = []
        with TedsSchemaCache() as cache:
            # Warm up
            resolve_schema_node(
                self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
            )

            for _ in range(iterations):
                start = time.perf_counter()
                schema, _ = resolve_schema_node(
                    self.demo_dir, f"sample_schemas.yaml{self.test_pointers[0]}", cache
                )
                end = time.perf_counter()
                warm_cache_times.append(end - start)

        return {
            "no_cache": {
                "mean": statistics.mean(no_cache_times) * 1000,
                "median": statistics.median(no_cache_times) * 1000,
                "stdev": statistics.stdev(no_cache_times) * 1000,
            },
            "cold_cache": {
                "mean": statistics.mean(cold_cache_times) * 1000,
                "median": statistics.median(cold_cache_times) * 1000,
                "stdev": statistics.stdev(cold_cache_times) * 1000,
            },
            "warm_cache": {
                "mean": statistics.mean(warm_cache_times) * 1000,
                "median": statistics.median(warm_cache_times) * 1000,
                "stdev": statistics.stdev(warm_cache_times) * 1000,
            },
        }

    def run_full_benchmark(self) -> dict:
        """Run all benchmarks and return results."""
        print("🚀 Starting TeDS Cache Performance Benchmark")
        print(f"Test schemas: {self.sample_schema}, {self.public_schema}")

        results = {
            "current_cache": self.benchmark_current_cache(),
            "multiple_pointers": self.benchmark_multiple_pointers(),
            "cache_overhead": self.benchmark_cache_overhead(),
        }

        return results

    def print_results(self, results: dict):
        """Print formatted benchmark results."""
        print("\n" + "=" * 60)
        print("📊 BENCHMARK RESULTS SUMMARY")
        print("=" * 60)

        print("\n🔥 Current Cache Performance:")
        for operation, stats in results["current_cache"].items():
            print(
                f"  {operation:20} | Mean: {stats['mean']:6.2f}ms | Median: {stats['median']:6.2f}ms | StdDev: {stats['stdev']:6.2f}ms"
            )

        print("\n🎯 Multiple Pointers Performance:")
        for pointer, stats in results["multiple_pointers"].items():
            short_name = pointer.split("/")[-1]
            print(
                f"  {short_name:20} | Mean: {stats['mean']:6.2f}ms | Median: {stats['median']:6.2f}ms"
            )

        print("\n⚡ Cache Overhead Analysis:")
        overhead = results["cache_overhead"]
        print(f"  No Cache:         {overhead['no_cache']['mean']:6.2f}ms")
        print(f"  Cold Cache:       {overhead['cold_cache']['mean']:6.2f}ms")
        print(f"  Warm Cache:       {overhead['warm_cache']['mean']:6.2f}ms")

        # Calculate speedup
        no_cache_mean = overhead["no_cache"]["mean"]
        warm_cache_mean = overhead["warm_cache"]["mean"]
        speedup = no_cache_mean / warm_cache_mean if warm_cache_mean > 0 else 0
        print(f"  Speedup (warm):   {speedup:.2f}x")

        print("\n" + "=" * 60)


def main():
    benchmark = CacheBenchmark()
    results = benchmark.run_full_benchmark()
    benchmark.print_results(results)

    # Save results to file
    results_file = Path(__file__).parent / "benchmark_results_current.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to: {results_file}")


if __name__ == "__main__":
    main()
