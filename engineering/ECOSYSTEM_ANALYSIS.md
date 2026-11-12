# ECOSYSTEM INTEGRATION ANALYSIS (PERSPECTIVE 2)

**Document ID:** ENG-ECOSYSTEM-MESA-20261110  
**Target Device:** Xiaomi Redmi Note 10 Pro (`sweet` / `sweetin`, M2101K6P)  
**Target Repository:** `/data/data/com.termux/files/home/development/repo/mesa-for-android-container/`  
**Ecosystem Location:** `/data/data/com.termux/files/home/development/repo/`  
**Date:** 2026-11-10  

---

## 1. Neighboring Development Ecosystem Projects

The neighboring repositories in `/data/data/com.termux/files/home/development/repo/` were investigated to determine how improvements inside `mesa-for-android-container` directly benefit their development, deployment, and runtime:

```
/data/data/com.termux/files/home/development/repo/
├── Droidspaces-rootfs-Desktop-builder/    (Builds Arch/Debian/Fedora container rootfs & installers)
├── anland/                                (Wayland/X11 display consumer/producer daemon)
├── droidspaces-oss/                       (Core Linux container daemon & manager)
├── droidspaces-package/                   (Distribution packaging & repo releases)
├── los_kernel_xiaomi_sm6150/              (Qualcomm 4.14 kernel source with KGSL driver)
└── mesa-for-android-container/            <--- PRIMARY TARGET REPOSITORY
```

---

## 2. Cross-Project Benefits & Value Delivered

### 2.1 Benefit to `Droidspaces-rootfs-Desktop-builder`
- **Current State:**
  The desktop builder installs custom scripts `scripts/tui/install-mesa.sh` and `scripts/tui/droidspaces-gpu.sh`. When building rootfs images, it sets `MESA_LOADER_DRIVER_OVERRIDE=kgsl` in `/etc/environment`. However, it lacks a dedicated runtime probe to verify whether the installed Mesa packages successfully bind to `/dev/kgsl-3d0` and whether the current kernel supports DMA-heap or ION.
- **Value Delivered from Target:**
  The new `bin/mesa-container-ctl` tool provides an automated, standardized interface:
  - `mesa-container-ctl check`: Pre-flight sanity check for rootfs installation recipes to verify hardware acceleration before launching desktop environments.
  - `mesa-container-ctl profile <mode>`: Pre-tested configurations (`balanced`, `performance`, `battery-saver`) that can be directly written into `/etc/environment` during desktop image creation.

### 2.2 Benefit to `droidspaces-oss`
- **Current State:**
  `droidspaces-oss` manages container isolation, namespaces, cgroups, and device nodes (`--gpu` flag passing `/dev/kgsl-3d0` and `/dev/dri`). If KGSL permissions or group access are misconfigured (`droidspaces-gpu` group vs root), graphics initialization in Mesa fails silently without actionable diagnostic output.
- **Value Delivered from Target:**
  `mesa-container-ctl check` verifies `/dev/kgsl-3d0` presence, permissions, major/minor device numbers, and active devfreq governors, allowing `droidspaces-oss` test harnesses and health checks to validate GPU pass-through automatically.

### 2.3 Benefit to `anland`
- **Current State:**
  `anland` runs the container Wayland display producer (`anland-wayland` backend) and Android consumer application (`com.anland.consumer`). When container applications render via Mesa, frame pacing and buffer presentation depend directly on DMA-BUF import and fence synchronization.
- **Value Delivered from Target:**
  1. Caching the allocator file descriptor in `kgsl_bo.c` eliminates redundant `open()` syscalls and latency spikes during DMA-BUF allocation, smoothing buffer presentation to `anland`.
  2. Enforcing GMEM tiling prevents client-side presentation stalls and ensures clean fence completion signaling across Wayland IPC sockets.

### 2.4 Benefit to `droidspaces-package`
- **Current State:**
  `droidspaces-package` distributes compiled Mesa packages (`.pkg.tar.xz` for Arch Linux, `.tar.gz` for Debian/Ubuntu/Fedora).
- **Value Delivered from Target:**
  Upstreaming the cached allocator and stack safety fixes into the Mesa build tree directly enhances the reliability, latency, and memory safety of every binary distributed by `droidspaces-package`.

---

## 3. Strict Boundary Compliance

All source modifications were strictly implemented inside `/data/data/com.termux/files/home/development/repo/mesa-for-android-container/`. No neighboring repositories were altered or refactored.
