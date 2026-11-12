# Mesa for Android Container — Engineering Documentation Directory

This directory contains the complete autonomous engineering record for the optimization of `mesa-for-android-container` on the Xiaomi Redmi Note 10 Pro (Qualcomm Snapdragon 732G / Adreno 618).

## Document Index

| Document | Description |
|---|---|
| [STATUS.md](STATUS.md) | Project phase status, completed tasks, and verified findings |
| [ENVIRONMENT_DISCOVERY.md](ENVIRONMENT_DISCOVERY.md) | Phase 0 Hardware forensics, kernel telemetry, and ecosystem mapping |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Phase 1 Codebase architecture audit and bottleneck identification |
| [BASELINE.md](BASELINE.md) | Phase 2 Controlled baseline measurements, telemetry, and per-scene breakdown |
| [EXPERIMENT_REPORT.md](EXPERIMENT_REPORT.md) | Phase 3 Experimental research on BO allocations, GMEM vs Sysmem, and stack safety |
| [OPTIMIZATION_LOG.md](OPTIMIZATION_LOG.md) | Phase 4 Detailed log of all adopted code modifications and reasons |
| [BENCHMARKS.md](BENCHMARKS.md) | Phase 5 Comprehensive before-and-after benchmarks and statistical comparisons |
| [THERMAL_ANALYSIS.md](THERMAL_ANALYSIS.md) | Thermal dissipation, governor scaling, and throttling margins |
| [BATTERY_ANALYSIS.md](BATTERY_ANALYSIS.md) | Power draw (Watts), energy consumed (Joules), and performance-per-watt |
| [REGRESSION_REPORT.md](REGRESSION_REPORT.md) | Edge cases, safety checks, and rejected approaches |
| [ECOSYSTEM_ANALYSIS.md](ECOSYSTEM_ANALYSIS.md) | Cross-project integration analysis for neighboring repositories |
| [FINAL_REPORT.md](FINAL_REPORT.md) | Phase 8 Final executive deliverable covering both perspectives |

## Directory Structure
- `benchmarks/raw/`: Raw JSON benchmark results with 200 ms interval telemetry.
- `experiments/`: Standalone experimental microbenchmarks (`experiment_001_bo_alloc`).
- `scripts/`: Automated telemetry collection and benchmarking harnesses (`run_benchmarks.py`).
