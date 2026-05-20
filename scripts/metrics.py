import time
import resource
import tracemalloc
import gc


def measure_execution_time(func):
    """Mede o tempo de execução de uma função em segundos."""
    gc.collect()
    start = time.perf_counter()
    func()
    end = time.perf_counter()
    return round(end - start, 4)


def measure_cpu_usage(func):
    """Mede o uso de CPU (user + system) de uma função em segundos."""
    gc.collect()
    ru_start = resource.getrusage(resource.RUSAGE_SELF)
    func()
    ru_end = resource.getrusage(resource.RUSAGE_SELF)
    user_time = round(ru_end.ru_utime - ru_start.ru_utime, 4)
    sys_time = round(ru_end.ru_stime - ru_start.ru_stime, 4)
    return {"user_s": user_time, "system_s": sys_time}


def measure_memory_consumption(func):
    """Mede o pico de consumo de memória de uma função em MB."""
    gc.collect()
    tracemalloc.start()
    func()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"current_mb": round(current / (1024 * 1024), 2), "peak_mb": round(peak / (1024 * 1024), 2)}


def measure_all(func):
    """Mede tempo, CPU e memória em uma única execução da função."""
    gc.collect()
    tracemalloc.start()
    t_start = time.perf_counter()
    ru_start = resource.getrusage(resource.RUSAGE_SELF)

    func()

    t_end = time.perf_counter()
    ru_end = resource.getrusage(resource.RUSAGE_SELF)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "time_s": round(t_end - t_start, 4),
        "cpu_user_s": round(ru_end.ru_utime - ru_start.ru_utime, 4),
        "cpu_sys_s": round(ru_end.ru_stime - ru_start.ru_stime, 4),
        "mem_current_mb": round(current / (1024 * 1024), 2),
        "mem_peak_mb": round(peak / (1024 * 1024), 2),
    }
