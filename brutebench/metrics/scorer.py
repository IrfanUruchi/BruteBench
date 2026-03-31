def clamp(value, minimum=0, maximum=1000):
    return max(minimum, min(maximum, value))


def score_cpu(avg_ops, reference_ops):
    if avg_ops <= 0:
        return 0

    ratio = (avg_ops / reference_ops) / 3

    score = 1000 * (ratio ** 0.18)

    if ratio > 1.5:
        score *= 0.85
    if ratio > 2.0:
        score *= 0.75
    if ratio > 3.0:
        score *= 0.65

    return clamp(int(score))


def score_dev_cpu(avg_time, reference_time):
    if avg_time <= 0:
        return 0

    ratio = (reference_time / avg_time) / 2
    score = 1000 * (ratio ** 0.30)
    if ratio > 1.8:
        score *= 0.85
    if ratio > 2.5:
        score *= 0.75
    return clamp(int(score))


def score_memory(latency_spread, reference_spread):
    if latency_spread <= 0:
        return 0

    ratio = (reference_spread / latency_spread) / 1.8
    score = 1000 * (ratio ** 0.9)

    return clamp(int(score))


def score_system(avg_time, reference_time=2.0):
    if avg_time <= 0:
        return 0

    ratio = (reference_time / avg_time) / 2.5
    score = 1000 * (ratio ** 0.4)
    if ratio > 2.0:
        score *= 0.85
    if ratio > 3.0:
        score *= 0.70
    return clamp(int(score))


def score_gpu(avg_time, reference_time=1.5, backend="CPU"):
    if avg_time <= 0:
        return 0

    ratio = reference_time / avg_time
    score = 1000 * (ratio ** 0.7)

    if backend == "CPU":
        score *= 0.35
    elif backend == "MLX":
        score *= 0.13
    elif backend == "CUDA":
        score *= 1.0

    return clamp(int(score))


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

    penalty = 0

    if system_info:
        ram_gb = system_info.get("ram_gb", 0)
        cores = system_info.get("cpu_cores", 0)

        if ram_gb < 32:
            penalty += 0.06
        if ram_gb < 24:
            penalty += 0.15
        if ram_gb < 16:
            penalty += 0.20

        if cores < 12:
            penalty += 0.08
        if cores < 8:
            penalty += 0.12

    final = base_score * (1 - penalty)

    return int(final)


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


def category_score(name, cpu=None, dev=None, memory=None, system=None, gpu=None):
    cpu = cpu or 0
    dev = dev or 0
    memory = memory or 0
    system = system or 0
    gpu = gpu or 0

    parts = []

    if name == "mobile":
        if cpu is not None:
            parts.append(cpu * 0.45)
        if dev is not None:
            parts.append(dev * 0.45)

    elif name == "backend":
        if cpu is not None:
            parts.append(cpu * 0.4)
        if dev is not None:
            parts.append(dev * 0.4)
        if memory is not None:
            parts.append(memory * 0.2)

    elif name == "ai":
        parts.append(memory * 0.4)
        parts.append(system * 0.3)
        parts.append(gpu * 0.3)

    elif name == "systems":
        if cpu is not None:
            parts.append(cpu * 0.3)
        if dev is not None:
            parts.append(dev * 0.2)
        if memory is not None:
            parts.append(memory * 0.2)
        if system is not None:
            parts.append(system * 0.3)

    elif name == "data":
        if cpu is not None:
            parts.append(cpu * 0.2)
        if memory is not None:
            parts.append(memory * 0.4)
        if system is not None:
            parts.append(system * 0.4)

    elif name == "devops":
        parts.append(cpu * 0.3)
        parts.append(dev * 0.2)
        parts.append(memory * 0.3)
        parts.append(system * 0.2)

    if not parts:
        return 0

    return clamp(int(sum(parts)))


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