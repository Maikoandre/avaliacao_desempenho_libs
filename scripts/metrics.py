import time
import resource
import gc
import os


def _get_cpu_frequency_mhz():
    """Lê a frequência máxima do CPU em MHz a partir de /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("cpu MHz"):
                    return float(line.split(":")[1].strip())
    except (FileNotFoundError, ValueError):
        pass
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq") as f:
            return int(f.read().strip()) / 1000
    except (FileNotFoundError, ValueError):
        pass
    return 2500.0


def measure_all(func):
    """Mede tempo, CPU e memória pico em uma única execução."""
    gc.collect()
    cpu_freq_mhz = _get_cpu_frequency_mhz()
    t_start = time.perf_counter()
    ru_start = resource.getrusage(resource.RUSAGE_SELF)

    func()

    t_end = time.perf_counter()
    ru_end = resource.getrusage(resource.RUSAGE_SELF)

    wall_time = t_end - t_start
    cpu_time = (ru_end.ru_utime - ru_start.ru_utime) + (ru_end.ru_stime - ru_start.ru_stime)

    mips = (cpu_time / wall_time * cpu_freq_mhz) if wall_time > 0 else 0.0

    return {
        "time_s": round(wall_time, 4),
        "cpu_user_s": round(ru_end.ru_utime - ru_start.ru_utime, 4),
        "cpu_sys_s": round(ru_end.ru_stime - ru_start.ru_stime, 4),
        "cpu_mips": round(mips, 2),
        "mem_peak_mb": round(ru_end.ru_maxrss / 1024, 2),
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


def _read_proc_cpu_times(pid):
    """Lê tempos de CPU de /proc/<pid>/stat em segundos."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            parts = f.read().split()
            clk = os.sysconf("SC_CLK_TCK")
            utime = int(parts[13]) / clk
            stime = int(parts[14]) / clk
            return utime, stime
    except (FileNotFoundError, PermissionError, ProcessLookupError, IndexError):
        pass
    return 0.0, 0.0


def measure_all_spark(func):
    """Mede tempo, CPU e memória incluindo processos Java filhos do Spark."""
    gc.collect()
    cpu_freq_mhz = _get_cpu_frequency_mhz()
    t_start = time.perf_counter()
    ru_start = resource.getrusage(resource.RUSAGE_SELF)

    java_pids_before = _get_java_child_pids()
    cpu_before = sum((_read_proc_cpu_times(p) for p in java_pids_before), start=(0.0, 0.0))

    func()

    t_end = time.perf_counter()
    ru_end = resource.getrusage(resource.RUSAGE_SELF)

    java_pids_after = _get_java_child_pids()
    cpu_after = sum((_read_proc_cpu_times(p) for p in java_pids_after), start=(0.0, 0.0))
    mem_java = max((_read_proc_mem_mb(p) for p in set(java_pids_before) | set(java_pids_after)), default=0)

    wall_time = t_end - t_start
    user = (ru_end.ru_utime - ru_start.ru_utime) + (cpu_after[0] - cpu_before[0])
    sys = (ru_end.ru_stime - ru_start.ru_stime) + (cpu_after[1] - cpu_before[1])
    cpu_time = user + sys
    mips = (cpu_time / wall_time * cpu_freq_mhz) if wall_time > 0 else 0.0
    mem = max(ru_end.ru_maxrss / 1024, mem_java)

    return {
        "time_s": round(wall_time, 4),
        "cpu_user_s": round(user, 4),
        "cpu_sys_s": round(sys, 4),
        "cpu_mips": round(mips, 2),
        "mem_peak_mb": round(mem, 2),
    }
