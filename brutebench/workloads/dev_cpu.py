import time
import json
import hashlib
from statistics import mean

from brutebench.workloads.base import Workload
from brutebench.utils.logger import log


class DevCPUWorkload(Workload):
    name = "dev_cpu"

    def __init__(self, rounds=5, iterations=20000):
        self.rounds = rounds
        self.iterations = iterations

    def single_task(self):
        data = {
            "id": 123,
            "name": "BruteBench",
            "values": list(range(50)),
            "nested": {"a": "x", "b": "y", "c": "z"}
        }

        s = json.dumps(data)

        for _ in range(10):
            obj = json.loads(s)

            h = hashlib.sha256(s.encode()).hexdigest()

            _ = f"{obj['name']}-{h[:8]}"

    def run(self):
        log(f"Running dev workload: {self.rounds} rounds")

        times = []

        for r in range(self.rounds):
            log(f"Round {r+1}/{self.rounds}")

            start = time.time()

            for _ in range(self.iterations):
                self.single_task()

            duration = time.time() - start
            times.append(duration)

            log(f"  {duration:.2f}s")

        avg_time = mean(times)

        baseline = times[0]
        degradation = [((t - baseline) / baseline) * 100 for t in times]
        stability = max(0, min(100, 100 - abs(mean(degradation))))

        return {
            "avg_time": avg_time,
            "stability": stability,
            "min_time": min(times),
            "max_time": max(times),
        }