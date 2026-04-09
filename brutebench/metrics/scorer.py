import math


def clamp(value, minimum=0, maximum=1000):
    return max(minimum, min(maximum, value))


def soft_score(ratio, exponent=0.5, baseline=1.0):
    if ratio <= 0:
        return 0
    adjusted = ratio / baseline
    if adjusted <= 0:
        return 0
    return 1000 * (adjusted ** exponent)


def damp_high_end(score, ratio, tiers):
    for threshold, multiplier in tiers:
        if ratio > threshold:
            score *= multiplier
    return score

def score_cpu(avg_ops, reference_ops):
    if avg_ops <= 0 or reference_ops <= 0:
        return 0

    ratio = avg_ops / reference_ops

    score = 1000 * (ratio ** 0.30)

    if ratio > 1.4:
        score *= 0.94
    if ratio > 2.0:
        score *= 0.86
    if ratio > 2.8:
        score *= 0.78
    if ratio > 3.5:
        score *= 0.70

    return clamp(int(score))


def score_dev_cpu(avg_time, reference_time):
    if avg_time <= 0 or reference_time <= 0:
        return 0

    ratio = reference_time / avg_time

    score = 1000 * (ratio ** 0.32)

    if ratio > 1.5:
        score *= 0.95
    if ratio > 2.2:
        score *= 0.87
    if ratio > 3.0:
        score *= 0.78

    return clamp(int(score))


def score_memory(latency_spread, reference_spread):
    if latency_spread <= 0 or reference_spread <= 0:
        return 0

    ratio = reference_spread / latency_spread
    score = soft_score(ratio, exponent=0.62, baseline=0.95)
    score = damp_high_end(score, ratio, [
        (1.8, 0.96),
        (2.5, 0.90),
        (3.5, 0.84),
    ])

    return clamp(int(score))


def score_system(avg_time, reference_time=2.0):
    if avg_time <= 0 or reference_time <= 0:
        return 0

    ratio = reference_time / avg_time
    score = soft_score(ratio, exponent=0.50, baseline=0.95)
    score = damp_high_end(score, ratio, [
        (2.0, 0.94),
        (2.8, 0.88),
        (3.8, 0.82),
    ])

    return clamp(int(score))


def score_gpu(avg_time, reference_time=1.5, backend="CPU"):
    if avg_time <= 0 or reference_time <= 0:
        return 0

    backend = (backend or "CPU").upper().strip()

    if avg_time < 0.20:
        return 0

    ratio = reference_time / avg_time
    norm = math.log1p(max(ratio, 0)) / math.log1p(12.0)

    if backend == "CPU":
        return clamp(int(260 * norm), 0, 300)

    if backend == "MLX":
        return clamp(int(880 * norm))

    if backend == "CUDA":
        return clamp(int(1000 * norm))

    if backend == "ROCM":
        return clamp(int(970 * norm))

    if backend == "DIRECTML":
        return clamp(int(820 * norm))

    return 0


def overall_score(cpu_score=None, dev_score=None, memory_score=None, system_score=None, gpu_score=None, system_info=None):
    parts = []

    if cpu_score is not None:
        parts.append((cpu_score, 0.28))
    if dev_score is not None:
        parts.append((dev_score, 0.27))
    if memory_score is not None:
        parts.append((memory_score, 0.12))
    if system_score is not None:
        parts.append((system_score, 0.23))
    if gpu_score is not None:
        parts.append((gpu_score, 0.10))

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
            penalty += 0.10
        elif ram_gb < 24:
            penalty += 0.05

        if cores < 6:
            penalty += 0.10
        elif cores < 8:
            penalty += 0.05

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
        gpu is not None
        and gpu >= 320
        and gpu_ran
        and gpu_backend not in ("", "CPU")
    )

    if name == "mobile":
        add(cpu, 0.52)
        add(dev, 0.48)

    elif name == "backend":
        add(cpu, 0.40)
        add(dev, 0.35)
        add(memory, 0.10)
        add(system, 0.15)

    elif name == "ai":
        if real_gpu_available:
            add(gpu, 0.42)
            add(memory, 0.22)
            add(system, 0.16)
            add(cpu, 0.12)
            add(dev, 0.08)
        else:
            add(cpu, 0.38)
            add(memory, 0.22)
            add(system, 0.20)
            add(dev, 0.20)

    elif name == "systems":
        add(cpu, 0.28)
        add(system, 0.34)
        add(memory, 0.20)
        add(dev, 0.18)

    elif name == "data":
        add(memory, 0.36)
        add(system, 0.29)
        add(cpu, 0.20)
        add(dev, 0.15)

    elif name == "devops":
        add(cpu, 0.30)
        add(system, 0.24)
        add(memory, 0.20)
        add(dev, 0.26)

    if total_weight == 0:
        return 0

    score = clamp(int(sum(parts) / total_weight))

    if name == "ai" and not real_gpu_available:
        score = min(score, 780)

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
