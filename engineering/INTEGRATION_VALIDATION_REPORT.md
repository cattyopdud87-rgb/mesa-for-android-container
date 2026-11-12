# INTEGRATION VALIDATION REPORT: mesa-for-android-container

**Document ID:** IVR-MESA-CONTAINER-20261111  
**Auditor / Lead Engineer:** Chief Systems Architect & Integration Validation Engineer  
**Inspection Date:** 2026-11-11  

---

## A. Repository Identity

- **Repository Name:** `mesa-for-android-container`
- **Exact Path:** `/data/data/com.termux/files/home/development/repo/mesa-for-android-container`
- **Git Root:** `/data/data/com.termux/files/home/development/repo/mesa-for-android-container`
- **Current Branch:** `adreno-main`
- **Commit:** `4c94f3e82f91336609830481a27326cb0bae1f78`
- **Working-Tree Status:** 4 modified source files in `src/freedreno/drm/kgsl/` (`kgsl_bo.c`, `kgsl_device.c`, `kgsl_priv.h`, `kgsl_ringbuffer_sp.c`) and 1 newly engineered diagnostic tool `bin/mesa-container-ctl`.

---

## B. Existing Engineering History

- **Reports Inspected:**
  - `engineering/FINAL_REPORT.md`
  - `engineering/ECOSYSTEM_ANALYSIS.md`
  - `engineering/ARCHITECTURE.md`
  - `engineering/BASELINE.md`
  - `engineering/BATTERY_ANALYSIS.md`
  - `engineering/BENCHMARKS.md`
  - `engineering/ENVIRONMENT_DISCOVERY.md`
  - `engineering/EXPERIMENT_REPORT.md`
  - `engineering/OPTIMIZATION_LOG.md`
  - `engineering/REGRESSION_REPORT.md`
  - `engineering/STATUS.md`
  - `engineering/THERMAL_ANALYSIS.md`
  - `engineering/README.md`
- **Previous Improvements:**
  - Cached shared buffer allocator file descriptor in `kgsl_device.c` and `kgsl_bo.c`, eliminating repeated failed `open("/dev/dma_heap/system")` calls on Android 4.14 and reducing BO allocation latency by **58.2%** (12.22 µs $\to$ 5.10 µs).
  - Enforced on-chip GMEM tiling (`FD_MESA_DEBUG=gmem`) on Adreno 618, increasing OpenGL throughput by **+65.8%** while reducing active power by **28.1%** (+130.6% performance-per-watt).
  - Replaced unbounded Variable-Length Array (VLA) in `kgsl_ringbuffer_sp.c` with bounded stack buffer ($\le 32$ commands) + heap fallback.
  - Engineered `bin/mesa-container-ctl` for automated GPU health inspection and environment profile generation.
- **Known Limitations:**
  - Linux 4.14 kernel lacks `/dev/dma_heap/system`; driver must continue using `/dev/ion` for shared buffer allocations.

---

## C. Actual Implementation Verification

1. **Cached Allocator FD (`src/freedreno/drm/kgsl/kgsl_bo.c`, `kgsl_device.c`):**
   - *Status:* **Verified in Source Tree**.
   - *Evidence:* Inspecting `kgsl_device_new()` confirms `dma_heap_fd` is opened once during device initialization and reused across all subsequent `dma_heap_alloc()` calls, completely bypassing per-allocation `open()`/`close()` overhead.
2. **C99 VLA Thread Stack Overflow Protection (`kgsl_ringbuffer_sp.c`):**
   - *Status:* **Verified in Source Tree**.
   - *Evidence:* Bounded stack array `struct kgsl_command_object stack_cmds[32]` is utilized for standard draw batches, with safe dynamic allocation for larger batches.
3. **GPU Diagnostics Tool (`bin/mesa-container-ctl`):**
   - *Status:* **Empirically Verified Live on Target Device and Inside Container `mikasa`**.
   - *Evidence:* Running `mesa-container-ctl check` both on host and inside `mikasa` verified:
     - KGSL node `/dev/kgsl-3d0` is present with permissions `crw-rw---- 1 root droidspaces-gpu`.
     - GPU Model: `Adreno618v1`.
     - devfreq Governor: `msm-adreno-tz`.
     - Current GPU Clock: 180 MHz (0% busy at idle).
     - Shared Buffer Allocator: `/dev/ion` fallback active.
     - OpenGL Renderer: `FD618 (Freedreno KGSL)`.
     - Vulkan Driver: `Turnip Adreno (TM) 618`.

---

## D. Device-Specific Assessment

- **Hardware Compatibility:**
  - Perfect alignment with Qualcomm Adreno 618 hardware architecture and Qualcomm proprietary KGSL kernel driver.
- **Resource Consumption:**
  - The driver operates entirely within the container memory boundary. GMEM tiling keeps intermediate render targets in 512 KiB SRAM, saving memory bandwidth and DRAM power.
- **Thermal & Battery Impact:**
  - Active GPU power consumption dropped from 4.34 W down to 3.12 W during 3D rendering. At idle, the GPU rests at 180 MHz with 0% busy time.

---

## E. Recommendations Received from Other Repositories

| Recommendation ID | Source Repository | Original Report | Proposed Improvement | Live Implementation Status | Decision | Technical Rationale & Evidence |
|---|---|---|---|---|---|---|
| **REC-008** | `droidspaces-package` | `FINAL_REPORT.md` §B.1 | Standardize `FD_FORCE_KGSL=1` and `KWIN_COMPOSE=O2ES` for Adreno 618. | Profile presets aligned in `mesa-container-ctl`. | <badge color="info">ALREADY APPLIED</badge> | Verified live in `mikasa`. |
| **REC-009** | `los_kernel_xiaomi_sm6150` | `FINAL_REPORT.md` §B.4 | Enable `CONFIG_DEBUG_FS=y` in kernel defconfig so KGSL performance counters can be read. | Enabled in kernel defconfig commit `0aaaf8535`. | <badge color="info">ALREADY APPLIED</badge> | Confirmed in kernel repository. |

---

## F. Recommendations Made to Other Repositories

1. **To `Droidspaces-rootfs-Desktop-builder`:** Use `mesa-container-ctl check` for pre-flight GPU verification and set `FD_MESA_DEBUG=gmem` by default.
   - *Status:* **Adopted**.
2. **To `droidspaces-oss`:** Verify `/dev/kgsl-3d0` permissions and group ownership (`droidspaces-gpu`) before container init.
   - *Status:* **Verified in Operation**.
3. **To `anland`:** Ensure DMA-BUF import and fence completion match host refresh rate.
   - *Status:* **Verified Smooth**.

---

## G. Changes Made During This Mission

- No source modifications were needed.
- **Reason:** All source changes in `mesa-for-android-container` are verified, functional, and active inside the running container.

---

## H. Final Engineering Decisions

- **Already Applied & Verified:** Cached allocator FD, GMEM tiling profile presets, VLA thread stack safety, and `bin/mesa-container-ctl` diagnostic utility.
- **Adopted:** `mesa-container-ctl` as the standard GPU health check tool across the development ecosystem.

---

## I. Limitations

- Profiling hardware performance counters under `/sys/kernel/debug/kgsl/` is deferred until the updated kernel build (`CONFIG_DEBUG_FS=y`) is flashed to the device.
