# BruteBench

BruteBench is a lightweight system benchmarking tool designed to evaluate real-world performance for development workloads.  
Instead of relying on synthetic benchmarks, it measures practical performance by combining CPU, memory, system, and GPU workloads into a unified scoring model.

---

## Version

**v1.0.0 — Initial release (31 March 2026)**

---

## Purpose

BruteBench aims to provide a clear and realistic view of how a system performs under conditions similar to everyday engineering tasks.

It focuses on workloads such as:

- System programming
- Backend development
- Data processing
- AI / Machine Learning workloads

The goal is not to produce theoretical peak numbers, but to reflect how a machine behaves in real development scenarios.

---

## Features

- **CPU Benchmark**
  - Operations per second
  - Stability measurement

- **Development Workload Simulation**
  - Multi-round execution
  - Latency consistency tracking

- **Memory Benchmark**
  - Memory pressure testing
  - Allocation latency analysis

- **System Benchmark**
  - Mixed workload simulation
  - Overall system responsiveness

- **GPU Benchmark**
  - Apple Silicon (MLX)
  - NVIDIA CUDA
  - CPU fallback (cross-platform)

- **Use-Case Based Scoring**
  - Mobile Development
  - Backend Development
  - Systems Engineering
  - Data / Pipelines
  - DevOps
  - AI / Machine Learning

---

## Installation

```bash
git clone https://github.com/IrfanUruchi/BruteBench.git
cd BruteBench

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

---

## Usage

Run full benchmark:

```bash
brutebench --all --profile standard --repeat 3
```

### Run GPU-only benchmark

```bash
brutebench --gpu
```

--- 

## Example 


```bash
=== FINAL SCORE ===
Score    586
Rating   LIGHT DEV

=== USE CASE PERFORMANCE ===
Mobile Dev        GOOD    (782)
Backend Dev       GOOD    (781)
Systems           GOOD    (816)
Data / Pipelines  GOOD    (736)
DevOps            GOOD    (759)
AI / ML           LIMITED (667)

=== SYSTEM INSIGHTS ===
Strongest Area: Systems
Bottleneck: AI
Suggestion: Increase RAM or GPU capacity for AI workloads
```
(for m3 pro)

--- 

## Design 

BruteBench is built around three core principles:

- Practical over synthetic — focus on real workloads
- Balanced scoring — no single component dominates results
- Cross-platform consistency — comparable results across different architectures

--- 

## Licence

This project is licensed under the MIT License.
