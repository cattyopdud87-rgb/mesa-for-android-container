# REGRESSION & EDGE-CASE VALIDATION REPORT

**Document ID:** ENG-REGRESSION-MESA-20261110  
**Target Device:** Xiaomi Redmi Note 10 Pro (`sweet` / `sweetin`, M2101K6P)  
**Target Repository:** `/data/data/com.termux/files/home/development/repo/mesa-for-android-container/`  
**Date:** 2026-11-10  

---

## 1. Regression Testing Matrix

| Test Case | Description | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| **Zero-Command Batch** | Command list with `nr_cmds = 0` passed to `flush_submit_list()` | Handled gracefully without crash or invalid VLA allocation | Stack array pointer valid, 0 commands submitted | **PASSED** |
| **Large-Command Batch** | Command list with `nr_cmds > 32` passed to `flush_submit_list()` | Heap allocation fallback succeeds without stack overflow | Dynamically allocated via `malloc`, freed at function exit | **PASSED** |
| **Missing `/dev/dma_heap`** | Android 4.14 kernel where `/dev/dma_heap/system` does not exist | Falls back smoothly to `/dev/ion` without leaking file descriptors | Probe selects `/dev/ion`, stores fd in `dma_heap_fd`, allocations succeed | **PASSED** |
| **Device Teardown** | Calling `kgsl_device_destroy()` on active context | Closes cached descriptor and frees device struct | Clean exit, no memory or file descriptor leaks | **PASSED** |
| **Repeated 3D Bursts** | 3 consecutive `glmark2` and `vkmark` runs | Consistent FPS, no memory leaks or GPU hang | Scores consistent within $\pm 2.5\%$, no crash or GPU hang | **PASSED** |

---

## 2. Rejected Approaches & Failed Experiments

### 1. Forcing Sysmem Mode (`FD_MESA_DEBUG=sysmem`)
- **Hypothesis:** Direct rendering without tile binning would reduce CPU overhead on low-complexity geometry.
- **Measured Reality:** In Wayland offscreen rendering, the absence of GMEM tile resolves prevented proper presentation fence signaling, causing the client render thread to hang indefinitely in `ppoll()`. In Vulkan, `sysmem` cut rendering throughput by more than half (from 1656 score down to 706).
- **Resolution:** **REJECTED**. GMEM must remain the default mode for Adreno 6xx.

### 2. Disabling UBWC (`TU_DEBUG=noubwc`)
- **Hypothesis:** Disabling compression might save decompression latency on small surface formats.
- **Measured Reality:** Without UBWC, memory bandwidth consumption surged, causing presentation jitter and stalling on high-resolution targets.
- **Resolution:** **REJECTED**. UBWC compression is mandatory for performance and memory bandwidth efficiency.
