import time
import psutil
from statistics import mean

from brutebench.workloads.base import Workload
MEMORY_CHUNK_MB = 100
from brutebench.utils.logger import log


class MemoryWorkload(Workload):
    name = "memory"

    def __init__(self, max_percent=None):
        self.max_percent = max_percent or 70

    def run(self):
        log("Starting memory stress test")

        allocated = []
        chunk_size = MEMORY_CHUNK_MB * 1024 * 1024
        times = []

        while True:
            mem = psutil.virtual_memory()
            usage = mem.percent

            if usage >= self.max_percent:
                log(f"Reached safe memory limit: {usage}%")
                break

            if len(allocated) > 200:
                log("Hard limit reached — stopping")
                break

            start = time.time()

            try:
                block = bytearray(chunk_size)

                for i in range(0, chunk_size, 4096):
                    block[i] = 1

                allocated.append(block)

            except MemoryError:
                log("MemoryError — stopping")
                break

            duration = time.time() - start

            mem = psutil.virtual_memory()
            usage = mem.percent

            times.append(duration)

            log(f"+{MEMORY_CHUNK_MB}MB | {duration:.3f}s | usage: {usage:.1f}%")

            time.sleep(0.05)

        avg_time = mean(times) if times else 0
        min_time = min(times) if times else 0
        max_time = max(times) if times else 0
        latency_spread = (max_time / min_time) if min_time > 0 else 1.0

        return {
            "chunks": len(allocated),
            "total_mb": len(allocated) * MEMORY_CHUNK_MB,
            "avg_alloc_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "latency_spread": latency_spread,
        }