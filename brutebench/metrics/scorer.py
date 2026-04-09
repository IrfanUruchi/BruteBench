def clamp(value, minimum=0, maximum=1000):
    return max(minimum, min(maximum, value))


def score_cpu(avg_ops, reference_ops):
    if avg_ops <= 0 or reference_ops <= 0:
        return 0

    ratio = (avg_ops / reference_ops) / 3.0
    score = 1000 * (ratio ** 0.18)

    if ratio > 3.0:
        score *= 0.65
    elif ratio > 2.0:
        score *= 0.75
    elif ratio > 1.5:
        score *= 0.85

    return clamp(int(score))


def score_dev_cpu(avg_time, reference_time):
    if avg_time <= 0 or reference_time <= 0:
        return 0

    ratio = (reference_time / avg_time) / 2.0
    score = 1000 * (ratio ** 0.30)

    if ratio > 2.5:
        score *= 0.75
    elif ratio > 1.8:
        score *= 0.85

    return clamp(int(score))


def score_memory(latency_spread, reference_spread):
    if latency_spread <= 0 or reference_spread <= 0:
        return 0

    ratio = (reference_spread / latency_spread) / 1.8
    score = 1000 * (ratio ** 0.9)

    return clamp(int(score))


def score_system(avg_time, reference_time=2.0):
    if avg_time <= 0 or reference_time <= 0:
        return 0

    ratio = (reference_time / avg_time) / 2.5
    score = 1000 * (ratio ** 0.4)

    if ratio > 3.0:
        score *= 0.70
    elif ratio > 2.0:
        score *= 0.85

    return clamp(int(score))


def score_gpu(avg_time, reference_time=1.5, backend="CPU"):
    if avg_time <= 0 or reference_time <= 0:
        return 0

    backend = (backend or "CPU").upper().strip()

    if avg_time < 0.20:
        return 0

    ratio = reference_time / avg_time

    if backend == "CPU":
        score = 300 * (ratio ** 0.5)
        return clamp(int(score), 0, 350)

    if backend == "MLX":
        score = 1000 * (ratio ** 0.7) * 0.50
        return clamp(int(score))

    if backend == "CUDA":
        score = 1000 * (ratio ** 0.7)
        return clamp(int(score))

    if backend == "ROCM":
        score = 1000 * (ratio ** 0.7)
        return clamp(int(score))

    if backend == "DIRECTML":
        score = 1000 * (ratio ** 0.65) * 0.90
        return clamp(int(score))

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
            penalty += 0.20
        elif ram_gb < 24:
            penalty += 0.15
        elif ram_gb < 32:
            penalty += 0.06

        if cores < 8:
            penalty += 0.12
        elif cores < 12:
            penalty += 0.08

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
    """
    Category scoring with proper missing-value handling.
    AI category:
    - if GPU really ran -> use GPU
    - if GPU did not run / fallback only -> shift weight toward CPU/system/memory
    """
    name = (name or "").lower().strip()
    gpu_backend = (gpu_backend or "").upper().strip()

    parts = []
    total_weight = 0.0

    def add_part(value, weight):
        nonlocal total_weight
        if value is not None:
            parts.append(value * weight)
            total_weight += weight

    if name == "mobile":
        add_part(cpu, 0.45)
        add_part(dev, 0.45)

    elif name == "backend":
        add_part(cpu, 0.40)
        add_part(dev, 0.40)
        add_part(memory, 0.20)

    elif name == "ai":
        real_gpu_available = (
            gpu is not None
            and gpu > 0
            and gpu_ran
            and gpu_backend not in ("", "CPU")
        )

        if real_gpu_available:
            add_part(memory, 0.35)
            add_part(system, 0.25)
            add_part(cpu, 0.10)
            add_part(gpu, 0.30)
        else:
        
            add_part(cpu, 0.35)
            add_part(memory, 0.35)
            add_part(system, 0.20)
            add_part(dev, 0.10)

    elif name == "systems":
        add_part(cpu, 0.30)
        add_part(dev, 0.20)
        add_part(memory, 0.20)
        add_part(system, 0.30)

    elif name == "data":
        add_part(cpu, 0.20)
        add_part(memory, 0.40)
        add_part(system, 0.40)

    elif name == "devops":
        add_part(cpu, 0.30)
        add_part(dev, 0.20)
        add_part(memory, 0.30)
        add_part(system, 0.20)

    if total_weight == 0:
        return 0

    return clamp(int(sum(parts) / total_weight))


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
