from brutebench.config import SCORE_REFERENCES
from brutebench.engine.result import BenchmarkResult
from brutebench.metrics.scorer import (
    category_label,
    category_score,
    overall_score,
    rating_label,
    score_cpu,
    score_dev_cpu,
    score_gpu,
    score_memory,
    score_system,
)
from brutebench.system.info import get_system_info
from brutebench.system.limits import build_workload_plan
from brutebench.utils.logger import log, section
from brutebench.workloads.cpu import CPUWorkload
from brutebench.workloads.dev_cpu import DevCPUWorkload
from brutebench.workloads.gpu import GPUWorkload
from brutebench.workloads.memory import MemoryWorkload
from brutebench.workloads.system import SystemWorkload


def _selected_benchmarks(args):
    if args.all:
        return ["cpu", "memory", "gpu", "cpu-dev", "system"]

    selected = []
    if args.cpu:
        selected.append("cpu")
    if args.memory:
        selected.append("memory")
    if args.gpu:
        selected.append("gpu")
    if args.cpu_dev:
        selected.append("cpu-dev")
    if getattr(args, "system", False):
        selected.append("system")
    return selected


def _device_summary(system_info, plan):
    section("Device Profile")
    print(f"OS         {system_info['os']} {system_info['release']}")
    print(f"Arch       {system_info['arch']}")
    print(f"CPU        {system_info['cpu_name']}")
    print(
        f"Cores      {system_info['cpu_cores_physical']} physical / "
        f"{system_info['cpu_cores_logical']} logical"
    )

    if system_info.get("cpu_frequency_ghz"):
        print(f"CPU Clock  {system_info['cpu_frequency_ghz']:.2f} GHz")

    print(
        f"Memory     {system_info['ram_gb']:.2f} GB total / "
        f"{system_info['available_ram_gb']:.2f} GB available"
    )
    print(f"Load       {system_info['ram_usage_percent']:.1f}% RAM in use")

    gpu_devices = system_info.get("gpu_devices") or []
    accelerators = system_info.get("accelerators") or []
    print(f"GPU        {', '.join(gpu_devices) if gpu_devices else 'No dedicated GPU detected'}")
    print(f"Accel      {', '.join(accelerators) if accelerators else 'No GPU runtime detected'}")
    print(f"Tier       {plan['device_class']} ({plan['device_scale']:.2f}x benchmark scale)")


def _memory_behavior(spread):
    if spread < 1.4:
        return "Stable"
    if spread < 2.0:
        return "Moderate pressure"
    return "Heavy pressure"


def _latency_behavior(spread):
    if spread < 1.1:
        return "Very stable"
    if spread < 1.25:
        return "Stable"
    return "Variable"


def _system_suggestion(weakest):
    if weakest == "AI":
        return "Increase accelerator support or memory capacity for heavier ML workloads"
    if weakest == "Data":
        return "Improve memory bandwidth and storage throughput for data-heavy workflows"
    if weakest == "Systems":
        return "Increase sustained CPU performance for build and low-level toolchain work"
    if weakest == "DevOps":
        return "Aim for more balanced CPU and memory headroom for concurrency"
    if weakest == "Backend":
        return "Faster CPU throughput will help with compile and service workloads"
    return "System balance looks solid for everyday development"


