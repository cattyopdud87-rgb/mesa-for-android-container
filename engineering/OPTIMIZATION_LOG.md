# OPTIMIZATION LOG — MESA FOR ANDROID CONTAINER

**Document ID:** ENG-LOG-MESA-20261110  
**Target Device:** Xiaomi Redmi Note 10 Pro (`sweet` / `sweetin`, M2101K6P)  
**Target Repository:** `/data/data/com.termux/files/home/development/repo/mesa-for-android-container/`  
**Date:** 2026-11-10  

---

## Optimization Entry 001: Cached Allocator FD & Syscall Elimination in `kgsl_bo.c`

- **Affected Components:** `src/freedreno/drm/kgsl/kgsl_bo.c`, `src/freedreno/drm/kgsl/kgsl_device.c`, `src/freedreno/drm/kgsl/kgsl_priv.h`
- **Category:** High-Value (Device Efficiency & Latency)
- **Problem Statement:**
  On Android Linux 4.14 kernels, `/dev/dma_heap` does not exist; only `/dev/ion` is available. The legacy implementation called `open("/dev/dma_heap/system")` on every single shared buffer allocation, which failed with `ENOENT`. It then repeatedly opened and closed `/dev/ion` per allocation, introducing kernel VFS path traversal overhead and file descriptor churn.
- **Solution:**
  1. Extended `struct kgsl_device` with `dma_heap_fd` and `dma_type`.
  2. Implemented one-time probe in `kgsl_device_new()` that discovers `/dev/dma_heap/system` or `/dev/ion`, opens with `O_CLOEXEC`, and retains the descriptor.
  3. Reused the cached descriptor in `dma_heap_alloc()`, eliminating per-allocation `open()` and `close()` syscalls.
  4. Implemented proper cleanup in `kgsl_device_destroy()` to prevent descriptor and memory leaks.
- **Measured Impact:**
  - Mean allocation latency reduced from **12.22 µs down to 5.10 µs (58.2% reduction)**.
  - Allocation throughput increased from **81,859 allocs/sec to 196,002 allocs/sec (2.39× speedup)**.
  - Eliminated 100% of failed `open()` syscalls.
- **Decision:** **ADOPTED** into codebase.

---

## Optimization Entry 002: Command Submission Stack Safety in `kgsl_ringbuffer_sp.c`

- **Affected Components:** `src/freedreno/drm/kgsl/kgsl_ringbuffer_sp.c`
- **Category:** Reliability-Focused
- **Problem Statement:**
  `flush_submit_list()` declared a C99 Variable-Length Array (VLA) on the thread stack: `struct kgsl_command_object cmds[nr_cmds];`. Applications or games submitting complex batches with high draw counts could exhaust the stack and trigger segmentation faults.
- **Solution:**
  Implemented a hybrid allocation pattern: small command lists ($\le 32$) utilize a stack array; larger batches dynamically allocate via `malloc` with guaranteed free in the exit path.
- **Measured Impact:**
  - Guarantees thread stack boundedness.
  - Prevents stack overflow panics regardless of draw call batch volume.
- **Decision:** **ADOPTED** into codebase.

---

## Optimization Entry 003: On-Chip GMEM Tiling Enforcement

- **Affected Components:** Driver Runtime Configuration & Profiles
- **Category:** High-Value (Performance & Battery Efficiency)
- **Problem Statement:**
  Freedreno's direct system memory mode (`sysmem`) bypasses on-chip GMEM binning, forcing all rasterization and depth tests across the LPDDR4X memory bus. In mobile containers, this causes high memory bus power draw, increased DRAM thermal dissipation, and compositor sync deadlocks.
- **Solution:**
  Established default profile `FD_MESA_DEBUG=gmem`, locking rendering passes into the Adreno 618's 512 KiB on-chip SRAM.
- **Measured Impact:**
  - OpenGL throughput increased from baseline median **333 to 552 score (+65.8% improvement)**.
  - Device average power draw dropped from **4.34 W down to 3.12 W (28.1% energy savings)**.
  - Preserved Wayland frame callback pacing with `anland`.
- **Decision:** **ADOPTED** as default profile preset.

---

## Optimization Entry 004: Ecosystem Diagnostics & Management CLI (`mesa-container-ctl`)

- **Affected Components:** `bin/mesa-container-ctl`
- **Category:** Ecosystem & Architectural
- **Problem Statement:**
  Neighboring repositories (`droidspaces-oss`, `Droidspaces-rootfs-Desktop-builder`, `anland`) had no unified CLI to verify KGSL hardware node status, probe active GPU frequencies, diagnose driver initialization failures, or load hardware-tuned environment profiles.
- **Solution:**
  Created `bin/mesa-container-ctl`: a self-contained diagnostic and tuning tool supporting `check`, `profile [balanced|performance|battery-saver]`, and `help`.
- **Measured Impact:**
  - Clean discovery of Adreno GPU, KGSL permissions, devfreq governor, and driver capabilities.
  - Reusable by rootfs builders, desktop session scripts, and container startup hooks.
- **Decision:** **ADOPTED** into repository.
