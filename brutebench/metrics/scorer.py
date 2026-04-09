import math


def clamp(value, minimum=0, maximum=1000):
    return max(minimum, min(maximum, value))


def _curve(ratio, exponent=0.85):
    if ratio <= 0:
        return 0.0
    return 1000 * (1 - math.exp(-(ratio ** exponent)))


def _stability_multiplier(stability):
    if stability is None:
        return 1.0
    normalized = clamp(stability, 0, 100) / 100
    return 0.82 + (normalized * 0.18)


def _blend(parts):
    valid = [(score, weight) for score, weight in parts if score is not None]
    if not valid:
        return 0
    total_weight = sum(weight for _, weight in valid)
    weighted_score = sum(score * weight for score, weight in valid)
    return clamp(int(weighted_score / total_weight))


def score_cpu(avg_ops, reference_ops, stability=None):
    if avg_ops <= 0 or reference_ops <= 0:
        return 0

    score = _curve(avg_ops / reference_ops, exponent=0.78)
    score *= _stability_multiplier(stability)
    return clamp(int(score))


def score_dev_cpu(avg_ops, reference_ops, stability=None):
    if avg_ops <= 0 or reference_ops <= 0:
        return 0

    score = _curve(avg_ops / reference_ops, exponent=0.82)
    score *= _stability_multiplier(stability)
    return clamp(int(score))


def score_memory(throughput_mb_s, latency_spread, reference_throughput, reference_spread, stability=None):
    if throughput_mb_s <= 0 or reference_throughput <= 0:
        return 0

    throughput_score = _curve(throughput_mb_s / reference_throughput, exponent=0.88)
    spread_score = _curve(reference_spread / max(latency_spread, 1.0), exponent=0.9)
    score = (throughput_score * 0.7) + (spread_score * 0.3)
    score *= _stability_multiplier(stability)
    return clamp(int(score))


def score_system(avg_ops, reference_ops=14, stability=None):
    if avg_ops <= 0 or reference_ops <= 0:
        return 0

    score = _curve(avg_ops / reference_ops, exponent=0.9)
    score *= _stability_multiplier(stability)
    return clamp(int(score))


def score_gpu(avg_gflops, accelerated=False, reference_gflops_accelerated=250, reference_gflops_fallback=0.3, backend="NONE"):
    if avg_gflops <= 0:
        return 0

    if accelerated:
        score = _curve(avg_gflops / reference_gflops_accelerated, exponent=0.72)
        if backend in {"MLX", "CUDA", "MPS"}:
            score *= 1.04
        return clamp(int(score))

    score = _curve(avg_gflops / reference_gflops_fallback, exponent=0.9) * 0.45
    return clamp(int(score))


def overall_score(cpu_score=None, dev_score=None, memory_score=None, system_score=None, gpu_score=None, system_info=None):
    base = _blend([
        (cpu_score, 0.24),
        (dev_score, 0.20),
        (memory_score, 0.18),
        (system_score, 0.23),
        (gpu_score, 0.15),
    ])

    if base <= 0:
        return 0

    adjustment = 0.0

    if system_info:
        ram_gb = float(system_info.get("ram_gb", 0) or 0)
        physical_cores = int(system_info.get("cpu_cores_physical", 0) or 0)

        if ram_gb < 8:
            adjustment -= 0.12
        elif ram_gb < 16:
            adjustment -= 0.06
        elif ram_gb >= 32:
            adjustment += 0.03

        if physical_cores < 4:
            adjustment -= 0.10
        elif physical_cores < 8:
            adjustment -= 0.04
        elif physical_cores >= 12:
            adjustment += 0.03

    return clamp(int(base * (1 + adjustment)))


def rating_label(score):
    if score >= 930:
        return "EXTREME"
    if score >= 850:
        return "WORKSTATION"
    if score >= 760:
        return "HIGH PERFORMANCE"
    if score >= 660:
        return "DEV PRO"
    if score >= 560:
        return "DEV READY"
    if score >= 460:
        return "LIGHT DEV"
    if score >= 340:
        return "LIMITED"
    return "STRAINED"


def category_score(name, cpu=None, dev=None, memory=None, system=None, gpu=None):
    if name == "mobile":
        return _blend([(cpu, 0.5), (dev, 0.5)])

    if name == "backend":
        return _blend([(cpu, 0.35), (dev, 0.35), (memory, 0.15), (system, 0.15)])

    if name == "ai":
        return _blend([(memory, 0.2), (system, 0.15), (gpu, 0.65)])

    if name == "systems":
        return _blend([(cpu, 0.25), (dev, 0.15), (memory, 0.2), (system, 0.4)])

    if name == "data":
        return _blend([(cpu, 0.15), (memory, 0.4), (system, 0.3), (gpu, 0.15)])

    if name == "devops":
        return _blend([(cpu, 0.25), (dev, 0.2), (memory, 0.25), (system, 0.3)])

    return 0


def category_label(score):
    if score >= 900:
        return "EXCELLENT"
    if score >= 780:
        return "GREAT"
    if score >= 640:
        return "GOOD"
    if score >= 480:
        return "LIMITED"
    return "POOR"
