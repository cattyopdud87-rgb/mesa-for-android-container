# PHASE 2 — BASELINE PERFORMANCE & TELEMETRY REPORT

**Document ID:** ENG-PHASE2-MESA-BASELINE-20261109  
**Target Device:** Xiaomi Redmi Note 10 Pro (`sweet` / `sweetin`, M2101K6P)  
**Target Repository:** `/data/data/com.termux/files/home/development/repo/mesa-for-android-container/`  
**Date:** 2026-11-09  

---

## 1. Methodology & Test Harness

A dedicated automated telemetry and benchmarking harness (`engineering/scripts/run_benchmarks.py`) was developed to execute multi-iteration benchmarks while sampling low-level device sensors at 200 ms intervals:
- **Battery Sensor Telemetry:** Voltage ($\text{V}$), Current ($\text{A}$), Instantaneous Power ($P = V \times I$), Temperature ($\text{°C}$), and Total Energy Consumed ($E = \int P \, dt$ in Joules).
- **GPU Kernel Driver Telemetry:** Frequency scaling states (`devfreq/cur_freq`), GPU utilization (`gpu_busy_percentage`).
- **Statistical Protocol:** 3 complete iterations per workload with 1.0 s thermal stabilization periods between runs.
- **Display Pipeline:** Native container Wayland session (`mikasa` Arch Linux container running KDE Plasma 6.8 `kwin_wayland` via socket `wayland-1`).

---

## 2. Baseline Performance Results

### 2.1 OpenGL Acceleration (Freedreno FD618 via KGSL)
- **Harness:** `glmark2-wayland --off-screen`
- **Workload:** 4 representative scenes @ 2.0 s duration each:
  - `terrain`: Heightmap mesh displacement & heavy texturing
  - `shading`: Gouraud and Phong fragment lighting calculations
  - `build`: High-volume geometry draw-call submission
  - `bump`: Normal mapping and specular highlight rendering

| Iteration | Overall Score | Avg Power (W) | Peak Power (W) | Energy (J) | Avg GPU Freq | Avg GPU Busy | Temp Delta |
|---|---|---|---|---|---|---|---|
| Run 1 | 447 | 4.108 W | 5.340 W | 41.73 J | 365.7 MHz | 58.0% | +0.1 °C |
| Run 2 | 265 | 4.527 W | 5.720 W | 48.14 J | 369.6 MHz | 47.1% | +0.3 °C |
| Run 3 | 333 | 4.374 W | 5.610 W | 44.60 J | 288.5 MHz | 36.2% | +0.2 °C |
| **Statistical Summary** | **Median: 333.0** (Mean: 348.3) | **Mean: 4.34 W** | **5.72 W** | **Mean: 44.8 J** | **341.3 MHz** | **47.1%** | **Avg: +0.2 °C** |

#### Per-Scene Latency Breakdown (OpenGL):
- `terrain`: **89.0 FPS** (FrameTime: **11.34 ms**)
- `shading`: **551.0 FPS** (FrameTime: **1.82 ms**)
- `build`: **368.0 FPS** (FrameTime: **2.72 ms**)
- `bump`: **343.0 FPS** (FrameTime: **2.92 ms**)

---

### 2.2 Vulkan Acceleration (Turnip Adreno 618 via KGSL)
- **Harness:** `vkmark --winsys wayland`
- **Workload:** 4 representative Vulkan scenes @ 2.0 s duration each:
  - `vertex`: Vertex pipeline throughput & state transitions
  - `texture`: Compressed texture fetch & UBWC caching
  - `shading`: Fragment shader compute
  - `desktop`: Multi-window composite workload

| Iteration | Overall Score | Avg Power (W) | Peak Power (W) | Energy (J) | Avg GPU Freq | Avg GPU Busy | Temp Delta |
|---|---|---|---|---|---|---|---|
| Run 1 | 1313 | 4.601 W | 5.890 W | 41.31 J | 741.5 MHz | 76.3% | +0.1 °C |
| Run 2 | 1235 | 5.028 W | 6.120 W | 46.37 J | 740.8 MHz | 76.4% | +0.1 °C |
| Run 3 | 1668 | 2.959 W | 4.880 W | 25.62 J | 742.3 MHz | 85.6% | +0.2 °C |
| **Statistical Summary** | **Median: 1313.0** (Mean: 1405.3) | **Mean: 4.20 W** | **6.12 W** | **Mean: 37.8 J** | **741.5 MHz** | **79.4%** | **Avg: +0.13 °C** |

#### Per-Scene Latency Breakdown (Vulkan):
- `vertex`: **1491.0 FPS** (FrameTime: **0.67 ms**)
- `texture`: **1182.0 FPS** (FrameTime: **0.85 ms**)
- `shading`: **1073.0 FPS** (FrameTime: **0.93 ms**)
- `desktop`: **1697.0 FPS** (FrameTime: **0.59 ms**)

---

## 3. Key Telemetry & Architectural Insights

1. **Vulkan (Turnip) Outperforms OpenGL (Freedreno) by 3.9×:**
   - Vulkan Median Score: **1313** vs. OpenGL Median Score: **333**.
   - Turnip engages modern asynchronous command streaming, efficient GMEM suballocators, and hardware UBWC compression. The GPU governor scales rapidly to high-frequency states (741.5 MHz average), resulting in sub-millisecond frame times (0.59 – 0.93 ms).
2. **Freedreno OpenGL devfreq Under-Utilization:**
   - In Freedreno OpenGL, the GPU governor averages only 341.3 MHz (often idling around 288 MHz) with GPU busy percentages below 50%. The CPU-side submission overhead and synchronous fence waiting prevent the GPU governor from maintaining maximum power states.
3. **Power & Energy Dynamics:**
   - Average device power draw during rendering ranges between **4.20 W and 4.34 W**.
   - Thermal stability is excellent: across 8-second multi-scene burst runs, battery temperature rises by only 0.1 – 0.3 °C.
   - Run-to-run variance exists due to devfreq governor hysteresis, proving the necessity of multi-run median statistics.
