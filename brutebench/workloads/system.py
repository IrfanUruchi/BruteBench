import time
import json
import hashlib
from statistics import mean

from brutebench.workloads.base import Workload
from brutebench.utils.logger import log


class SystemWorkload(Workload):
    name = "system"

    def __init__(self, rounds=3, iterations=8000):
        self.rounds = rounds
        self.iterations = iterations

    def run(self):
        log(f"Running system workload: {self.rounds} rounds")

        times = []

        for r in range(self.rounds):
            log(f"Round {r+1}/{self.rounds}")

            start = time.time()

            for _ in range(self.iterations):
                data = {
                    "vals": list(range(100)),
                    "nested": {"a": "x", "b": "y"}
                }

                s = json.dumps(data)
                obj = json.loads(s)

                h = hashlib.sha256(s.encode()).hexdigest()

                tmp = [str(i) for i in range(50)]
                "".join(tmp)

                _ = f"{obj['nested']['a']}-{h[:6]}"

            duration = time.time() - start
            times.append(duration)

            log(f"  {duration:.2f}s")

        avg = mean(times)

        return {
            "avg_time": avg,
            "min_time": min(times),
            "max_time": max(times),
        }