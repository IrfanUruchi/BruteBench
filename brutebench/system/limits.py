from brutebench.config import PROFILES


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def device_scale(system_info):
    logical_cores = max(1, int(system_info.get("cpu_cores_logical") or system_info.get("cpu_cores") or 1))
    ram_gb = max(4.0, float(system_info.get("ram_gb") or 4.0))
    gpu_bonus = 0.08 if system_info.get("accelerators") else 0.0

    core_factor = min(logical_cores, 16) / 8
    memory_factor = min(ram_gb, 64) / 16
    scale = ((core_factor * 0.6) + (memory_factor * 0.4)) ** 0.5
    scale += gpu_bonus

    return round(_clamp(scale, 0.75, 1.5), 2)


def device_class(system_info):
    logical_cores = int(system_info.get("cpu_cores_logical") or system_info.get("cpu_cores") or 1)
    ram_gb = float(system_info.get("ram_gb") or 0.0)
    accelerators = system_info.get("accelerators") or []

    if logical_cores >= 16 and ram_gb >= 32 and accelerators:
        return "workstation"
    if logical_cores >= 8 and ram_gb >= 16:
        return "performance"
    if logical_cores >= 4 and ram_gb >= 8:
        return "balanced"
    return "light"


def build_workload_plan(profile_name, system_info):
    profile = PROFILES.get(profile_name, PROFILES["standard"])
    scale = device_scale(system_info)
    logical_cores = max(1, int(system_info.get("cpu_cores_logical") or system_info.get("cpu_cores") or 1))
    physical_cores = max(1, int(system_info.get("cpu_cores_physical") or max(1, logical_cores // 2)))
    available_ram_mb = max(
        512,
        int((float(system_info.get("available_ram_gb") or system_info.get("ram_gb") or 4.0)) * 1024),
    )

    cpu_processes = min(logical_cores, max(1, physical_cores), profile["cpu_workers_cap"])
    memory_target_mb = int(min(profile["memory_cap_mb"] * scale, available_ram_mb * profile["memory_fraction"]))
    memory_target_mb = max(profile["memory_chunk_mb"] * 2, memory_target_mb)
    memory_target_mb = min(memory_target_mb, max(profile["memory_chunk_mb"] * 2, int(available_ram_mb * 0.25)))
    memory_chunk_mb = min(profile["memory_chunk_mb"], max(4, memory_target_mb // 8))

    gpu_size = max(64, int(round(profile["gpu_size"] * min(scale, 1.25) / 16) * 16))
    gpu_iters = max(2, int(round(profile["gpu_iters"] * scale)))

    return {
        "profile": profile_name,
        "device_scale": scale,
        "device_class": device_class(system_info),
        "cpu_rounds": profile["cpu_rounds"],
        "cpu_units": max(4, int(round(profile["cpu_units"] * scale))),
        "cpu_span": max(192, int(round(profile["cpu_span"] * scale))),
        "cpu_processes": cpu_processes,
        "dev_rounds": profile["dev_rounds"],
        "dev_iterations": max(200, int(round(profile["dev_iterations"] * scale))),
        "memory_target_mb": memory_target_mb,
        "memory_chunk_mb": memory_chunk_mb,
        "memory_floor_mb": profile["memory_floor_mb"],
        "system_rounds": profile["system_rounds"],
        "system_files": max(8, int(round(profile["system_files"] * scale))),
        "system_payload_kb": max(8, int(round(profile["system_payload_kb"] * scale))),
        "gpu_rounds": profile["gpu_rounds"],
        "gpu_size": gpu_size,
        "gpu_iters": gpu_iters,
    }
