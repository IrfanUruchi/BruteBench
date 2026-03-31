import time

def _ts():
    return time.strftime("%H:%M:%S")

def log(msg):
    print(f"[{_ts()}] {msg}")

def section(title):
    print(f"\n=== {title} ===")

def metric(name, value):
    print(f"{name}: {value}")

def warn(msg):
    print(f"[WARN] {msg}")

def error(msg):
    print(f"[ERROR] {msg}")