import math
import time
import multiprocessing as mp
from statistics import mean

from brutebench.workloads.base import Workload
# removed CPU_PROCESSES dependency
from brutebench.utils.logger import log

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0 and n != 2:
        return False
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True

def compute_primes(start: int, end: int) -> int:
    count = 0
    for i in range(start, end):
        if is_prime(i):
            count += 1
    return count

def worker(task_size: int):
    return compute_primes(10_000, 10_000 + task_size)

class CPUWorkload(Workload):
    name = "cpu"

    def __init__(self, rounds=5, task_size=500000, processes=None):
        self.rounds = rounds
        self.task_size = task_size
        self.processes = processes or mp.cpu_count()

    def run_round(self):
        start = time.time()

        with mp.Pool(self.processes) as pool:
            results = pool.map(worker, [self.task_size] * self.processes)

        duration = time.time() - start
        total = sum(results)

        ops = total / duration if duration > 0 else 0

        return duration, ops

    def run(self):
        log(f"Running {self.rounds} rounds on {self.processes} cores")

        times = []
        ops_list = []

        for i in range(self.rounds):
            log(f"Round {i+1}/{self.rounds}")

            duration, ops = self.run_round()

            times.append(duration)
            ops_list.append(ops)

            log(f"  {duration:.2f}s | {int(ops)} ops/sec")

        baseline = times[0]
        degradation = [((t - baseline) / baseline) * 100 for t in times]

        avg_time = mean(times)
        avg_ops = mean(ops_list)

        stability = 100 - abs(mean(degradation))
        stability = max(0, min(100, stability))

        return {
            "avg_time": avg_time,
            "avg_ops": avg_ops,
            "stability": stability,
            "degradation": degradation
        }