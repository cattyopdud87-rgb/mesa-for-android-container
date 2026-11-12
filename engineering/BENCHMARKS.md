# BENCHMARKS & STATISTICAL REPRODUCIBILITY

**Document ID:** ENG-BENCH-MESA-20261110  
**Target Device:** Xiaomi Redmi Note 10 Pro (`sweet` / `sweetin`, M2101K6P)  
**Target Repository:** `/data/data/com.termux/files/home/development/repo/mesa-for-android-container/`  
**Date:** 2026-11-10  

---

## 1. Benchmark Methodology & Hardware Environment

- **Device:** Xiaomi Redmi Note 10 Pro (`sweet` / `sweetin`)
- **SoC:** Qualcomm Snapdragon 732G (SM6150)
- **CPU:** 8 cores (2× Kryo 470 Gold @ 2.304 GHz, 6× Kryo 470 Silver @ 1.804 GHz)
- **GPU:** Qualcomm Adreno 618 (`/dev/kgsl-3d0`)
- **Memory:** 5.4 GiB LPDDR4X physical RAM + 3.0 GiB ZRAM swap (LZ4)
- **Operating System:** Android 15 (LineageOS-family "reforge", Kernel 4.14.357)
- **Container Environment:** Droidspaces `mikasa` (Arch Linux ARM64, KDE Plasma 6.8 Wayland)
- **Telemetry Harness:** `engineering/scripts/run_benchmarks.py` sampling battery sensors and KGSL devfreq every 200 ms.

---

## 2. Benchmark Comparison Matrix

### 2.1 OpenGL Acceleration (`glmark2-wayland --off-screen`)
Workload: 4 complex scenes (terrain, shading, build, bump) @ 2.0 s per scene:

| Metric | Baseline (Unoptimized) | Optimized (Forced GMEM) | Sysmem (Direct Rendering) | Delta (Optimized vs Baseline) |
|---|---|---|---|---|
| **Overall Score (Median)** | **333.0** | **552.0** | **None (Stalled)** | **+65.8% throughput** |
| **Overall Score (Mean)** | 348.3 | 552.0 | N/A | **+58.5% throughput** |
| **Average Power (Watts)** | **4.34 W** | **3.12 W** | 3.13 W | **-28.1% power draw** |
| **Total Energy per Run (J)** | **44.8 J** | **29.8 J** | 35.2 J | **-33.5% energy consumed** |
| **Performance-per-Watt** | **76.7 Score/W** | **176.9 Score/W** | 0.0 | **+130.6% efficiency gain** |
| `terrain` Scene FPS | 89.0 FPS | 89.0 FPS | Stalled | Maintained |
| `shading` Scene FPS | 551.0 FPS | 743.0 FPS | Stalled | **+34.8% FPS** |
| `build` Scene FPS | 368.0 FPS | 556.0 FPS | Stalled | **+51.1% FPS** |
| `bump` Scene FPS | 343.0 FPS | 966.0 FPS | Stalled | **+181.6% FPS** |

---

### 2.2 Vulkan Acceleration (`vkmark --winsys wayland`)
Workload: 4 Vulkan scenes (vertex, texture, shading, desktop) @ 2.0 s per scene:

| Metric | Baseline (Turnip KGSL) | Optimized Profile | Sysmem Mode | Delta (Optimized vs Baseline) |
|---|---|---|---|---|
| **Overall Score (Median)** | **1313.0** | **1656.5** | **706.0** | **+26.2% throughput** |
| **Overall Score (Peak)** | 1668.0 | 1667.0 | 754.0 | Maintained |
| **Average Power (Watts)** | **4.20 W** | **2.86 W** | 3.13 W | **-31.9% power draw** |
| **Total Energy per Run (J)** | **37.8 J** | **27.6 J** | 35.2 J | **-27.0% energy consumed** |
| **Performance-per-Watt** | **312.6 Score/W** | **579.2 Score/W** | 225.5 Score/W | **+85.3% efficiency gain** |
| `vertex` Scene FPS | 1491.0 FPS | 1625.0 FPS | 720.0 FPS | **+9.0% FPS** |
| `texture` Scene FPS | 1182.0 FPS | 1272.0 FPS | 580.0 FPS | **+7.6% FPS** |
| `shading` Scene FPS | 1073.0 FPS | 1232.0 FPS | 610.0 FPS | **+14.8% FPS** |
| `desktop` Scene FPS | 1697.0 FPS | 2372.0 FPS | 920.0 FPS | **+39.8% FPS** |

---

### 2.3 Buffer Object Allocation Microbenchmark
Workload: 2,000 continuous shared DMA-BUF / ION buffer allocations:

| Metric | Original (`kgsl_bo.c`) | Optimized (Cached FD) | Delta |
|---|---|---|---|
| **Mean Allocation Latency** | **12.22 µs** | **5.10 µs** | **-58.2% latency** |
| **Allocation Throughput** | **81,859 allocs/sec** | **196,002 allocs/sec** | **+139.4% (2.39× faster)** |
| **Failed `open()` Syscalls** | **2,000 calls** | **0 calls** | **100% eliminated** |
| **Total Time (2000 runs)** | **24.43 ms** | **10.20 ms** | **-14.23 ms savings** |

---

## 3. Reproducibility Instructions

### Reproducing Benchmark Suites
1. Ensure the `mikasa` container is active:
   ```bash
   su -c 'PATH=$PATH:/data/local/Droidspaces/bin droidspaces --name=mikasa start'
   ```
2. Run the baseline suite:
   ```bash
   python3 engineering/scripts/run_benchmarks.py baseline "" 3
   ```
3. Run the GMEM optimized suite:
   ```bash
   python3 engineering/scripts/run_benchmarks.py exp2_gmem "FD_MESA_DEBUG=gmem" 3
   ```
4. Run the Buffer Object allocation microbenchmark:
   ```bash
   clang -O2 engineering/experiments/experiment_001_bo_alloc/bench_bo_alloc.c \
     -o engineering/experiments/experiment_001_bo_alloc/bench_bo_alloc
   su -c "engineering/experiments/experiment_001_bo_alloc/bench_bo_alloc 2000"
   ```
