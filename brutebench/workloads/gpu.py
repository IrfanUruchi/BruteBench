import time
from statistics import mean

from brutebench.workloads.base import Workload
from brutebench.utils.logger import log


class GPUWorkload(Workload):
    name = "gpu"

    def __init__(self, rounds=4, size=1024, iters=80):
        self.rounds = rounds
        self.size = size
        self.iters = iters

    def _run_mlx(self):
        try:
            import mlx.core as mx
        except Exception as e:
            log(f"MLX import failed: {e}")
            return None

        try:
            dev = mx.default_device()
            times = []

            for r in range(self.rounds):
                log(f"Round {r+1}/{self.rounds} · MLX · {dev}")

                a = mx.random.normal((self.size, self.size), dtype=mx.float32)
                b = mx.random.normal((self.size, self.size), dtype=mx.float32)

                warm = mx.matmul(a, b)
                mx.eval(warm)

                start = time.time()
                c = a
                for _ in range(self.iters):
                    c = mx.matmul(c, b)
                mx.eval(c)

                duration = time.time() - start
                times.append(duration)
                log(f"  {duration:.2f}s")

            return times
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

        for r in range(self.rounds):
            log(f"Round {r+1}/{self.rounds} · CUDA · {device}")
            a = torch.randn(self.size, self.size, device=device, dtype=torch.float32)
            b = torch.randn(self.size, self.size, device=device, dtype=torch.float32)

            warm = torch.matmul(a, b)
            torch.cuda.synchronize()

            start = time.time()
            c = a
            for _ in range(self.iters):
                c = torch.matmul(c, b)
            torch.cuda.synchronize()

            duration = time.time() - start
            times.append(duration)
            log(f"  {duration:.2f}s")

        return times

    def _run_numpy(self):
        try:
            import numpy as np
        except Exception as e:
            log(f"NumPy import failed: {e}")
            return None

        times = []
        cpu_size = max(512, self.size // 2)
        cpu_iters = max(30, self.iters // 2)

        for r in range(self.rounds):
            log(f"Round {r+1}/{self.rounds} · CPU fallback")
            a = np.random.randn(cpu_size, cpu_size).astype("float32")
            b = np.random.randn(cpu_size, cpu_size).astype("float32")

            _ = np.matmul(a, b)

            start = time.time()
            c = a
            for _ in range(cpu_iters):
                c = np.matmul(c, b)

            duration = time.time() - start
            times.append(duration)
            log(f"  {duration:.2f}s")

        return times

    def run(self):
        log("Starting GPU workload")

        backend = None
        times = None

        try:
            times = self._run_mlx()
            if times is not None:
                backend = "MLX"
        except Exception as e:
            log(f"MLX failed: {e}")
            times = None

        if times is None:
            try:
                times = self._run_cuda()
                if times is not None:
                    backend = "CUDA"
            except Exception as e:
                log(f"CUDA failed: {e}")
                times = None

        if times is None:
            try:
                times = self._run_numpy()
                if times is not None:
                    backend = "CPU"
            except Exception as e:
                log(f"CPU fallback failed: {e}")
                times = None

        if times is None:
            return {
                "avg_time": 0,
                "min_time": 0,
                "max_time": 0,
                "backend": "NONE",
                "rounds": 0,
            }

        avg = mean(times)

        if backend == "CPU" and avg < 0.25:
            avg = 0.25

        if backend == "MLX" and avg < 0.15:
            avg = 0.15

        if backend == "CUDA" and avg < 0.12:
            avg = 0.12

        return {
            "avg_time": avg,
            "min_time": min(times),
            "max_time": max(times),
            "backend": backend,
            "rounds": len(times),
        }