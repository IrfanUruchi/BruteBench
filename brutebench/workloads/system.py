import ast
import gzip
import hashlib
import io
import json
import tempfile
from pathlib import Path
from statistics import mean, pstdev
from time import perf_counter

from brutebench.utils.logger import log
from brutebench.workloads.base import Workload


class SystemWorkload(Workload):
    name = "system"

    def __init__(self, rounds=3, file_count=18, payload_kb=20):
        self.rounds = rounds
        self.file_count = file_count
        self.payload_kb = payload_kb

    def _write_round_files(self, root, round_index):
        total_bytes = 0

        for file_index in range(self.file_count):
            manifest = {
                "name": f"service_{round_index}_{file_index}",
                "version": f"1.{round_index}.{file_index}",
                "deps": {
                    f"pkg_{item}": f"{1 + ((round_index + item) % 3)}.{file_index % 7}.{item % 5}"
                    for item in range(1, 8)
                },
                "targets": ["api", "worker", "scheduler"],
            }
            manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
            padding = (b"x" * 1024) * self.payload_kb
            path = root / f"pkg_{file_index}.json"
            path.write_bytes(manifest_bytes + b"\n" + padding)
            total_bytes += path.stat().st_size

            source_lines = [f"VALUE_{value} = {round_index + file_index + value}" for value in range(10)]
            source_lines.append("")
            source_lines.append(f"class Service{file_index}:")
            source_lines.append("    def execute(self, payload):")
            source_lines.append("        return sum(len(str(item)) for item in payload)")
            source_lines.append("")
            source_lines.append("def build(items):")
            source_lines.append("    return [item * 2 for item in items if item % 2 == 0]")
            source = "\n".join(source_lines).encode("utf-8")
            module_path = root / f"module_{file_index}.py"
            module_path.write_bytes(source)
            total_bytes += module_path.stat().st_size

        return total_bytes

    def _process_round_files(self, root):
        digest = hashlib.blake2b(digest_size=16)
        archive = io.BytesIO()
        total_bytes = 0
        token_count = 0
        passes = 4

        with gzip.GzipFile(fileobj=archive, mode="wb", compresslevel=6) as handle:
            paths = sorted(root.iterdir())

            for _ in range(passes):
                for path in paths:
                    data = path.read_bytes()
                    total_bytes += len(data)
                    digest.update(data)
                    handle.write(data)
                    token_count += data.count(b"\n")

                    if path.suffix == ".py":
                        source = data.decode("utf-8")
                        tree = ast.parse(source)
                        compile(tree, filename=path.name, mode="exec")
                    elif path.suffix == ".json":
                        payload = json.loads(data.decode("utf-8").splitlines()[0])
                        token_count += len(payload.get("deps", {}))

        archive_value = archive.getvalue()
        restored = gzip.decompress(archive_value)
        digest.update(archive_value[:4096])
        digest.update(restored[:4096])
        token_count += restored.count(b"pkg_")

        return total_bytes, token_count, digest.hexdigest()

    def run(self):
        log(f"Running system workload: {self.rounds} rounds")

        times = []
        throughput = []
        checksums = []

        for round_index in range(self.rounds):
            log(f"Round {round_index + 1}/{self.rounds}")

            with tempfile.TemporaryDirectory(prefix="brutebench-system-") as tempdir:
                root = Path(tempdir)
                start = perf_counter()
                written_bytes = self._write_round_files(root, round_index)
                processed_bytes, token_count, checksum = self._process_round_files(root)
                duration = perf_counter() - start

            times.append(duration)
            checksums.append(int(checksum[:8], 16))
            total_mb = (written_bytes + processed_bytes) / (1024 * 1024)
            ops = total_mb / duration if duration > 0 else 0.0
            throughput.append(ops)

            log(f"  {duration:.2f}s | {ops:.2f} MB/s | tokens {token_count}")

        avg_time = mean(times)
        avg_ops = mean(throughput)
        variability = (pstdev(times) / avg_time) if len(times) > 1 and avg_time else 0.0
        stability = max(0.0, min(100.0, 100.0 - (variability * 100.0)))

        return {
            "avg_time": avg_time,
            "avg_ops": avg_ops,
            "min_time": min(times),
            "max_time": max(times),
            "stability": stability,
            "checksum": sum(checksums),
        }
