import os
import time
import psutil
import pandas as pd
import polars as pl
import duckdb
from pyspark.sql import SparkSession
import json
import gc
import sys
import subprocess

# --- SUBPROCESS RUNNER LOGIC ---
# This allows running each benchmark in a clean process, 
# preventing cumulative memory buildup on low-RAM systems.

def track_metrics_internal(lib, size, op, func):
    gc.collect()
    process = psutil.Process()
    t_start = time.perf_counter()
    cpu_start = process.cpu_times()
    
    try:
        func()
        success = True
    except Exception as e:
        print(f"FAILED: {str(e)}")
        sys.exit(1)

    t_end = time.perf_counter()
    cpu_end = process.cpu_times()
    mem_peak = process.memory_info().rss / (1024 * 1024)
    
    # Print result in a parsable format for the parent
    result = {
        "library": lib, "dataset_size": size, "operation": op,
        "time_s": t_end - t_start, "mem_mb": mem_peak,
        "cpu_user_s": cpu_end.user - cpu_start.user, "cpu_sys_s": cpu_end.system - cpu_start.system
    }
    print(f"RESULT_JSON:{json.dumps(result)}")
    sys.exit(0)

def internal_run(lib, size, op, file_path):
    # Small lookup for joins
    lookup_data = {"CS_SEXO": ["1", "2", "9"], "SEXO_DESC": ["M", "F", "I"]}
    lk_pd = pd.DataFrame(lookup_data)
    lk_pl = pl.DataFrame(lookup_data)

    if lib == "pandas":
        df = pd.read_parquet(file_path)
        if op == "filter": track_metrics_internal(lib, size, op, lambda: df[df["ID_MUNICIP"] == 355030])
        if op == "aggr": track_metrics_internal(lib, size, op, lambda: df.groupby("CS_SEXO")["NU_IDADE_N"].sum())
        if op == "join": track_metrics_internal(lib, size, op, lambda: df.merge(lk_pd, on="CS_SEXO"))
        if op == "sort": track_metrics_internal(lib, size, op, lambda: df.sort_values("DT_NOTIFIC"))
    
    if lib == "polars":
        # Limit threads to save RAM on 4GB systems
        os.environ["POLARS_MAX_THREADS"] = "2"
        q = pl.scan_parquet(file_path)
        if op == "filter": track_metrics_internal(lib, size, op, lambda: q.filter(pl.col("ID_MUNICIP") == 355030).collect(engine='streaming'))
        if op == "aggr": track_metrics_internal(lib, size, op, lambda: q.group_by("CS_SEXO").agg(pl.col("NU_IDADE_N").sum()).collect(engine='streaming'))
        if op == "join": track_metrics_internal(lib, size, op, lambda: q.join(lk_pl.lazy(), on="CS_SEXO").collect(engine='streaming'))
        if op == "sort": track_metrics_internal(lib, size, op, lambda: q.sort("DT_NOTIFIC").collect(engine='streaming'))

    if lib == "duckdb":
        if op == "filter": track_metrics_internal(lib, size, op, lambda: duckdb.sql(f"SELECT * FROM '{file_path}' WHERE ID_MUNICIP = 355030").df())
        if op == "aggr": track_metrics_internal(lib, size, op, lambda: duckdb.sql(f"SELECT CS_SEXO, SUM(NU_IDADE_N) FROM '{file_path}' GROUP BY CS_SEXO").df())
        if op == "join": track_metrics_internal(lib, size, op, lambda: duckdb.sql(f"SELECT * FROM '{file_path}' AS t JOIN lk_pd ON t.CS_SEXO = lk_pd.CS_SEXO").df())
        if op == "sort": track_metrics_internal(lib, size, op, lambda: duckdb.sql(f"SELECT * FROM '{file_path}' ORDER BY DT_NOTIFIC").df())

    if lib == "pyspark":
        spark = SparkSession.builder.appName("Bench").config("spark.driver.memory", "1g").getOrCreate()
        df = spark.read.parquet(file_path)
        lk_sp = spark.createDataFrame(lk_pd)
        if op == "filter": track_metrics_internal(lib, size, op, lambda: df.filter(df.ID_MUNICIP == 355030).collect())
        if op == "aggr": track_metrics_internal(lib, size, op, lambda: df.groupBy("CS_SEXO").sum("NU_IDADE_N").collect())
        if op == "join": track_metrics_internal(lib, size, op, lambda: df.join(lk_sp, "CS_SEXO").collect())
        if op == "sort": track_metrics_internal(lib, size, op, lambda: df.sort("DT_NOTIFIC").collect())
        spark.stop()

# --- MAIN RUNNER ---

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--internal-run":
        internal_run(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
        sys.exit(0)

    SCRIPT_PATH = os.path.abspath(__file__)
    SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
    
    datasets = {
        "500MB": os.path.join(PROJECT_ROOT, "data/dataset_500mb.parquet"),
        "1GB": os.path.join(PROJECT_ROOT, "data/dataset_1gb.parquet"),
        "2GB": os.path.join(PROJECT_ROOT, "data/dataset_2gb.parquet")
    }
    
    libs = ["duckdb", "polars", "pandas", "pyspark"]
    ops = ["filter", "aggr", "join", "sort"]
    
    total_ram_gb = psutil.virtual_memory().total / (1024**3)
    results = []

    for label, path in datasets.items():
        if not os.path.exists(path): continue
        print(f"\n>>> Dataset: {label}")
        file_size_gb = os.path.getsize(path) / (1024**3)

        for lib in libs:
            # Safety: skip pandas if file > 250MB on 4GB RAM
            if lib == "pandas" and total_ram_gb < 6 and file_size_gb > 0.25:
                print(f"[{lib}] Skipping {label} (Safety)")
                continue

            print(f"  Testing {lib}...")
            for op in ops:
                # Run as subprocess
                try:
                    cmd = [sys.executable, SCRIPT_PATH, "--internal-run", lib, label, op, path]
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    
                    if proc.returncode == 0:
                        # Extract JSON from output
                        for line in proc.stdout.splitlines():
                            if line.startswith("RESULT_JSON:"):
                                res = json.loads(line.replace("RESULT_JSON:", ""))
                                results.append(res)
                                print(f"    {op}: {res['time_s']:.4f}s")
                    else:
                        print(f"    {op}: FAILED (Crash/OOM)")
                except subprocess.TimeoutExpired:
                    print(f"    {op}: TIMEOUT")

    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=4)
    print("\nBenchmark complete. Results saved.")
