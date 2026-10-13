// Read-only macOS PID/birth-qualified memory observation; never launches/signals.
#include <errno.h>
#include <inttypes.h>
#include <libproc.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/proc_info.h>
#include <sys/resource.h>
#include <time.h>

static uint64_t monotonic_ns(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts)) return 0;
    return (uint64_t)ts.tv_sec * 1000000000ull + ts.tv_nsec;
}
static int birth(pid_t pid, struct proc_bsdinfo *info) {
    memset(info, 0, sizeof(*info));
    return proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, info, sizeof(*info)) == sizeof(*info)
        && info->pbi_pid == (uint32_t)pid;
}
int main(int argc, char **argv) {
    if (argc != 2 && argc != 4) { fprintf(stderr, "usage: proc-memory PID [BIRTH_SEC BIRTH_USEC]\n"); return 2; }
    char *end = NULL;
    long value = strtol(argv[1], &end, 10);
    if (!end || *end || value <= 1 || value > INT32_MAX) return 2;
    pid_t pid = (pid_t)value;
    uint64_t begin = monotonic_ns();
    struct proc_bsdinfo before, after;
    struct rusage_info_v4 usage = {0};
    if (!birth(pid, &before)) { fprintf(stderr, "NOT-RUN identity-before errno=%d\n", errno); return 3; }
    if (argc == 4) {
        char *sec_end = NULL, *usec_end = NULL;
        uint64_t sec = strtoull(argv[2], &sec_end, 10), usec = strtoull(argv[3], &usec_end, 10);
        if (!sec_end || *sec_end || !usec_end || *usec_end || usec >= 1000000) return 2;
        if (sec != before.pbi_start_tvsec || usec != before.pbi_start_tvusec) {
            fprintf(stderr, "NOT-RUN expected-birth-mismatch\n"); return 4;
        }
    }
    if (proc_pid_rusage(pid, RUSAGE_INFO_V4, (rusage_info_t *)&usage)) {
        fprintf(stderr, "NOT-RUN rusage errno=%d\n", errno); return 3;
    }
    if (!birth(pid, &after) || before.pbi_start_tvsec != after.pbi_start_tvsec
        || before.pbi_start_tvusec != after.pbi_start_tvusec) {
        fprintf(stderr, "NOT-RUN birth-changed-during-read\n"); return 4;
    }
    uint64_t finish = monotonic_ns();
    printf("{\"schema\":1,\"pid\":%d,\"birth_sec\":%" PRIu64 ",\"birth_usec\":%" PRIu64
        ",\"expected_birth_checked\":%s,\"clock\":\"host_CLOCK_MONOTONIC_ns\",\"sample_begin_ns\":%" PRIu64
        ",\"sample_end_ns\":%" PRIu64 ",\"rss_bytes\":%" PRIu64 ",\"physical_footprint_bytes\":%" PRIu64
        ",\"kernel_lifetime_max_physical_footprint_bytes\":%" PRIu64
        ",\"rusage_proc_start_mach_abstime_ticks\":%" PRIu64 "}\n",
        pid, before.pbi_start_tvsec, before.pbi_start_tvusec, argc == 4 ? "true" : "false",
        begin, finish, usage.ri_resident_size, usage.ri_phys_footprint,
        usage.ri_lifetime_max_phys_footprint, usage.ri_proc_start_abstime);
    return 0;
}
