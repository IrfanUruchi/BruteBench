from brutebench.utils.logger import section, log
from brutebench.workloads.cpu import CPUWorkload
from brutebench.workloads.memory import MemoryWorkload
from brutebench.workloads.dev_cpu import DevCPUWorkload
from brutebench.workloads.gpu import GPUWorkload
from brutebench.metrics.scorer import (
    score_cpu,
    score_dev_cpu,
    score_memory,
    score_gpu,
    overall_score,
    rating_label,
    category_score,
    category_label,
)
from brutebench.workloads.system import SystemWorkload
from brutebench.metrics.scorer import score_system
from brutebench.config import (
    CPU_SCORE_REFERENCE_OPS,
    DEV_SCORE_REFERENCE_TIME,
    MEMORY_SCORE_REFERENCE_SPREAD,
)
from brutebench.config import PROFILES
from brutebench.engine.result import BenchmarkResult
from brutebench.system.info import get_system_info


def run_benchmark(args):
    repeat = getattr(args, "repeat", 1)
    selected = []

    if args.all:
        selected = ["cpu", "memory", "gpu", "cpu-dev", "system"]
    else:
        if args.cpu:
            selected.append("cpu")
        if args.memory:
            selected.append("memory")
        if args.gpu:
            selected.append("gpu")
        if args.cpu_dev:
            selected.append("cpu-dev")

    if not selected:
        log("No benchmark selected. Use --cpu / --memory / --gpu / --cpu-dev / --all")
        return

    gpu_only = selected == ["gpu"]

    profile_name = getattr(args, "profile", "standard")
    profile = PROFILES.get(profile_name, PROFILES["standard"])

    all_scores = []
    category_totals = {
        "mobile": 0,
        "backend": 0,
        "systems": 0,
        "data": 0,
        "llm": 0,
        "devops": 0,
    }

    for i in range(repeat):
        print(f"\n=== RUN {i+1}/{repeat} ===")

        cpu_score_value = None
        memory_score_value = None
        dev_score_value = None
        system_score_value = None
        gpu_score_value = None

        result_store = BenchmarkResult()
        result_store.add("system", get_system_info())

        for task in selected:
            if task == "cpu":
                section("CPU Benchmark")
                result = CPUWorkload(
                    rounds=profile["cpu_rounds"],
                    task_size=profile["cpu_task_size"]
                ).execute()
                cpu_score_value = score_cpu(result["avg_ops"], CPU_SCORE_REFERENCE_OPS)

                print("\nCPU Workload")
                print(f"Avg       {result['avg_time']:.2f}s")
                print(f"Ops/sec   {int(result['avg_ops'])}")
                print(f"Stability {result['stability']:.1f}%")
                print(f"Score     {cpu_score_value}")

                result_store.add("cpu", {
                    "avg_time": result["avg_time"],
                    "ops": result["avg_ops"],
                    "score": cpu_score_value,
                })

            elif task == "memory":
                section("Memory Benchmark")
                result = MemoryWorkload(
                    max_percent=profile["memory_max_percent"]
                ).execute()

                spread = result["latency_spread"]
                memory_score_value = score_memory(spread, MEMORY_SCORE_REFERENCE_SPREAD)

                if spread < 2:
                    behavior = "Stable"
                elif spread < 4:
                    behavior = "Moderate pressure"
                else:
                    behavior = "Heavy pressure"

                print("\nMemory Workload")
                print(f"Allocated  {result['total_mb']} MB")
                print(f"Chunks     {result['chunks']}")
                print(f"Latency    {spread:.2f}x ({behavior})")
                print(f"Avg alloc  {result['avg_alloc_time']:.4f}s")
                print(f"Score      {memory_score_value}")

                result_store.add("memory", {
                    "allocated_mb": result["total_mb"],
                    "latency_spread": spread,
                    "score": memory_score_value,
                })

            elif task == "cpu-dev":
                section("Dev CPU Benchmark")
                result = DevCPUWorkload(
                    iterations=profile["dev_iterations"]
                ).execute()

                spread = result["max_time"] / result["min_time"] if result["min_time"] > 0 else 1
                dev_score_value = score_dev_cpu(result["avg_time"], DEV_SCORE_REFERENCE_TIME)

                if spread < 1.2:
                    behavior = "Very stable"
                elif spread < 1.5:
                    behavior = "Stable"
                else:
                    behavior = "Variable"

                print("\nDev CPU Workload")
                print(f"Avg       {result['avg_time']:.2f}s")
                print(f"Latency   {spread:.2f}x ({behavior})")
                print(f"Stability {result['stability']:.1f}%")
                print(f"Score     {dev_score_value}")

                result_store.add("dev_cpu", {
                    "avg_time": result["avg_time"],
                    "score": dev_score_value,
                })

            elif task == "system":
                section("System Benchmark")

                result = SystemWorkload().execute()

                system_score_value = score_system(result["avg_time"])

                print("\nSystem Workload")
                print(f"Avg       {result['avg_time']:.2f}s")
                print(f"Score     {system_score_value}")

                result_store.add("system", {
                    "avg_time": result["avg_time"],
                    "score": system_score_value,
                })

            elif task == "gpu":
                section("GPU Benchmark")

                result = GPUWorkload().execute()

                gpu_score_value = score_gpu(
                    result["avg_time"],
                    backend=result.get("backend", "CPU"),
                )

                print("\nGPU Workload")
                print(f"Backend   {result['backend']}")
                print(f"Avg       {result['avg_time']:.2f}s")
                print(f"Min       {result['min_time']:.2f}s")
                print(f"Max       {result['max_time']:.2f}s")
                print(f"Score     {gpu_score_value}")

                result_store.add("gpu", {
                    "avg_time": result["avg_time"],
                    "min_time": result["min_time"],
                    "max_time": result["max_time"],
                    "backend": result["backend"],
                    "score": gpu_score_value,
                })


        final_score = overall_score(
            cpu_score=cpu_score_value,
            dev_score=dev_score_value,
            memory_score=memory_score_value,
            system_score=system_score_value,
            gpu_score=gpu_score_value,
            system_info=get_system_info(),
        )

        if final_score > 0:
            all_scores.append(final_score)

            if not gpu_only:
                category_totals["mobile"] += category_score("mobile", cpu=cpu_score_value, dev=dev_score_value)
                category_totals["backend"] += category_score("backend", cpu=cpu_score_value, dev=dev_score_value, memory=memory_score_value)
                category_totals["systems"] += category_score("systems", cpu=cpu_score_value, dev=dev_score_value, memory=memory_score_value, system=system_score_value)
                category_totals["data"] += category_score("data", cpu=cpu_score_value, memory=memory_score_value, system=system_score_value)
                category_totals["llm"] += category_score("ai", memory=memory_score_value, system=system_score_value, gpu=gpu_score_value)
                category_totals["devops"] += category_score("devops", cpu=cpu_score_value, dev=dev_score_value, memory=memory_score_value, system=system_score_value)

                print("\n=== OVERALL SCORE ===")
                print(f"BruteBench Score: {final_score}")
                print(f"Rating: {rating_label(final_score)}")

                result_store.add("overall", {
                    "score": final_score,
                    "rating": rating_label(final_score),
                })

                file_path = result_store.save()
                print(f"\nSaved results → {file_path}")

            else:
                return


    if all_scores:
        avg_score = sum(all_scores) / len(all_scores)

        print("\n=== FINAL SCORE ===")
        print(f"Score    {int(avg_score)}")
        print(f"Rating   {rating_label(avg_score)}")

        print("\n=== USE CASE PERFORMANCE ===")

        count = len(all_scores)

        mobile = category_totals["mobile"] / count
        backend = category_totals["backend"] / count
        systems = category_totals["systems"] / count
        data = category_totals["data"] / count
        ai = category_totals["llm"] / count
        devops = category_totals["devops"] / count

        print(f"Mobile Dev        {category_label(mobile):<6} ({int(mobile)})")
        print(f"Backend Dev       {category_label(backend):<6} ({int(backend)})")
        print(f"Systems           {category_label(systems):<6} ({int(systems)})")
        print(f"Data / Pipelines  {category_label(data):<6} ({int(data)})")
        print(f"DevOps            {category_label(devops):<6} ({int(devops)})")
        print(f"AI / ML           {category_label(ai):<6} ({int(ai)})")

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

        if weakest == "AI":
            print("Suggestion: Increase RAM or GPU capacity for AI workloads")
        elif weakest == "Data":
            print("Suggestion: More RAM recommended")
        elif weakest == "Systems":
            print("Suggestion: Improve CPU or overall system balance")
        elif weakest == "DevOps":
            print("Suggestion: Balance CPU and memory for better concurrency")
        else:
            print("Suggestion: System is well balanced for most workloads")