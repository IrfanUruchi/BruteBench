from statistics import mean
from time import perf_counter

from brutebench.utils.logger import log
from brutebench.workloads.base import Workload


class GPUWorkload(Workload):
    name = "gpu"

    def __init__(self, rounds=3, size=128, iters=4, target_seconds=1.2):
        self.rounds = rounds
        self.size = size
        self.iters = iters
        self.target_seconds = max(0.25, target_seconds)

    def _ops_per_run(self, size, iterations):
        return (2 * (size ** 3) * iterations) / 1_000_000_000

    def _run_mlx(self):
        try:
            import mlx.core as mx
        except Exception as e:
            log(f"MLX import failed: {e}")
            return None

        try:
            device = mx.default_device()
            times = []
            gflops = []

            for round_index in range(self.rounds):
                log(f"Round {round_index + 1}/{self.rounds} · MLX · {device}")

                a = mx.random.normal((self.size, self.size), dtype=mx.float32)
                b = mx.random.normal((self.size, self.size), dtype=mx.float32)
                warmup = mx.matmul(a, b)
                mx.eval(warmup)

                start = perf_counter()
                completed_runs = 0

                while True:
                    c = a
                    for _ in range(self.iters):
                        c = mx.matmul(c, b)
                    mx.eval(c)
                    completed_runs += 1

                    duration = perf_counter() - start
                    if duration >= self.target_seconds:
                        break

                duration = perf_counter() - start
                round_gflops = (self._ops_per_run(self.size, self.iters) * completed_runs) / duration
                times.append(duration)
                gflops.append(round_gflops)
                log(f"  {duration:.2f}s | {round_gflops:.2f} GFLOPS")

            return times, gflops, self.size, self.iters, "MLX", True
        except Exception as e:
            log(f"MLX execution failed: {e}")
            return None

    def _run_cuda(self):
        try:
            import torch
            if not torch.cuda.is_available():
                return None
        except Exception as e:
            log(f"CUDA import failed: {e}")
            return None

        import torch

        device = torch.device("cuda")
        times = []
        gflops = []

        for round_index in range(self.rounds):
            log(f"Round {round_index + 1}/{self.rounds} · CUDA · {device}")
            a = torch.randn(self.size, self.size, device=device, dtype=torch.float32)
            b = torch.randn(self.size, self.size, device=device, dtype=torch.float32)

            _ = torch.matmul(a, b)
            torch.cuda.synchronize()

            start = perf_counter()
            completed_runs = 0

            while True:
                c = a
                for _ in range(self.iters):
                    c = torch.matmul(c, b)
                torch.cuda.synchronize()
                completed_runs += 1

                duration = perf_counter() - start
                if duration >= self.target_seconds:
                    break

            duration = perf_counter() - start
            round_gflops = (self._ops_per_run(self.size, self.iters) * completed_runs) / duration
            times.append(duration)
            gflops.append(round_gflops)
            log(f"  {duration:.2f}s | {round_gflops:.2f} GFLOPS")

        return times, gflops, self.size, self.iters, "CUDA", True

    def _run_mps(self):
        try:
            import torch
            if not getattr(torch.backends, "mps", None) or not torch.backends.mps.is_available():
                return None
        except Exception as e:
            log(f"MPS import failed: {e}")
            return None

        import torch

        device = torch.device("mps")
        times = []
        gflops = []

        for round_index in range(self.rounds):
            log(f"Round {round_index + 1}/{self.rounds} · MPS · {device}")
            a = torch.randn(self.size, self.size, device=device, dtype=torch.float32)
            b = torch.randn(self.size, self.size, device=device, dtype=torch.float32)

            _ = torch.matmul(a, b)
            if hasattr(torch.mps, "synchronize"):
                torch.mps.synchronize()

            start = perf_counter()
            completed_runs = 0

            while True:
                c = a
                for _ in range(self.iters):
                    c = torch.matmul(c, b)
                if hasattr(torch.mps, "synchronize"):
                    torch.mps.synchronize()
                completed_runs += 1

                duration = perf_counter() - start
                if duration >= self.target_seconds:
                    break

            duration = perf_counter() - start
            round_gflops = (self._ops_per_run(self.size, self.iters) * completed_runs) / duration
            times.append(duration)
            gflops.append(round_gflops)
            log(f"  {duration:.2f}s | {round_gflops:.2f} GFLOPS")

        return times, gflops, self.size, self.iters, "MPS", True

    def _run_numpy(self):
        try:
            import numpy as np
        except Exception as e:
            log(f"NumPy import failed: {e}")
            return None

        size = max(48, self.size)
        iterations = max(2, self.iters)
        times = []
        gflops = []

        for round_index in range(self.rounds):
            log(f"Round {round_index + 1}/{self.rounds} · NumPy fallback")
            a = np.random.randn(size, size).astype("float32")
            b = np.random.randn(size, size).astype("float32")

            _ = np.matmul(a, b)

            start = perf_counter()
            completed_runs = 0

            while True:
                c = a
                for _ in range(iterations):
                    c = np.matmul(c, b)
                completed_runs += 1

                duration = perf_counter() - start
                if duration >= self.target_seconds:
                    break

            duration = perf_counter() - start
            round_gflops = (self._ops_per_run(size, iterations) * completed_runs) / duration
            times.append(duration)
            gflops.append(round_gflops)
            log(f"  {duration:.2f}s | {round_gflops:.2f} GFLOPS")

        return times, gflops, size, iterations, "NumPy", False

    def _run_python(self):
        size = max(24, min(48, self.size // 2))
        iterations = max(3, min(6, self.iters + 1))
        times = []
        gflops = []

        base_a = [[((row + col) % 11) / 10 for col in range(size)] for row in range(size)]
        base_b = [[((row * 2 + col) % 13) / 10 for col in range(size)] for row in range(size)]
        base_bt = [list(column) for column in zip(*base_b)]

        for round_index in range(self.rounds):
            log(f"Round {round_index + 1}/{self.rounds} · Python fallback")
            start = perf_counter()
            checksum = 0.0
            completed_runs = 0

            while True:
                for _ in range(iterations):
                    for row in base_a:
                        for col in base_bt:
                            checksum += sum(left * right for left, right in zip(row, col))
                completed_runs += 1

                duration = perf_counter() - start
                if duration >= self.target_seconds:
                    break

            duration = perf_counter() - start
            round_gflops = (self._ops_per_run(size, iterations) * completed_runs) / duration
            times.append(duration)
            gflops.append(round_gflops)
            log(f"  {duration:.2f}s | {round_gflops:.2f} GFLOPS | checksum {int(checksum)}")

        return times, gflops, size, iterations, "Python", False

    def run(self):
        log("Starting GPU workload")

        result = None

        for runner in (
            self._run_mlx,
            self._run_cuda,
            self._run_mps,
            self._run_numpy,
            self._run_python,
        ):
            try:
                result = runner()
            except Exception as e:
                log(f"{runner.__name__} failed: {e}")
                result = None

            if result is not None:
                break

        if result is None:
            return {
                "avg_time": 0,
                "min_time": 0,
                "max_time": 0,
                "backend": "NONE",
                "rounds": 0,
                "avg_gflops": 0.0,
                "accelerated": False,
                "size": 0,
                "iters": 0,
            }

        times, gflops, size, iterations, backend, accelerated = result
        avg_time = mean(times)

        return {
            "avg_time": avg_time,
            "min_time": min(times),
            "max_time": max(times),
            "backend": backend,
            "rounds": len(times),
            "avg_gflops": mean(gflops),
            "accelerated": accelerated,
            "size": size,
            "iters": iterations,
            "target_seconds": self.target_seconds,
        }
