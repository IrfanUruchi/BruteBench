import json
import time
from pathlib import Path


class BenchmarkResult:
    def __init__(self):
        self.timestamp = int(time.time())
        self.data = {}

    def add(self, key, value):
        self.data[key] = value

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "results": self.data,
        }

    def save(self, folder="results"):
        Path(folder).mkdir(exist_ok=True)

        filename = f"{folder}/run_{self.timestamp}.json"

        with open(filename, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return filename