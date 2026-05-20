import time
import resource
import gc
import os


def measure_all(func, include_children=False):
    """Mede tempo, CPU e memória pico em uma única execução."""
    gc.collect()
    t_start = time.perf_counter()
    ru_start = resource.getrusage(resource.RUSAGE_SELF)
    if include_children:
        ru_children_start = resource.getrusage(resource.RUSAGE_CHILDREN)

    func()

    t_end = time.perf_counter()
    ru_end = resource.getrusage(resource.RUSAGE_SELF)
    if include_children:
        ru_children_end = resource.getrusage(resource.RUSAGE_CHILDREN)

    user = ru_end.ru_utime - ru_start.ru_utime
    sys = ru_end.ru_stime - ru_start.ru_stime
    mem = ru_end.ru_maxrss

    if include_children:
        user += ru_children_end.ru_utime - ru_children_start.ru_utime
        sys += ru_children_end.ru_stime - ru_children_start.ru_stime
        mem = max(mem, ru_children_end.ru_maxrss)

    return {
        "time_s": round(t_end - t_start, 4),
        "cpu_user_s": round(user, 4),
        "cpu_sys_s": round(sys, 4),
        "mem_peak_mb": round(mem / 1024, 2),
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
                    with open(f"/proc/{entry}/cmdline") as cmd:
                        if b"java" in cmd.read().lower().encode():
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


def _read_proc_cpu_times(pid):
    """Lê tempos de CPU de /proc/<pid>/stat em segundos."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            parts = f.read().split()
            utime = int(parts[13]) / os.sysconf("SC_CLK_TCK")
            stime = int(parts[14]) / os.sysconf("SC_CLK_TCK")
            return utime, stime
    except (FileNotFoundError, PermissionError, ProcessLookupError, IndexError):
        pass
    return 0.0, 0.0


def measure_all_spark(func):
    """Mede tempo, CPU e memória incluindo processos Java filhos do Spark."""
    gc.collect()
    t_start = time.perf_counter()
    ru_start = resource.getrusage(resource.RUSAGE_SELF)

    java_pids_before = _get_java_child_pids()
    cpu_before = sum(_read_proc_cpu_times(p) for p in java_pids_before)

    func()

    t_end = time.perf_counter()
    ru_end = resource.getrusage(resource.RUSAGE_SELF)

    java_pids_after = _get_java_child_pids()
    cpu_after = sum(_read_proc_cpu_times(p) for p in java_pids_after)
    mem_java = max((_read_proc_mem_mb(p) for p in java_pids_after), default=0)

    all_pids = set(java_pids_before) | set(java_pids_after)
    mem_java = max((_read_proc_mem_mb(p) for p in all_pids), default=0)

    user = (ru_end.ru_utime - ru_start.ru_utime) + (cpu_after[0] - cpu_before[0])
    sys = (ru_end.ru_stime - ru_start.ru_stime) + (cpu_after[1] - cpu_before[1])
    mem = max(ru_end.ru_maxrss / 1024, mem_java)

    return {
        "time_s": round(t_end - t_start, 4),
        "cpu_user_s": round(user, 4),
        "cpu_sys_s": round(sys, 4),
        "mem_peak_mb": round(mem, 2),
    }
