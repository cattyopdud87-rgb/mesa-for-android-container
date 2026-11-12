# PHASE 0 — ENVIRONMENT DISCOVERY REPORT

**Document ID:** ENG-PHASE0-MESA-DISCOVERY-20261109  
**Target Device:** Xiaomi Redmi Note 10 Pro (`sweet` / `sweetin`, M2101K6P)  
**Primary Target Repository:** `/data/data/com.termux/files/home/development/repo/mesa-for-android-container/`  
**Date:** 2026-11-09  

---

## 1. Executive Overview & Target Mission

The primary objective is autonomous engineering optimization of the authoritative repository:
`/data/data/com.termux/files/home/development/repo/mesa-for-android-container/`

This work addresses two rigorous engineering perspectives simultaneously:
- **Perspective 1 (Device-Specific Efficiency):** Optimize the Mesa graphics stack to deliver maximum practical rendering throughput, lower frame latency, reduced buffer churn, and minimal memory footprint on the Snapdragon 732G / Adreno 618 architecture under strict thermal and battery constraints.
- **Perspective 2 (Ecosystem Value):** Enhance the repository's interfaces, build profiles, configuration tooling, and integration ergonomics so neighboring projects in `/data/data/com.termux/files/home/development/repo` (`anland`, `droidspaces-oss`, `Droidspaces-rootfs-Desktop-builder`, `droidspaces-package`) benefit seamlessly from high-performance container acceleration.

---

## 2. Target Hardware & Platform Forensics

### 2.1 SoC / Compute Subsystem
- **Device:** Xiaomi Redmi Note 10 Pro (`sweet` / `sweetin`, M2101K6P)
- **SoC:** Qualcomm SM6150 / Snapdragon 732G ("SDMMAGPIE")
- **CPU Architecture:** 8 Cores (ARMv8.2-A big.LITTLE / DynamIQ):
  - **Gold Cluster:** 2× Kryo 470 Gold (Cortex-A76) @ 2.304 GHz (CPUs 6, 7). Governor: `schedutil`.
  - **Silver Cluster:** 6× Kryo 470 Silver (Cortex-A55) @ 1.804 GHz (CPUs 0–5). Governor: `schedutil`.
- **Instruction Extensions:**
  - `asimddp`: ARMv8.2 INT8 Dot Product instructions (`SDOT`/`UDOT`)
  - `fphp`, `asimdhp`: Half-precision floating-point arithmetic (FP16)
  - `atomics`: Large System Extensions (LSE) atomics
  - `crc32`, `aes`, `pmull`, `sha1`, `sha2`, `dcpop`

### 2.2 GPU & Kernel Graphics Subsystem
- **GPU Model:** Qualcomm Adreno 618 (A6xx family)
- **Kernel Interface:** KGSL (Kernel Graphics Support Layer) character device `/dev/kgsl-3d0` (Major 503, Minor 0).
- **GPU Frequency Scaling (devfreq):**
  - Path: `/sys/class/kgsl/kgsl-3d0/devfreq/`
  - Active Governor: `msm-adreno-tz`
  - Available Frequency States:
    - 180 MHz (Pwrlevel 5, Idle floor)
    - 267 MHz (Pwrlevel 4)
    - 355 MHz (Pwrlevel 3)
    - 430 MHz (Pwrlevel 2)
    - 565 MHz (Pwrlevel 1)
    - 650 MHz (Pwrlevel 0, Peak performance)
- **Telemetry Interfaces:**
  - GPU Temperature: `/sys/class/kgsl/kgsl-3d0/temp`
  - GPU Busy Percentage: `/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage`
  - GPU Clock Stats: `/sys/class/kgsl/kgsl-3d0/gpu_clock_stats`

### 2.3 Memory Constraints (Primary Physical Bottleneck)
- **Total Physical RAM:** 5,654,864 kB (~5.4 GiB kernel-visible).
- **ZRAM Swap:** 3,145,724 kB (3.0 GiB) on `/dev/block/zram0` (LZ4 compression).
- **Swap Utilization:** 85–92% utilized during multi-subsystem desktop operation.
- **Critical Impact on Graphics:** Unnecessary graphics buffer allocations, unevicted shader caches, and unbounded command buffers directly trigger `kswapd` thrashing and Android LowMemoryKiller (LMK) eviction.