def run_benchmark(args):
    repeat = max(1, getattr(args, "repeat", 1))
    selected = _selected_benchmarks(args)

    if not selected:
        log("No benchmark selected. Use --cpu / --memory / --gpu / --cpu-dev / --system / --all")
        return

    system_info = get_system_info()
    profile_name = getattr(args, "profile", "standard")
    plan = build_workload_plan(profile_name, system_info)
    gpu_only = selected == ["gpu"]
    show_categories = (len(selected) >= 3) and not gpu_only

    _device_summary(system_info, plan)

    all_scores = []
    category_totals = {
        "mobile": 0,
        "backend": 0,
        "systems": 0,
        "data": 0,
        "llm": 0,
        "devops": 0,
    }

    for run_index in range(repeat):
        print(f"\n=== RUN {run_index + 1}/{repeat} ===")

        cpu_score_value = None
        memory_score_value = None
        dev_score_value = None
        system_score_value = None
        gpu_score_value = None

        result_store = BenchmarkResult()
        result_store.add("device", system_info)
        result_store.add("profile", plan)
        result_store.add("selected", selected)

        for task in selected:
            if task == "cpu":
                section("CPU Benchmark")
                result = CPUWorkload(
                    rounds=plan["cpu_rounds"],
                    units=plan["cpu_units"],
                    span=plan["cpu_span"],
                    processes=plan["cpu_processes"],
                ).execute()

                cpu_score_value = score_cpu(
                    result["avg_ops"],
                    SCORE_REFERENCES["cpu_ops"],
                    stability=result["stability"],
                )

                print("\nCPU Workload")
                print(f"Avg       {result['avg_time']:.2f}s")
                print(f"Ops/sec   {int(result['avg_ops'])}")
                print(f"Workers   {result['processes']}")
                print(f"Stability {result['stability']:.1f}%")
                print(f"Score     {cpu_score_value}")

                result["score"] = cpu_score_value
                result_store.add("cpu", result)

            elif task == "memory":
                section("Memory Benchmark")
                result = MemoryWorkload(
                    target_mb=plan["memory_target_mb"],
                    chunk_mb=plan["memory_chunk_mb"],
                    floor_mb=plan["memory_floor_mb"],
                ).execute()

                spread = result["latency_spread"]
                memory_score_value = score_memory(
                    result["throughput_mb_s"],
                    spread,
                    SCORE_REFERENCES["memory_throughput"],
                    SCORE_REFERENCES["memory_spread"],
                    stability=result["stability"],
                )

                print("\nMemory Workload")
                print(f"Target     {result['target_mb']} MB")
                print(f"Allocated  {result['total_mb']} MB")
                print(f"Chunks     {result['chunks']}")
                print(f"Throughput {result['throughput_mb_s']:.2f} MB/s")
                print(f"Latency    {spread:.2f}x ({_memory_behavior(spread)})")
                print(f"Stability  {result['stability']:.1f}%")
                print(f"Stop       {result['stop_reason']}")
                print(f"Score      {memory_score_value}")

                result["score"] = memory_score_value
                result_store.add("memory", result)

            elif task == "cpu-dev":
                section("Dev CPU Benchmark")
                result = DevCPUWorkload(
                    rounds=plan["dev_rounds"],
                    iterations=plan["dev_iterations"],
                ).execute()

                spread = result["max_time"] / result["min_time"] if result["min_time"] > 0 else 1.0
                dev_score_value = score_dev_cpu(
                    result["avg_ops"],
                    SCORE_REFERENCES["dev_ops"],
                    stability=result["stability"],
                )

                print("\nDev CPU Workload")
                print(f"Avg       {result['avg_time']:.2f}s")
                print(f"Tasks/sec {int(result['avg_ops'])}")
                print(f"Latency   {spread:.2f}x ({_latency_behavior(spread)})")
                print(f"Stability {result['stability']:.1f}%")
                print(f"Score     {dev_score_value}")

                result["score"] = dev_score_value
                result_store.add("dev_cpu", result)

            elif task == "system":
                section("System Benchmark")
                result = SystemWorkload(
                    rounds=plan["system_rounds"],
                    file_count=plan["system_files"],
                    payload_kb=plan["system_payload_kb"],
                ).execute()

                system_score_value = score_system(
                    result["avg_ops"],
                    reference_ops=SCORE_REFERENCES["system_ops"],
                    stability=result["stability"],
                )

                print("\nSystem Workload")
                print(f"Avg       {result['avg_time']:.2f}s")
                print(f"MB/sec    {result['avg_ops']:.2f}")
                print(f"Stability {result['stability']:.1f}%")
                print(f"Score     {system_score_value}")

                result["score"] = system_score_value
                result_store.add("system", result)

            elif task == "gpu":
                section("GPU Benchmark")
                result = GPUWorkload(
                    rounds=plan["gpu_rounds"],
                    size=plan["gpu_size"],
                    iters=plan["gpu_iters"],
                ).execute()

                gpu_score_value = score_gpu(
                    result["avg_gflops"],
                    accelerated=result["accelerated"],
                    reference_gflops_accelerated=SCORE_REFERENCES["gpu_gflops_accelerated"],
                    reference_gflops_fallback=SCORE_REFERENCES["gpu_gflops_fallback"],
                    backend=result.get("backend", "NONE"),
                )

                print("\nGPU Workload")
                print(f"Backend   {result['backend']}")
                print(f"Avg       {result['avg_time']:.2f}s")
                print(f"Min       {result['min_time']:.2f}s")
                print(f"Max       {result['max_time']:.2f}s")
                print(f"GFLOPS    {result['avg_gflops']:.3f}")
                print(f"Score     {gpu_score_value}")

                result["score"] = gpu_score_value
                result_store.add("gpu", result)

        final_score = overall_score(
            cpu_score=cpu_score_value,
            dev_score=dev_score_value,
            memory_score=memory_score_value,
            system_score=system_score_value,
            gpu_score=gpu_score_value,
            system_info=system_info,
        )

        result_store.add(
            "overall",
            {
                "score": final_score,
                "rating": rating_label(final_score) if final_score > 0 else "N/A",
            },
        )

        file_path = result_store.save()

        if final_score > 0:
            print("\n=== OVERALL SCORE ===")
            print(f"BruteBench Score: {final_score}")
            print(f"Rating: {rating_label(final_score)}")
            all_scores.append(final_score)

            if show_categories:
                category_totals["mobile"] += category_score("mobile", cpu=cpu_score_value, dev=dev_score_value)
                category_totals["backend"] += category_score(
                    "backend",
                    cpu=cpu_score_value,
                    dev=dev_score_value,
                    memory=memory_score_value,
                    system=system_score_value,
                )
                category_totals["systems"] += category_score(
                    "systems",
                    cpu=cpu_score_value,
                    dev=dev_score_value,
                    memory=memory_score_value,
                    system=system_score_value,
                )
                category_totals["data"] += category_score(
                    "data",
                    cpu=cpu_score_value,
                    memory=memory_score_value,
                    system=system_score_value,
                    gpu=gpu_score_value,
                )
                category_totals["llm"] += category_score(
                    "ai",
                    memory=memory_score_value,
                    system=system_score_value,
                    gpu=gpu_score_value,
                )
                category_totals["devops"] += category_score(
                    "devops",
                    cpu=cpu_score_value,
                    dev=dev_score_value,
                    memory=memory_score_value,
                    system=system_score_value,
                )

        print(f"\nSaved results -> {file_path}")

    if not all_scores:
        return

    avg_score = sum(all_scores) / len(all_scores)

    print("\n=== FINAL SCORE ===")
    print(f"Score    {int(avg_score)}")
    print(f"Rating   {rating_label(avg_score)}")

    if not show_categories:
        return

    print("\n=== USE CASE PERFORMANCE ===")

    count = len(all_scores)
    mobile = category_totals["mobile"] / count
    backend = category_totals["backend"] / count
    systems = category_totals["systems"] / count
    data = category_totals["data"] / count
    ai = category_totals["llm"] / count
    devops = category_totals["devops"] / count

    print(f"Mobile Dev        {category_label(mobile):<9} ({int(mobile)})")
    print(f"Backend Dev       {category_label(backend):<9} ({int(backend)})")
    print(f"Systems           {category_label(systems):<9} ({int(systems)})")
    print(f"Data / Pipelines  {category_label(data):<9} ({int(data)})")
    print(f"DevOps            {category_label(devops):<9} ({int(devops)})")
    print(f"AI / ML           {category_label(ai):<9} ({int(ai)})")

    print("\n=== SYSTEM INSIGHTS ===")

    categories = {
        "Mobile": mobile,
        "Backend": backend,
        "Systems": systems,
        "Data": data,
        "DevOps": devops,
        "AI": ai,
    }

    weakest = min(categories, key=categories.get)
    strongest = max(categories, key=categories.get)

    print(f"Strongest Area: {strongest}")
    print(f"Bottleneck: {weakest}")
    print(f"Suggestion: {_system_suggestion(weakest)}")
