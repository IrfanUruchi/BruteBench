import hashlib
import math
import multiprocessing as mp
import zlib
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from statistics import mean, pstdev
from time import perf_counter

from brutebench.utils.logger import log
from brutebench.workloads.base import Workload


def is_prime(value):
    if value < 2:
        return False
    if value == 2:
        return True
    if value % 2 == 0:
        return False

    limit = int(math.sqrt(value)) + 1
    for candidate in range(3, limit, 2):
        if value % candidate == 0:
            return False
    return True


def cpu_worker(task):
    units, span, seed = task
    checksum = 0

    for unit in range(units):
        start_value = seed + (unit * span)
        buffer = bytearray(span * 4)

        for offset in range(span):
            value = start_value + offset
            if is_prime(value):
                checksum += 1

            mixed = ((value * 2654435761) ^ (value >> 3)) & 0xFFFFFFFF
            index = offset * 4
            buffer[index:index + 4] = mixed.to_bytes(4, "little")

        digest = hashlib.blake2b(buffer, digest_size=32).digest()
        compressed = zlib.compress(buffer, level=6)
        checksum ^= digest[0]
        checksum += len(compressed)

    return checksum


class CPUWorkload(Workload):
    name = "cpu"

    def __init__(self, rounds=4, units=12, span=480, processes=None):
        self.rounds = rounds
        self.units = units
        self.span = span
        self.processes = max(1, processes or (mp.cpu_count() or 1))

    def _tasks(self):
        stride = self.units * self.span * 2
        return [
            (self.units, self.span, 10_000 + (worker_index * stride))
            for worker_index in range(self.processes)
        ]

    def _run_with_executor(self, executor_factory, **executor_kwargs):
        times = []
        ops_per_second = []
        checksums = []
        total_work = self.units * self.span * self.processes

        with executor_factory(max_workers=self.processes, **executor_kwargs) as executor:
            warmup_tasks = [(1, max(64, self.span // 3), 2_000 + index) for index in range(self.processes)]
            list(executor.map(cpu_worker, warmup_tasks))

            for round_index in range(self.rounds):
                log(f"Round {round_index + 1}/{self.rounds}")
                start = perf_counter()
                round_checksums = list(executor.map(cpu_worker, self._tasks()))
                duration = perf_counter() - start

                checksums.append(sum(round_checksums))
                times.append(duration)
                ops = total_work / duration if duration > 0 else 0
                ops_per_second.append(ops)

                log(f"  {duration:.2f}s | {int(ops)} ops/sec")

        return times, ops_per_second, checksums

    def run(self):
        log(
            f"Running {self.rounds} sustained rounds on {self.processes} workers "
            f"({self.units} units x {self.span} span)"
        )

        try:
            context = mp.get_context("spawn")
            times, ops_per_second, checksums = self._run_with_executor(
                ProcessPoolExecutor,
                mp_context=context,
            )
        except Exception as error:
            log(f"Process workers unavailable ({error}); falling back to threaded execution")
            times, ops_per_second, checksums = self._run_with_executor(ThreadPoolExecutor)

        avg_time = mean(times)
        avg_ops = mean(ops_per_second)
        variability = (pstdev(times) / avg_time) if len(times) > 1 and avg_time else 0.0
        stability = max(0.0, min(100.0, 100.0 - (variability * 100.0)))

        return {
            "avg_time": avg_time,
            "avg_ops": avg_ops,
            "stability": stability,
            "min_time": min(times),
            "max_time": max(times),
            "processes": self.processes,
            "units": self.units,
            "span": self.span,
            "checksum": sum(checksums),
        }
