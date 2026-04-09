import ctypes
import os
import platform
import re
import socket
import subprocess
from functools import lru_cache

try:
    import psutil
except Exception:
    psutil = None


def _run_command(command):
    try:
        return subprocess.check_output(
            command,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip()
    except Exception:
        return ""


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            return handle.read()
    except OSError:
        return ""


def _extract_meminfo_value(text, key):
    match = re.search(rf"^{key}:\s+(\d+)\s+kB", text, re.MULTILINE)
    if not match:
        return 0
    return int(match.group(1)) * 1024


def _parse_size_to_bytes(value):
    match = re.search(r"([\d.]+)\s*(TB|GB|MB|KB)", value.upper())
    if not match:
        return 0

    number = float(match.group(1))
    unit = match.group(2)
    scale = {
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4,
    }
    return int(number * scale[unit])


@lru_cache(maxsize=1)
def _darwin_hardware_profile():
    output = _run_command(["system_profiler", "SPHardwareDataType"])
    profile = {}

    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Chip:"):
            profile["cpu_name"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Processor Name:"):
            profile["cpu_name"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Total Number of Cores:"):
            value = stripped.split(":", 1)[1].strip()
            match = re.search(r"(\d+)", value)
            if match:
                profile["cpu_cores"] = int(match.group(1))
        elif stripped.startswith("Memory:"):
            value = stripped.split(":", 1)[1].strip()
            profile["memory_bytes"] = _parse_size_to_bytes(value)

    return profile


def get_memory_snapshot():
    if psutil:
        memory = psutil.virtual_memory()
        return {
            "total": int(memory.total),
            "available": int(memory.available),
            "percent": float(memory.percent),
        }

    system_name = platform.system()

    if system_name == "Darwin":
        total = int(_darwin_hardware_profile().get("memory_bytes") or 0)
        vm_stat = _run_command(["vm_stat"])
        available = 0
        page_size = 4096

        if vm_stat:
            page_size_match = re.search(r"page size of (\d+) bytes", vm_stat)
            if page_size_match:
                page_size = int(page_size_match.group(1))

            for label in (
                "Pages free",
                "Pages inactive",
                "Pages speculative",
                "Pages purgeable",
            ):
                match = re.search(rf"{re.escape(label)}:\s+(\d+)\.", vm_stat)
                if match:
                    available += int(match.group(1)) * page_size

        percent = ((total - available) / total * 100) if total and available else 0.0
        return {
            "total": total,
            "available": available,
            "percent": percent,
        }

    if system_name == "Linux":
        meminfo = _read_text("/proc/meminfo")
        total = _extract_meminfo_value(meminfo, "MemTotal")
        available = _extract_meminfo_value(meminfo, "MemAvailable")
        if not available:
            available = _extract_meminfo_value(meminfo, "MemFree")
        percent = ((total - available) / total * 100) if total and available else 0.0
        return {
            "total": total,
            "available": available,
            "percent": percent,
        }

    if system_name == "Windows":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        state = MEMORYSTATUSEX()
        state.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            return {
                "total": int(state.ullTotalPhys),
                "available": int(state.ullAvailPhys),
                "percent": float(state.dwMemoryLoad),
            }

    return {
        "total": 0,
        "available": 0,
        "percent": 0.0,
    }


def _cpu_counts():
    logical = os.cpu_count() or 1
    physical = 0

    if psutil:
        physical = psutil.cpu_count(logical=False) or 0
        logical = psutil.cpu_count(logical=True) or logical

    if not physical:
        system_name = platform.system()
        if system_name == "Darwin":
            profile = _darwin_hardware_profile()
            physical = int(profile.get("cpu_cores") or 0)
            logical = max(logical, physical)
        elif system_name == "Linux":
            lscpu = _run_command(["lscpu", "-p=Core"])
            if lscpu:
                cores = {
                    line.strip()
                    for line in lscpu.splitlines()
                    if line.strip() and not line.startswith("#")
                }
                physical = len(cores)
        elif system_name == "Windows":
            output = _run_command(
                ["wmic", "cpu", "get", "NumberOfCores,NumberOfLogicalProcessors"]
            )
            numbers = [int(value) for value in re.findall(r"\d+", output)]
            if len(numbers) >= 2:
                physical = numbers[0]
                logical = numbers[1]

    if not physical:
        physical = max(1, logical // 2)

    return physical, logical


def _cpu_name():
    system_name = platform.system()

    if system_name == "Darwin":
        name = _darwin_hardware_profile().get("cpu_name", "")
        if not name:
            name = _run_command(["sysctl", "-n", "hw.model"])
        if name:
            return name

    if system_name == "Linux":
        cpuinfo = _read_text("/proc/cpuinfo")
        for line in cpuinfo.splitlines():
            if line.lower().startswith("model name"):
                _, _, value = line.partition(":")
                return value.strip()

    if system_name == "Windows":
        name = _run_command(["wmic", "cpu", "get", "Name"])
        lines = [line.strip() for line in name.splitlines() if line.strip() and "Name" not in line]
        if lines:
            return lines[0]

    fallback = platform.processor() or platform.machine()
    return fallback or "Unknown CPU"


def _cpu_frequency_ghz():
    if psutil and psutil.cpu_freq():
        frequency = psutil.cpu_freq()
        if frequency and frequency.max:
            return round(frequency.max / 1000, 2)
        if frequency and frequency.current:
            return round(frequency.current / 1000, 2)

    system_name = platform.system()
    if system_name == "Darwin":
        frequency = _run_command(["sysctl", "-n", "hw.cpufrequency"])
        if frequency.isdigit():
            return round(int(frequency) / 1_000_000_000, 2)

    if system_name == "Linux":
        cpuinfo = _read_text("/proc/cpuinfo")
        match = re.search(r"cpu MHz\s+:\s+([\d.]+)", cpuinfo)
        if match:
            return round(float(match.group(1)) / 1000, 2)

    return 0.0


def _gpu_devices():
    devices = []

    nvidia = _run_command(["nvidia-smi", "-L"])
    if nvidia:
        for line in nvidia.splitlines():
            if line.strip():
                devices.append(line.split(" (UUID")[0].strip())

    system_name = platform.system()

    if system_name == "Darwin":
        profiler = _run_command(["system_profiler", "SPDisplaysDataType"])
        for line in profiler.splitlines():
            if "Chipset Model:" in line or "Graphics/Displays:" in line:
                _, _, value = line.partition(":")
                value = value.strip()
                if value and value not in devices:
                    devices.append(value)

    if system_name == "Linux":
        lspci = _run_command(["lspci"])
        for line in lspci.splitlines():
            if "VGA compatible controller" in line or "3D controller" in line or "Display controller" in line:
                value = line.split(": ", 1)[-1].strip()
                if value and value not in devices:
                    devices.append(value)

    if system_name == "Windows":
        output = _run_command(["wmic", "path", "win32_VideoController", "get", "Name"])
        for line in output.splitlines():
            value = line.strip()
            if value and value != "Name" and value not in devices:
                devices.append(value)

    return devices


def _available_accelerators():
    accelerators = []

    try:
        import mlx.core as mx

        _ = mx.default_device()
        accelerators.append("MLX")
    except Exception:
        pass

    try:
        import torch

        if torch.cuda.is_available():
            accelerators.append("CUDA")
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            accelerators.append("MPS")
    except Exception:
        pass

    return accelerators


def get_system_info():
    physical_cores, logical_cores = _cpu_counts()
    memory = get_memory_snapshot()
    gpu_devices = _gpu_devices()
    accelerators = _available_accelerators()

    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.version(),
        "release": platform.release(),
        "arch": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_name": _cpu_name(),
        "cpu_cores": logical_cores,
        "cpu_cores_logical": logical_cores,
        "cpu_cores_physical": physical_cores,
        "cpu_frequency_ghz": _cpu_frequency_ghz(),
        "ram_gb": round(memory["total"] / (1024 ** 3), 2) if memory["total"] else 0.0,
        "available_ram_gb": round(memory["available"] / (1024 ** 3), 2) if memory["available"] else 0.0,
        "ram_usage_percent": round(memory["percent"], 1),
        "gpu_devices": gpu_devices,
        "gpu_count": len(gpu_devices),
        "accelerators": accelerators,
    }
