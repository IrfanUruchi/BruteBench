import argparse

from brutebench.config import PROFILES
from brutebench.engine.runner import run_benchmark
from brutebench.utils.logger import section


def main():
    parser = argparse.ArgumentParser(description="BruteBench")

    parser.add_argument("--cpu", action="store_true", help="Run CPU benchmark")
    parser.add_argument("--memory", action="store_true", help="Run memory benchmark")
    parser.add_argument("--gpu", action="store_true", help="Run GPU benchmark")
    parser.add_argument("--cpu-dev", action="store_true", help="Run developer CPU workload")
    parser.add_argument("--system", action="store_true", help="Run mixed system benchmark")
    parser.add_argument("--all", action="store_true", help="Run all benchmarks")
    parser.add_argument(
        "--profile",
        default="standard",
        choices=sorted(PROFILES.keys()),
        help="Benchmark profile",
    )
    parser.add_argument("--repeat", type=int, default=1, help="Repeat benchmark runs")

    args = parser.parse_args()

    section("BruteBench")
    run_benchmark(args)


if __name__ == "__main__":
    main()
