# PHASE 1 — CODEBASE ARCHITECTURE & OPTIMIZATION AUDIT

**Document ID:** ENG-PHASE1-MESA-ARCH-20261109  
**Target Device:** Xiaomi Redmi Note 10 Pro (`sweet` / `sweetin`, M2101K6P)  
**Target Repository:** `/data/data/com.termux/files/home/development/repo/mesa-for-android-container/`  
**Date:** 2026-11-09  

---

## 1. Executive Summary & Codebase Architecture

`mesa-for-android-container` is an engineering fork of the upstream Mesa 3D Graphics Library designed to enable fully accelerated OpenGL (via Freedreno) and Vulkan (via Turnip) inside Linux containers on Android devices powered by Qualcomm Adreno GPUs.

Unlike desktop Linux systems which interface with the upstream Linux DRM/KMS kernel driver (`msm`), Android kernels use Qualcomm's proprietary **KGSL (Kernel Graphics Support Layer)** driver exposed via `/dev/kgsl-3d0`. This repository implements custom userspace KGSL backends that translate standard Gallium and Vulkan driver calls into KGSL ioctls.

```
+-------------------------------------------------------------------------------------------------+
|                               LINUX CONTAINER (mikasa - Arch Linux)                             |
|                                                                                                 |
|   +------------------------------------+             +---------------------------------------+  |
|   |       OpenGL Applications          |             |          Vulkan Applications          |  |
|   |     (glmark2, KDE Plasma kwin)     |             |         (vkmark, Games, Emulators)    |  |
|   +------------------------------------+             +---------------------------------------+  |
|                     |                                                    |                      |
|                     v                                                    v                      |
|   +------------------------------------+             +---------------------------------------+  |
|   |          libEGL / libGLX           |             |           libvulkan (Loader)          |  |
|   +------------------------------------+             +---------------------------------------+  |
|                     |                                                    |                      |
|                     v                                                    v                      |
|   +------------------------------------+             +---------------------------------------+  |
|   |         Mesa Gallium Driver        |             |          Turnip Vulkan Driver         |  |
|   |           (Freedreno a6xx)         |             |             (tu_device, tu_cs)        |  |
|   +------------------------------------+             +---------------------------------------+  |
|                     |                                                    |                      |
|                     v                                                    v                      |
|   +------------------------------------+             +---------------------------------------+  |
|   |     Freedreno KGSL DRM Backend     |             |       Turnip KGSL Kernel Layer        |  |
|   |   (src/freedreno/drm/kgsl/bo/pipe) |             |    (src/freedreno/vulkan/tu_knl_kgsl) |  |
|   +------------------------------------+             +---------------------------------------+  |
+-------------------------------------------------------------------------------------------------+
                                       |                               |
                                       +---------------+---------------+
                                                       |
                                                       v ioctl(/dev/kgsl-3d0)
+-------------------------------------------------------------------------------------------------+
|                                     ANDROID 15 LINUX KERNEL 4.14                                |
|                                                                                                 |
|   +-----------------------------------------------------------------------------------------+   |
|   |                    KGSL Driver (/dev/kgsl-3d0, char major 503, minor 0)                 |   |
|   |    IOCTL_KGSL_GPU_COMMAND | IOCTL_KGSL_GPUMEM_ALLOC_ID | IOCTL_KGSL_DEVICE_WAITTIMESTAMP|   |
|   +-----------------------------------------------------------------------------------------+   |
|                                                  |                                              |
|                                                  v                                              |
|   +-----------------------------------------------------------------------------------------+   |
|   |               Qualcomm Adreno 618 GPU Hardware (Snapdragon 732G SM6150)                 |   |
|   |       512KB GMEM Tile Cache | 180-650 MHz devfreq | UBWC Lossless Compression           |   |
|   +-----------------------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------+
```

---

## 2. Execution Paths & Critical Subsystems

### 2.1 Freedreno KGSL Backend (`src/freedreno/drm/kgsl/`)
- **Device Management (`kgsl_device.c`):**
  Opens `/dev/kgsl-3d0` and queries hardware capabilities via `IOCTL_KGSL_DEVICE_GETPROPERTY`. Sets up `fd_device` function table.
- **Pipe & Context Execution (`kgsl_pipe.c`):**
  Allocates a hardware execution context via `IOCTL_KGSL_DRAWCTXT_CREATE`.
  Fences are represented by monotonic timestamps; fence waits are executed synchronously using `IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID` with nanosecond timeout adjustments.
- **Buffer Object Management (`kgsl_bo.c`):**
  Allocates native GPU memory using `IOCTL_KGSL_GPUMEM_ALLOC_ID`.
  Maps GPU buffers into userspace virtual memory via `mmap()` offset encoding (`bo->handle << 12`).
  Allocates scanout / shared buffers via DMA-BUF or legacy ION.
