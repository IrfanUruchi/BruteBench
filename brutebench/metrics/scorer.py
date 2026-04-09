import math

def clamp(value, minimum=0, maximum=1000):
    return max(minimum, min(maximum, value))


def normalize_ratio(ratio, cap=8.0):
    if ratio <= 0:
        return 0
    return math.log1p(ratio) / math.log1p(cap)


def score_cpu(avg_ops, reference_ops):
    if avg_ops <= 0 or reference_ops <= 0:
        return 0

    ratio = avg_ops / reference_ops
    norm = normalize_ratio(ratio, 6.0)

    return clamp(int(1000 * norm))


def score_dev_cpu(avg_time, reference_time):
    if avg_time <= 0 or reference_time <= 0:
        return 0

    ratio = reference_time / avg_time
    norm = normalize_ratio(ratio, 6.0)

    return clamp(int(1000 * norm))


def score_memory(latency_spread, reference_spread):
    if latency_spread <= 0 or reference_spread <= 0:
        return 0

    ratio = reference_spread / latency_spread
    norm = normalize_ratio(ratio, 5.0)

    return clamp(int(1000 * norm))


def score_system(avg_time, reference_time=2.0):
    if avg_time <= 0 or reference_time <= 0:
        return 0

    ratio = reference_time / avg_time
    norm = normalize_ratio(ratio, 5.5)

    return clamp(int(1000 * norm))


def score_gpu(avg_time, reference_time=1.5, backend="CPU"):
    if avg_time <= 0 or reference_time <= 0:
        return 0

    backend = (backend or "CPU").upper().strip()

    if avg_time < 0.20:
        return 0

    ratio = reference_time / avg_time
    norm = normalize_ratio(ratio, 10.0)

    if backend == "CPU":
        return clamp(int(350 * norm))

    if backend == "MLX":
        return clamp(int(1000 * norm * 0.85))

    if backend == "CUDA":
        return clamp(int(1000 * norm))

    if backend == "ROCM":
        return clamp(int(1000 * norm))

    if backend == "DIRECTML":
        return clamp(int(1000 * norm * 0.90))

    return 0


def overall_score(cpu_score=None, dev_score=None, memory_score=None, system_score=None, gpu_score=None, system_info=None):
    parts = []

    if cpu_score is not None:
        parts.append((cpu_score, 0.25))
    if dev_score is not None:
        parts.append((dev_score, 0.25))
    if memory_score is not None:
        parts.append((memory_score, 0.10))
    if system_score is not None:
        parts.append((system_score, 0.25))
    if gpu_score is not None:
        parts.append((gpu_score, 0.15))

    if not parts:
        return 0

    total_weight = sum(weight for _, weight in parts)
    weighted = sum(score * weight for score, weight in parts)
    base_score = weighted / total_weight

    penalty = 0.0

    if system_info:
        ram_gb = system_info.get("ram_gb", 0) or 0
        cores = system_info.get("cpu_cores", 0) or 0

        if ram_gb < 16:
            penalty += 0.18
        elif ram_gb < 24:
            penalty += 0.12
        elif ram_gb < 32:
            penalty += 0.05

        if cores < 8:
            penalty += 0.10
        elif cores < 12:
            penalty += 0.06

    final = base_score * (1 - penalty)
    return clamp(int(final))


def rating_label(score):
    if score >= 970:
        return "EXTREME"
    if score >= 900:
        return "WORKSTATION"
    if score >= 820:
        return "HIGH PERFORMANCE"
    if score >= 740:
        return "DEV PRO"
    if score >= 650:
        return "DEV READY"
    if score >= 550:
        return "LIGHT DEV"
    if score >= 450:
        return "LIMITED"
    return "STRAINED"


def category_score(name, cpu=None, dev=None, memory=None, system=None, gpu=None, gpu_backend=None, gpu_ran=True):
    name = (name or "").lower().strip()
    gpu_backend = (gpu_backend or "").upper().strip()

    parts = []
    total_weight = 0.0

    def add(value, weight):
        nonlocal total_weight
        if value is not None:
            parts.append(value * weight)
            total_weight += weight

    real_gpu_available = (
        gpu is not None and gpu > 250 and gpu_ran and gpu_backend not in ("", "CPU")
    )

    if name == "mobile":
        add(cpu, 0.5)
        add(dev, 0.5)

    elif name == "backend":
        add(cpu, 0.45)
        add(dev, 0.35)
        add(memory, 0.20)

    elif name == "ai":
        if real_gpu_available:
            add(gpu, 0.40)
            add(memory, 0.25)
            add(system, 0.20)
            add(cpu, 0.15)
        else:
            add(cpu, 0.35)
            add(memory, 0.30)
            add(system, 0.25)
            add(dev, 0.10)

    elif name == "systems":
        add(cpu, 0.30)
        add(system, 0.35)
        add(memory, 0.20)
        add(dev, 0.15)

    elif name == "data":
        add(memory, 0.45)
        add(system, 0.35)
        add(cpu, 0.20)

    elif name == "devops":
        add(cpu, 0.30)
        add(system, 0.25)
        add(memory, 0.25)
        add(dev, 0.20)

    if total_weight == 0:
        return 0

    score = clamp(int(sum(parts) / total_weight))

    if name == "ai" and not real_gpu_available:
        score = min(score, 900)

    return score


def category_label(score):
    if score >= 950:
        return "EXCELLENT"
    if score >= 850:
        return "GREAT"
    if score >= 700:
        return "GOOD"
    if score >= 550:
        return "LIMITED"
    return "POOR"
