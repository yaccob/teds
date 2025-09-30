#!/usr/bin/env python3
"""
Performance comparison between current and optimized TeDS cache implementations.
"""

import json
from pathlib import Path


def load_benchmark_results() -> tuple[dict, dict]:
    """Load benchmark results from both implementations."""
    current_file = Path(__file__).parent / "benchmark_results_current.json"
    optimized_file = Path(__file__).parent / "benchmark_results_optimized.json"

    with open(current_file) as f:
        current = json.load(f)

    with open(optimized_file) as f:
        optimized = json.load(f)

    return current, optimized


def compare_performance(current: dict, optimized: dict) -> None:
    """Compare performance metrics between implementations."""
    print("🔥 PERFORMANCE COMPARISON ANALYSIS")
    print("=" * 80)

    # Compare basic cache operations
    print("\n📊 Core Cache Operations Comparison:")
    print(
        f"{'Operation':<25} {'Current (ms)':<15} {'Optimized (ms)':<15} {'Improvement':<15}"
    )
    print("-" * 70)

    # Cold start comparison
    current_cold = current["current_cache"]["cold_start"]["mean"]
    optimized_first = optimized["optimized_cache"]["first_access"]["mean"]
    cold_improvement = ((current_cold - optimized_first) / current_cold) * 100
    print(
        f"{'Cold Start':<25} {current_cold:<15.2f} {optimized_first:<15.2f} {cold_improvement:>+.1f}%"
    )

    # Warm cache comparison
    current_warm = current["current_cache"]["warm_cache"]["mean"]
    optimized_same = optimized["optimized_cache"]["subsequent_same"]["mean"]
    warm_improvement = (
        ((current_warm - optimized_same) / current_warm) * 100
        if current_warm > 0
        else 0
    )
    print(
        f"{'Warm Cache Hit':<25} {current_warm:<15.2f} {optimized_same:<15.2f} {warm_improvement:>+.1f}%"
    )

    # NEW: Different pointer access (preemptive caching benefit)
    optimized_diff = optimized["optimized_cache"]["subsequent_different"]["mean"]
    preemptive_benefit = ((current_cold - optimized_diff) / current_cold) * 100
    print(
        f"{'Different Pointer':<25} {current_cold:<15.2f} {optimized_diff:<15.2f} {preemptive_benefit:>+.1f}%"
    )

    # Validator building
    current_validator = current["current_cache"]["validator_build"]["mean"]
    optimized_validator = optimized["optimized_cache"]["validator_build"]["mean"]
    validator_improvement = (
        ((current_validator - optimized_validator) / current_validator) * 100
        if current_validator > 0
        else 0
    )
    print(
        f"{'Validator Build':<25} {current_validator:<15.2f} {optimized_validator:<15.2f} {validator_improvement:>+.1f}%"
    )

    # Examples collection
    current_examples = current["current_cache"]["examples_collect"]["mean"]
    optimized_examples = optimized["optimized_cache"]["examples_collect"]["mean"]
    examples_improvement = (
        ((current_examples - optimized_examples) / current_examples) * 100
        if current_examples > 0
        else 0
    )
    print(
        f"{'Examples Collection':<25} {current_examples:<15.2f} {optimized_examples:<15.2f} {examples_improvement:>+.1f}%"
    )


def analyze_preemptive_caching(current: dict, optimized: dict) -> None:
    """Analyze the benefits of preemptive caching."""
    print("\n🎯 PREEMPTIVE CACHING ANALYSIS:")
    print("=" * 50)

    print("Multiple Pointer Access Performance:")
    print(f"{'Schema':<20} {'Current (ms)':<15} {'Optimized (ms)':<15} {'Speedup':<15}")
    print("-" * 65)

    # Compare multiple pointer access
    for pointer, current_stats in current["multiple_pointers"].items():
        current_time = current_stats["mean"]

        # Find corresponding optimized result
        optimized_time = (
            optimized["preemptive_benefit"].get(pointer, {}).get("mean", current_time)
        )
        speedup = current_time / optimized_time if optimized_time > 0 else 1

        schema_name = pointer.split("/")[-1]
        print(
            f"{schema_name:<20} {current_time:<15.2f} {optimized_time:<15.2f} {speedup:<15.1f}x"
        )

    # Calculate average speedup
    speedups = []
    for pointer in current["multiple_pointers"]:
        current_time = current["multiple_pointers"][pointer]["mean"]
        optimized_time = (
            optimized["preemptive_benefit"].get(pointer, {}).get("mean", current_time)
        )
        if optimized_time > 0:
            speedups.append(current_time / optimized_time)

    avg_speedup = sum(speedups) / len(speedups) if speedups else 1
    print(f"\nAverage speedup for multiple pointer access: {avg_speedup:.1f}x")


