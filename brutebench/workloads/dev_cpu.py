import ast
import hashlib
import json
import re
from statistics import mean, pstdev
from time import perf_counter

from brutebench.utils.logger import log
from brutebench.workloads.base import Workload


class DevCPUWorkload(Workload):
    name = "dev_cpu"

    def __init__(self, rounds=4, iterations=700, dataset_size=24):
        self.rounds = rounds
        self.iterations = iterations
        self.pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
        self.payloads = [self._build_payload(index) for index in range(dataset_size)]

    def _build_payload(self, index):
        dependencies = {
            f"lib_{item}": f"{1 + ((index + item) % 4)}.{(index * item) % 10}.{(index + item) % 7}"
            for item in range(1, 7)
        }
        manifest = {
            "id": index,
            "name": f"package_{index}",
            "private": index % 3 == 0,
            "scripts": {
                "build": "python -m build",
                "test": "pytest -q",
                "lint": "ruff check .",
            },
            "deps": dependencies,
            "targets": ["cli", "api", "worker"],
            "flags": {"typed": True, "cache": index % 2 == 0},
        }

        lines = [f"VALUE_{item} = {index + item}" for item in range(8)]
        lines.append("")
        lines.append(f"class Worker{index}:")
        lines.append("    def run(self, payload):")
        lines.append("        total = 0")
        lines.append("        for key, value in payload.items():")
        lines.append("            total += len(str(key)) + len(str(value))")
        lines.append("        return total")
        lines.append("")
        lines.append("def transform(values):")
        lines.append("    return [value * 2 for value in values if value % 2 == 0]")
        lines.append("")
        lines.append("def render(metadata):")
        lines.append("    return '-'.join(sorted(metadata.keys()))")

        return json.dumps(manifest, sort_keys=True), "\n".join(lines)

    def single_task(self, index):
        manifest_json, source = self.payloads[index % len(self.payloads)]
        manifest = json.loads(manifest_json)
        tree = ast.parse(source)
        compiled = compile(tree, filename=f"<bench-{index}>", mode="exec")
        tokens = self.pattern.findall(source)
        digest = hashlib.sha256((manifest_json + source).encode("utf-8")).hexdigest()
        ordered = sorted(
            manifest["deps"].items(),
            key=lambda item: (item[1], item[0]),
        )

        artifact = {
            "module": manifest["name"],
            "exports": len(tokens),
            "deps": ordered[:4],
            "bytecode_size": len(compiled.co_code),
        }
        return len(json.dumps(artifact, sort_keys=True)) + int(digest[:2], 16)

    def run(self):
        log(f"Running dev workload: {self.rounds} rounds")

        times = []
        ops_per_second = []
        checksums = []

        for round_index in range(self.rounds):
            log(f"Round {round_index + 1}/{self.rounds}")

            start = perf_counter()
            checksum = 0

            for iteration in range(self.iterations):
                checksum += self.single_task(iteration + round_index)

            duration = perf_counter() - start
            times.append(duration)
            checksums.append(checksum)
            ops = self.iterations / duration if duration > 0 else 0
            ops_per_second.append(ops)

            log(f"  {duration:.2f}s | {int(ops)} tasks/sec")

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
            "checksum": sum(checksums),
        }