- **Ringbuffer & Command Submission (`kgsl_ringbuffer_sp.c`):**
  Builds command batches and issues them via `IOCTL_KGSL_GPU_COMMAND` with `KGSL_CMDBATCH_SUBMIT_IB_LIST`.
  Converts completed timestamps into native Linux sync fences via `IOCTL_KGSL_TIMESTAMP_EVENT`.

### 2.2 Turnip Vulkan KGSL Backend (`src/freedreno/vulkan/tu_knl_kgsl.cc`)
- Implements the complete `tu_knl` interface over KGSL.
- Manages command stream buffers (`tu_cs`), suballocators, and GMEM tile binning configurations.
- Handles UBWC (Universal Bandwidth Compression) flags for textures and render targets.
- Provides support for sparse binding, asynchronous timeline semaphores, and sync fences.

### 2.3 Window System Integration (WSI)
- **Wayland (`platform_wayland.c`, `wsi_common_wayland.c`):**
  Directly communicates with Wayland compositors (`kwin_wayland`, `anland`) over Unix domain sockets using `wl_drm` or `linux-dmabuf-unstable-v1`.
- **X11 / Xwayland (`x11_dri3.c`, `wsi_common_x11.c`):**
  Uses DRI3 and Present extensions. Includes custom patches for present wait fences (`MESA_DRI3_DISABLE_PRESENT_WAIT_FENCE`) to prevent tearing.

---

## 3. Bottleneck Analysis & Optimization Opportunities

From the perspective of the target Snapdragon 732G device and the surrounding ecosystem, five major bottlenecks and optimization opportunities were identified:

### 3.1 Device Perspective Bottlenecks (Hardware Efficiency & Battery)
1. **Redundant Syscall Overhead in Shared BO Allocations (`kgsl_bo.c`):**
   `dma_heap_alloc()` in `kgsl_bo.c` unconditionally attempts `open("/dev/dma_heap/system", O_RDONLY)` on every single allocation. On Android kernels (like this 4.14 kernel), `/dev/dma_heap` does not exist; only `/dev/ion` is present. This results in a guaranteed failed `open()` syscall on every shared/scanout BO allocation, followed by opening and closing `/dev/ion` repeatedly.
2. **TBDR Tile Binning vs Direct Sysmem Rendering Overhead:**
   Adreno 618 has a 512 KiB high-speed GMEM on-chip cache. For simple 2D or small offscreen renderpasses, running a full tile binning pass adds CPU setup time and memory traffic. Conversely, for heavy 3D passes, failing to utilize GMEM causes massive bandwidth thrashing over the LPDDR4X bus, spiking power draw and thermal throttling.
3. **Mesa Shader Cache & Memory Churn under Chronic RAM Pressure:**
   The device has 5.4 GiB RAM and 3.0 GiB ZRAM. Mesa's on-disk and in-memory shader cache, if unbounded, causes cache bloat and triggers swap churn. Tuning shader cache bounds and default buffer allocation policies preserves critical memory for container desktop and AI workloads.
4. **GPU Devfreq Governors & Wakeup Behavior:**
   GPU scaling is controlled by `msm-adreno-tz`. Rapid fluctuations between 180 MHz and 650 MHz increase power consumption. Tuning presentation interval and buffer queuing prevents unnecessary burst wakeups.

### 3.2 Ecosystem Perspective Bottlenecks (Integration with Neighboring Tools)
1. **Dynamic Driver Switching & Environment Config:**
   `Droidspaces-rootfs-Desktop-builder` provides `droidspaces-gpu`, which sets environment variables (`MESA_LOADER_DRIVER_OVERRIDE=kgsl`, `VK_DRIVER_FILES`). However, users and ecosystem tools lack a centralized, automated diagnostic and tuning utility inside the container to verify KGSL permissions, validate driver fallback, and profile rendering latency.
2. **Wayland Sync Fence Pacing with `anland`:**
   `anland` acts as the Wayland display consumer bridge. Frame tearing or presentation stutter occurs when Mesa client presentation fails to align with Wayland frame callbacks.
3. **Packaging & Distro Parity in `droidspaces-package`:**
   Package distribution scripts need clean metadata, pre-configured hardware defaults for Adreno 618, and validated build profiles.

---

## 4. Prioritization Matrix

| Opportunity | Perspective | Impact | Risk | Complexity | Priority |
|---|---|---|---|---|---|
| **Eliminate Failed Syscalls in `kgsl_bo.c` (ION/DMA-heap caching)** | Device | High (Syscall latency reduction) | Very Low | Low | **Immediate** |
| **Establish Controlled Baseline Benchmarks (`glmark2`, `vkmark`)** | Both | Critical (Measurement foundation) | Zero | Low | **Immediate** |
| **Empirical Tuning of GMEM vs Sysmem & UBWC flags** | Device | High (Power per watt, Throughput) | Low | Medium | **High** |
| **Comprehensive Diagnostic & Optimization Tool for Ecosystem** | Ecosystem | High (Reusability for Droidspaces/Anland) | Zero | Medium | **High** |
| **Memory Footprint & Shader Cache Throttling** | Device | High (Prevents ZRAM churn/LMK) | Low | Medium | **High** |