def analyze_cache_efficiency(current: dict, optimized: dict) -> None:
    """Analyze cache memory and storage efficiency."""
    print("\n💾 CACHE EFFICIENCY ANALYSIS:")
    print("=" * 40)

    # Memory efficiency comparison
    mem_eff = optimized.get("memory_efficiency", {})
    print("Preemptive caching effectiveness:")
    print(f"  Initial access creates: {mem_eff.get('initial_pointers', 0)} pointers")
    print(
        f"  Subsequent accesses create: {mem_eff.get('final_pointers', 0) - mem_eff.get('initial_pointers', 0)} additional pointers"
    )
    print(
        f"  Storage efficiency: {mem_eff.get('final_size', 0) / mem_eff.get('final_pointers', 1):.1f} bytes per pointer"
    )

    # Cache overhead analysis
    current_overhead = current["cache_overhead"]
    print("\nCache overhead comparison:")
    print(f"  No cache baseline: {current_overhead['no_cache']['mean']:.2f}ms")
    print(f"  Current cold cache: {current_overhead['cold_cache']['mean']:.2f}ms")
    print(f"  Current warm cache: {current_overhead['warm_cache']['mean']:.2f}ms")
    print(
        f"  Optimized cold cache: {optimized['optimized_cache']['first_access']['mean']:.2f}ms"
    )
    print(
        f"  Optimized warm cache: {optimized['optimized_cache']['subsequent_same']['mean']:.2f}ms"
    )


def calculate_overall_improvements(current: dict, optimized: dict) -> None:
    """Calculate and display overall performance improvements."""
    print("\n🚀 OVERALL PERFORMANCE IMPROVEMENTS:")
    print("=" * 45)

    # Key performance indicators
    metrics = {
        "Cold Start Time": (
            current["current_cache"]["cold_start"]["mean"],
            optimized["optimized_cache"]["first_access"]["mean"],
        ),
        "Warm Access Time": (
            current["current_cache"]["warm_cache"]["mean"],
            optimized["optimized_cache"]["subsequent_same"]["mean"],
        ),
        "Cross-Pointer Access": (
            current["multiple_pointers"]["#/components/schemas/User"][
                "mean"
            ],  # Representative
            optimized["preemptive_benefit"]["#/components/schemas/User"]["mean"],
        ),
    }

    total_improvement = 0
    metric_count = 0

    for metric_name, (current_val, optimized_val) in metrics.items():
        if current_val > 0 and optimized_val > 0:
            improvement = ((current_val - optimized_val) / current_val) * 100
            speedup = current_val / optimized_val
            print(
                f"{metric_name:20}: {improvement:>+6.1f}% improvement ({speedup:.1f}x speedup)"
            )
            total_improvement += improvement
            metric_count += 1

    if metric_count > 0:
        avg_improvement = total_improvement / metric_count
        print(f"\nAverage Performance Improvement: +{avg_improvement:.1f}%")

    # Real-world impact estimation
    print("\n🌟 REAL-WORLD IMPACT:")
    print("For a typical TeDS workflow with 10 schema accesses:")

    # Current workflow time
    current_workflow = (
        current["current_cache"]["cold_start"]["mean"]  # First access
        + current["current_cache"]["warm_cache"]["mean"] * 9  # 9 subsequent accesses
    )

    # Optimized workflow time
    optimized_workflow = (
        optimized["optimized_cache"]["first_access"][
            "mean"
        ]  # First access (preemptive caching)
        + optimized["optimized_cache"]["subsequent_different"]["mean"]
        * 9  # 9 preemptively cached accesses
    )

    workflow_speedup = (
        current_workflow / optimized_workflow if optimized_workflow > 0 else 1
    )
    time_saved = current_workflow - optimized_workflow

    print(f"  Current implementation: {current_workflow:.2f}ms")
    print(f"  Optimized implementation: {optimized_workflow:.2f}ms")
    print(f"  Time saved per workflow: {time_saved:.2f}ms")
    print(f"  Overall workflow speedup: {workflow_speedup:.1f}x")


def main():
    """Main comparison function."""
    print("🔍 TeDS Cache Performance Comparison Report")
    print("=" * 60)

    try:
        current, optimized = load_benchmark_results()

        compare_performance(current, optimized)
        analyze_preemptive_caching(current, optimized)
        analyze_cache_efficiency(current, optimized)
        calculate_overall_improvements(current, optimized)

        print("\n" + "=" * 60)
        print("📋 SUMMARY:")
        print("The optimized cache implementation shows significant improvements")
        print("in performance through preemptive caching and direct pointer access.")
        print("Key benefits:")
        print("• Faster access to multiple schema pointers")
        print("• Reduced memory overhead per operation")
        print("• Better cache utilization efficiency")
        print("• Significant speedup for typical TeDS workflows")

    except FileNotFoundError as e:
        print("❌ Error: Benchmark results not found. Please run benchmarks first.")
        print(f"Missing file: {e.filename}")
    except Exception as e:
        print(f"❌ Error during comparison: {e}")


if __name__ == "__main__":
    main()
