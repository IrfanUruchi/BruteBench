PROFILES = {
    "quick": {
        "cpu_rounds": 3,
        "cpu_task_size": 500_000,
        "dev_iterations": 10000,
        "memory_max_percent": 60,
    },
    "standard": {
        "cpu_rounds": 5,
        "cpu_task_size": 2_000_000,
        "dev_iterations": 20000,
        "memory_max_percent": 70,
    },
    "stress": {
        "cpu_rounds": 8,
        "cpu_task_size": 4_000_000,
        "dev_iterations": 40000,
        "memory_max_percent": 80,
    },
}

CPU_SCORE_REFERENCE_OPS = 400000
DEV_SCORE_REFERENCE_TIME = 1.0
MEMORY_SCORE_REFERENCE_SPREAD = 4.0