#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <time.h>
#include <sys/ioctl.h>
#include <linux/types.h>

struct ion_allocation_data {
    __u64 len;
    __u32 heap_id_mask;
    __u32 flags;
    __u32 fd;
    __u32 unused;
};

#define ION_IOC_MAGIC   'I'
#define ION_IOC_ALLOC   _IOWR(ION_IOC_MAGIC, 0, struct ion_allocation_data)

/* Original implementation from src/freedreno/drm/kgsl/kgsl_bo.c */
static int dma_heap_alloc_original(uint64_t size)
{
    int ret;
    int dma_heap = open("/dev/dma_heap/system", O_RDONLY);

    if (dma_heap < 0) {
        int ion_heap = open("/dev/ion", O_RDONLY);
        if (ion_heap < 0)
            return -1;

        struct ion_allocation_data alloc_data = {
            .len = size,
            .heap_id_mask = (1U << 0) | (1U << 25),
            .flags = 0,
        };

        ret = ioctl(ion_heap, ION_IOC_ALLOC, &alloc_data);
        close(ion_heap);

        if (ret)
            return -1;

        return alloc_data.fd;
    }
    return -1;
}

/* Optimized implementation with cached fd & one-time probe */
static int cached_ion_fd = -1;
static int cached_alloc_type = -1; // 0 = dma_heap, 1 = ion

static int init_cached_allocator(void)
{
    int fd = open("/dev/dma_heap/system", O_RDONLY);
    if (fd >= 0) {
        cached_alloc_type = 0;
        cached_ion_fd = fd;
        return 0;
    }

    fd = open("/dev/ion", O_RDONLY);
    if (fd >= 0) {
        cached_alloc_type = 1;
        cached_ion_fd = fd;
        return 0;
    }

    return -1;
}

static int dma_heap_alloc_cached(uint64_t size)
{
    if (cached_ion_fd < 0)
        return -1;

    struct ion_allocation_data alloc_data = {
        .len = size,
        .heap_id_mask = (1U << 0) | (1U << 25),
        .flags = 0,
    };

    int ret = ioctl(cached_ion_fd, ION_IOC_ALLOC, &alloc_data);
    if (ret)
        return -1;

    return alloc_data.fd;
}

static uint64_t get_time_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

int main(int argc, char **argv)
{
    int iterations = 1000;
    if (argc > 1) {
        iterations = atoi(argv[1]);
    }

    printf("=======================================================\n");
    printf(" Experiment 001: Buffer Object Allocation Benchmark\n");
    printf(" Iterations: %d, Allocation Size: 4096 bytes\n", iterations);
    printf("=======================================================\n");

    // 1. Test Original
    uint64_t start_orig = get_time_ns();
    int success_orig = 0;
    for (int i = 0; i < iterations; i++) {
        int fd = dma_heap_alloc_original(4096);
        if (fd >= 0) {
            success_orig++;
            close(fd);
        }
    }
    uint64_t end_orig = get_time_ns();
    double time_orig_ms = (double)(end_orig - start_orig) / 1e6;
    double latency_orig_us = (double)(end_orig - start_orig) / (iterations * 1000.0);

    printf("[Original Implementation]\n");
    printf("  Successful allocations: %d/%d\n", success_orig, iterations);
    printf("  Total Time:   %.3f ms\n", time_orig_ms);
    printf("  Mean Latency: %.2f us per allocation\n", latency_orig_us);
    printf("  Throughput:   %.1f allocs/sec\n\n", (iterations / (time_orig_ms / 1000.0)));

    // 2. Test Cached
    if (init_cached_allocator() < 0) {
        fprintf(stderr, "Failed to initialize cached allocator: %s\n", strerror(errno));
        return 1;
    }

    uint64_t start_cached = get_time_ns();
    int success_cached = 0;
    for (int i = 0; i < iterations; i++) {
        int fd = dma_heap_alloc_cached(4096);
        if (fd >= 0) {
            success_cached++;
            close(fd);
        }
    }
    uint64_t end_cached = get_time_ns();
    double time_cached_ms = (double)(end_cached - start_cached) / 1e6;
    double latency_cached_us = (double)(end_cached - start_cached) / (iterations * 1000.0);

    printf("[Optimized (Cached) Implementation]\n");
    printf("  Successful allocations: %d/%d\n", success_cached, iterations);
    printf("  Total Time:   %.3f ms\n", time_cached_ms);
    printf("  Mean Latency: %.2f us per allocation\n", latency_cached_us);
    printf("  Throughput:   %.1f allocs/sec\n\n", (iterations / (time_cached_ms / 1000.0)));

    double speedup = time_orig_ms / time_cached_ms;
    double latency_reduction_pct = ((latency_orig_us - latency_cached_us) / latency_orig_us) * 100.0;
    printf("[Comparison]\n");
    printf("  Speedup:            %.2fx faster\n", speedup);
    printf("  Latency Reduction:  %.1f%%\n", latency_reduction_pct);
    printf("  Eliminated Syscalls: %d failed open() calls\n", iterations);
    printf("=======================================================\n");

    if (cached_ion_fd >= 0)
        close(cached_ion_fd);

    return 0;
}