### 2.4 Power & Thermal Telemetry
- **Battery Interface:** `/sys/class/power_supply/battery/`
  - Voltage: `/sys/class/power_supply/battery/voltage_now` (~3.72 V)
  - Current: `/sys/class/power_supply/battery/current_now` (~1.58 A)
  - Temperature: `/sys/class/power_supply/battery/temp` (~40.7°C)
  - Instantaneous Power: $P = V \times I$ (~5.87 W total device draw under load).

---

## 3. Primary Target Repository Status

- **Authoritative Path:** `/data/data/com.termux/files/home/development/repo/mesa-for-android-container/`
- **Git Commit:** `4c94f3e82f9` (`docs: update descriptions on new release '27.0.0-devel-20261025-r2'`)
- **Active Branch:** `adreno-main`
- **Remote Origin:** `https://github.com/lfdevs/mesa-for-android-container`
- **Working Tree:** Clean (verified via `git status -s`).
- **Rollback Branch:** `backup-pre-optimization` created at commit `4c94f3e82f9`.
- **Core Role:** Downstream distribution-agnostic Mesa fork providing:
  - Freedreno Gallium3D driver with KGSL backend (`src/freedreno/drm/kgsl/`) for OpenGL & OpenGL ES.
  - Turnip Vulkan driver with KGSL backend (`src/freedreno/vulkan/tu_knl_kgsl.cc`) for Vulkan 1.3.
  - Multi-distribution packaging pipelines (Arch, Debian, Ubuntu, Fedora, Alpine, SteamOS, Void).
  - Termux-VA video acceleration integration.

---

## 4. Surrounding Development Ecosystem

The development ecosystem resides at `/data/data/com.termux/files/home/development/repo/`:

| Neighboring Repository | Role in Ecosystem | Integration Surface with Target |
|---|---|---|
| `anland` | High-performance Wayland/X11 display and audio bridge between Android and container | Wayland client buffer presentation, DMA-BUF / sync fences, EGL swapchain |
| `droidspaces-oss` | Root container daemon and CLI runtime manager | Container environment variables (`MESA_LOADER_DRIVER_OVERRIDE`), GPU device pass-through (`/dev/kgsl-3d0`, `/dev/dri`), cgroup memory constraints |
| `Droidspaces-rootfs-Desktop-builder` | Builds rootfs images for Arch, Debian, Ubuntu | Installs Mesa packages, configures `/etc/environment`, sets up GPU switcher scripts |
| `droidspaces-package` | Distro package builder & repository | Packages custom compiled Mesa binaries for package manager installation (`pacman`, `apt`, `dnf`) |
| `los_kernel_xiaomi_sm6150` | Android 4.14 kernel source | Exposes `/dev/kgsl-3d0` ioctls, devfreq, and sync fence primitives |

---

## 5. Live Container Environment (`mikasa`)

- **Container Path:** `/data/local/Droidspaces/Containers/mikasa/`
- **Rootfs:** Arch Linux ARM64
- **Active Compositor:** KDE Plasma 6.8 (`kwin_wayland`) using socket `wayland-1` and Xwayland `:0`.
- **Installed Mesa Packages:**
  - `mesa 1:26.3.0-1`
  - `vulkan-freedreno 1:26.3.0-1`
  - `mesa-utils 9.0.0-7`
  - `vulkan-tools 1.4.363.0-1`
- **Live Empirical Benchmarks Verified:**
  - `glmark2-wayland --off-screen -b terrain`: **86 Score (87 FPS, 11.5 ms frame time)**
  - `vkmark --winsys wayland -b vertex`: **985 Score (985 FPS, 1.01 ms frame time)**
  - Vulkan Driver Info: `Turnip Adreno (TM) 618`, Vulkan 1.3.359, API Version 1.3.359
  - OpenGL Driver Info: `freedreno FD618`, OpenGL 4.6 (Compatibility & Core Profiles) Mesa 26.3.0-arch1.1

---

## 6. Established Rollback & Safety Strategy

1. **Git Tracking:**
   - Pre-optimization baseline tagged and branched on `backup-pre-optimization`.
   - Any modification will be tracked via isolated Git commits with full diff review.
2. **Container Safety:**
   - Container configuration backed up: `/data/local/Droidspaces/Containers/mikasa/container.config.bak`.
   - Installed packages verified via Arch Linux package database (`pacman -Q`).
3. **Execution Guard:**
   - No destructive commands executed.
   - Temperature limits actively monitored: bench loops abort if battery temperature exceeds 44°C.
