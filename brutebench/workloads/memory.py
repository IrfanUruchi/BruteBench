from statistics import mean, median, pstdev
from time import perf_counter

from brutebench.system.info import get_memory_snapshot
from brutebench.utils.logger import log
from brutebench.workloads.base import Workload


class MemoryWorkload(Workload):
    name = "memory"

    def __init__(self, target_mb=256, chunk_mb=16, floor_mb=384, touch_passes=8):
        self.target_mb = max(16, target_mb)
        self.chunk_mb = max(4, chunk_mb)
        self.floor_mb = max(128, floor_mb)
        self.touch_passes = max(2, touch_passes)

    def _percentile(self, values, ratio):
        if not values:
            return 0.0

        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
        return ordered[index]

    def run(self):
        log(
            f"Starting memory workload target={self.target_mb}MB "
            f"chunk={self.chunk_mb}MB"
        )

        allocated = []
        allocation_times = []
        access_times = []
        checksums = []
        chunk_size = self.chunk_mb * 1024 * 1024
        target_bytes = self.target_mb * 1024 * 1024
        allocated_bytes = 0
        stop_reason = "completed"

        while allocated_bytes < target_bytes:
            snapshot = get_memory_snapshot()
            available_bytes = snapshot.get("available", 0)
            threshold = (self.floor_mb + self.chunk_mb) * 1024 * 1024
            if available_bytes and available_bytes < threshold:
                stop_reason = "safety_floor"
                log("Stopping before low-memory threshold")
                break

            size = min(chunk_size, target_bytes - allocated_bytes)
            start = perf_counter()

            try:
                block = bytearray(size)

                for index in range(0, size, 4096):
                    block[index] = (index // 4096) % 251

                allocated.append(block)
            except MemoryError:
                stop_reason = "memory_error"
                log("Memory allocation failed safely")
                break

            allocation_duration = perf_counter() - start
            allocation_times.append(allocation_duration)

            start = perf_counter()
            checksum = 0
            for pass_index in range(self.touch_passes):
                for index in range(0, size, 4096):
                    checksum ^= block[index]
                    block[index] = (block[index] + pass_index + 7) % 251
            access_duration = perf_counter() - start

            access_times.append(access_duration)
            checksums.append(checksum)
            allocated_bytes += size

            log(
                f"+{size // (1024 * 1024)}MB | alloc {allocation_duration:.4f}s "
                f"| touch {access_duration:.4f}s"
            )

        combined_times = allocation_times + access_times
        avg_alloc_time = mean(allocation_times) if allocation_times else 0.0
        avg_access_time = mean(access_times) if access_times else 0.0
        min_time = min(combined_times) if combined_times else 0.0
        max_time = max(combined_times) if combined_times else 0.0
        p50_time = median(combined_times) if combined_times else 0.0
        p95_time = self._percentile(combined_times, 0.95)
        latency_spread = (p95_time / p50_time) if p50_time > 0 else 1.0
        total_time = sum(combined_times)
        total_mb = allocated_bytes / (1024 * 1024)
        throughput = total_mb / total_time if total_time > 0 else 0.0
        avg_combined = mean(combined_times) if combined_times else 0.0
        variability = (pstdev(combined_times) / avg_combined) if len(combined_times) > 1 and avg_combined else 0.0
        stability = max(0.0, min(100.0, 100.0 - (variability * 100.0)))

        return {
            "chunks": len(allocated),
            "target_mb": self.target_mb,
            "total_mb": round(total_mb, 2),
            "avg_alloc_time": avg_alloc_time,
            "avg_access_time": avg_access_time,
            "min_time": min_time,
            "max_time": max_time,
            "p50_time": p50_time,
            "p95_time": p95_time,
            "latency_spread": latency_spread,
            "throughput_mb_s": throughput,
            "stability": stability,
            "stop_reason": stop_reason,
            "touch_passes": self.touch_passes,
            "checksum": sum(checksums),
        }
