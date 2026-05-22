import time
import resource
import gc
import os


def measure_all(func):
    """Mede tempo e memória pico em uma única execução."""
    gc.collect()
    t_start = time.perf_counter()

    func()

    t_end = time.perf_counter()

    wall_time = t_end - t_start

    return {
        "time_s": round(wall_time, 4),
        "mem_peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
    }


def _get_java_child_pids():
    """Encontra PIDs de processos Java filhos do processo atual."""
    my_pid = os.getpid()
    java_pids = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/status") as f:
                ppid = None
                for line in f:
                    if line.startswith("PPid:"):
                        ppid = int(line.split()[1])
                        break
                if ppid == my_pid:
                    with open(f"/proc/{entry}/cmdline", "rb") as cmd:
                        if b"java" in cmd.read().lower():
                            java_pids.append(int(entry))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    return java_pids


def _read_proc_mem_mb(pid):
    """Lê VmHWM (pico de memória) de /proc/<pid>/status em MB."""
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) / 1024
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        pass
    return 0


def measure_all_spark(func):
    """Mede tempo e memória incluindo processos Java filhos do Spark."""
    gc.collect()
    t_start = time.perf_counter()

    java_pids_before = _get_java_child_pids()

    func()

    t_end = time.perf_counter()

    java_pids_after = _get_java_child_pids()
    mem_java = max((_read_proc_mem_mb(p) for p in set(java_pids_before) | set(java_pids_after)), default=0)

    wall_time = t_end - t_start
    mem = max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, mem_java)

    return {
        "time_s": round(wall_time, 4),
        "mem_peak_mb": round(mem, 2),
    }
