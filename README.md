# BruteBench

BruteBench is a lightweight system benchmarking tool designed to evaluate real-world performance for development workloads.  
Instead of relying on synthetic benchmarks, it measures practical performance by combining CPU, memory, system, and GPU workloads into a unified scoring model.

---

## Version

**v1.0.0 — Initial release (31 March 2026)**
**v1.0.1 — Updated release (04 April 2026)**
**v1.0.2 — Third release (27 April 2026)**

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


## GPU Acceleration (Optional but Recommended)

BruteBench supports GPU acceleration for AI and compute workloads.

Depending on your system, you may need to install additional libraries:

### NVIDIA (CUDA)
For NVIDIA GPUs, install PyTorch with CUDA support:

```bash
pip install torch torchvision torchaudio
```


Verify CUDA is working:


```python
import torch
print(torch.cuda.is_available())
```

Expected output: True

### Apple Silicon (MLX / MPS)

For Apple Silicon devices:

```bash
pip install mlx
pip install torch
```

### Fallback Behavior

If GPU runtimes are not available, BruteBench will automatically fall back to a CPU-based NumPy implementation.

In this case, GPU scores will not reflect actual GPU performance.

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

## Real System Examples

| CPU / System                              | Score        | Rating                    |
|-------------------------------------------|-------------|---------------------------|
| Intel Core Ultra 9 275hx (ROG Strix G16)  | ~794        | HIGH PERFORMANCE          |
| Apple M3 Pro (MacBook Pro 14")            | ~696        | DEV PRO                   |
| AMD Ryzen 7 7735HS (Lenovo Ideapad)       | ~560        | DEV READY                 |
| Intel i5-1145G7 (Dell Latitude 5420)      | ~525        | LIGHT DEV                 |

--- 

## Design 

BruteBench is built around three core principles:

- Practical over synthetic — focus on real workloads
- Balanced scoring — no single component dominates results
- Cross-platform consistency — comparable results across different architectures

--- 

## Licence

This project is licensed under the MIT License.
