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
import argparse

# --- ADAPTIVE CONFIGURATION ---
TOTAL_RAM_GB = psutil.virtual_memory().total / (1024**3)
IS_POWERFUL_PC = TOTAL_RAM_GB >= 8.0

# --- COLUMNS AND DTYPES ---
USE_COLS = ["ID_MUNICIP", "CS_SEXO", "NU_IDADE_N", "DT_NOTIFIC"]
PANDAS_DTYPES = {
    "ID_MUNICIP": "int32",
    "CS_SEXO": "category",
    "NU_IDADE_N": "float32",  # float because of potential NAs
    "DT_NOTIFIC": "category"
}

# --- SUBPROCESS RUNNER LOGIC ---

def track_metrics_internal(lib, size, op, iteration, func, is_warmup=False):
    if is_warmup:
        try:
            func()
        except:
            pass
        return

    gc.collect()
    process = psutil.Process()
    
    # Snapshots
    process.cpu_percent(interval=None) # Initialize process CPU percent
    t_start = time.perf_counter()
    cpu_start = process.cpu_times()
    disk_start = psutil.disk_io_counters()
    
    try:
        func()
    except MemoryError:
        print("STATUS:FAILED_OOM")
        sys.exit(0) # Exit cleanly so parent reads status
    except Exception as e:
        print(f"STATUS:FAILED_ERROR:{str(e)}")
        sys.exit(1)

    # End snapshots
    cpu_perc = process.cpu_percent(interval=None)
    t_end = time.perf_counter()
    cpu_end = process.cpu_times()
    disk_end = psutil.disk_io_counters()
    
    mem_peak = process.memory_info().rss / (1024 * 1024)
    mem_perc = process.memory_percent()
    
    result = {
        "library": lib, 
        "dataset_size": size, 
        "operation": op, 
        "iteration": int(iteration),
        "status": "SUCCESS",
        "time_s": round(t_end - t_start, 4), 
        "mem_mb": int(mem_peak),
        "cpu_user_s": round(cpu_end.user - cpu_start.user, 4), 
        "cpu_sys_s": round(cpu_end.system - cpu_start.system, 4),
        "disk_read_mb": int((disk_end.read_bytes - disk_start.read_bytes) / (1024 * 1024)),
        "disk_write_mb": int((disk_end.write_bytes - disk_start.write_bytes) / (1024 * 1024))
    }
    print(f"RESULT_JSON:{json.dumps(result)}")
    sys.exit(0)

def internal_run(lib, size, op, file_path, iteration, is_warmup=False):
    lookup_data = {"CS_SEXO": ["1", "2", "9"], "SEXO_DESC": ["M", "F", "I"]}
    lk_pd = pd.DataFrame(lookup_data)
    lk_pl = pl.DataFrame(lookup_data)

    try:
        if lib == "pandas":
            # Optimized reading with dtypes and usecols
            df = pd.read_csv(file_path, usecols=USE_COLS, dtype=PANDAS_DTYPES, na_values=["NA"], low_memory=False)
            if op == "filter": track_metrics_internal(lib, size, op, iteration, lambda: df[df["ID_MUNICIP"] == 355030], is_warmup)
            if op == "aggr": track_metrics_internal(lib, size, op, iteration, lambda: df.groupby("CS_SEXO", observed=True)["NU_IDADE_N"].sum(), is_warmup)
            if op == "join": track_metrics_internal(lib, size, op, iteration, lambda: df.merge(lk_pd, on="CS_SEXO"), is_warmup)
            if op == "sort": track_metrics_internal(lib, size, op, iteration, lambda: df.sort_values("DT_NOTIFIC"), is_warmup)
        
        if lib == "polars":
            if not IS_POWERFUL_PC:
                os.environ["POLARS_MAX_THREADS"] = "1"
                q = pl.scan_csv(file_path, null_values=["NA"], infer_schema_length=10000).select(USE_COLS)
                if op == "filter": track_metrics_internal(lib, size, op, iteration, lambda: q.filter(pl.col("ID_MUNICIP") == 355030).collect(engine='streaming'), is_warmup)
                if op == "aggr": track_metrics_internal(lib, size, op, iteration, lambda: q.group_by("CS_SEXO").agg(pl.col("NU_IDADE_N").sum()).collect(engine='streaming'), is_warmup)
                if op == "join": track_metrics_internal(lib, size, op, iteration, lambda: q.join(lk_pl.lazy(), on="CS_SEXO").collect(engine='streaming'), is_warmup)
                if op == "sort": 
                    track_metrics_internal(lib, size, op, iteration, lambda: q.sort("DT_NOTIFIC").collect(engine='streaming'), is_warmup)
            else:
                df = pl.read_csv(file_path, columns=USE_COLS, null_values=["NA"], infer_schema_length=10000)
                if op == "filter": track_metrics_internal(lib, size, op, iteration, lambda: df.filter(pl.col("ID_MUNICIP") == 355030), is_warmup)
                if op == "aggr": track_metrics_internal(lib, size, op, iteration, lambda: df.group_by("CS_SEXO").agg(pl.col("NU_IDADE_N").sum()), is_warmup)
                if op == "join": track_metrics_internal(lib, size, op, iteration, lambda: df.join(lk_pl, on="CS_SEXO"), is_warmup)
                if op == "sort": track_metrics_internal(lib, size, op, iteration, lambda: df.sort("DT_NOTIFIC"), is_warmup)

        if lib == "duckdb":
            # Optimized reading with SELECT
            cols_str = ", ".join(USE_COLS)
            csv_query = f"SELECT {cols_str} FROM read_csv_auto('{file_path}', nullstr='NA')"
            if op == "filter": track_metrics_internal(lib, size, op, iteration, lambda: duckdb.sql(f"SELECT * FROM ({csv_query}) WHERE ID_MUNICIP = 355030").df(), is_warmup)
            if op == "aggr": track_metrics_internal(lib, size, op, iteration, lambda: duckdb.sql(f"SELECT CS_SEXO, SUM(NU_IDADE_N) FROM ({csv_query}) GROUP BY CS_SEXO").df(), is_warmup)
            if op == "join": 
                duckdb.register("lk_pd", lk_pd)
                track_metrics_internal(lib, size, op, iteration, lambda: duckdb.sql(f"SELECT * FROM ({csv_query}) AS t JOIN lk_pd ON t.CS_SEXO = lk_pd.CS_SEXO").df(), is_warmup)
            if op == "sort": track_metrics_internal(lib, size, op, iteration, lambda: duckdb.sql(f"SELECT * FROM ({csv_query}) ORDER BY DT_NOTIFIC").df(), is_warmup)

        if lib == "pyspark":
            spark_mem = "8g" if IS_POWERFUL_PC else "1g"
            spark = SparkSession.builder.appName("Bench").config("spark.driver.memory", spark_mem).getOrCreate()
            # Optimized reading with select
            df = spark.read.csv(file_path, header=True, inferSchema=True, nullValue='NA').select(USE_COLS)
            lk_sp = spark.createDataFrame(lk_pd)
            if op == "filter": track_metrics_internal(lib, size, op, iteration, lambda: df.filter(df.ID_MUNICIP == 355030).collect(), is_warmup)
            if op == "aggr": track_metrics_internal(lib, size, op, iteration, lambda: df.groupBy("CS_SEXO").sum("NU_IDADE_N").collect(), is_warmup)
            if op == "join": track_metrics_internal(lib, size, op, iteration, lambda: df.join(lk_sp, "CS_SEXO").collect(), is_warmup)
            if op == "sort": track_metrics_internal(lib, size, op, iteration, lambda: df.sort("DT_NOTIFIC").collect(), is_warmup)
            spark.stop()
    except MemoryError:
        if not is_warmup: print("STATUS:FAILED_OOM")
        sys.exit(0)
    except Exception as e:
        if not is_warmup: print(f"STATUS:FAILED_ERROR:{str(e)}")
        sys.exit(1)

# --- MAIN RUNNER ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Data Processing Libraries")
    parser.add_argument("--internal-run", action="store_true", help="Run internally for a specific config")
    parser.add_argument("--lib", type=str, help="Library to test")
    parser.add_argument("--size", type=str, help="Dataset size label")
    parser.add_argument("--op", type=str, help="Operation to test")
    parser.add_argument("--path", type=str, help="Path to dataset")
    parser.add_argument("--iteration", type=int, help="Iteration number")
    parser.add_argument("--warmup", action="store_true", help="Run as warmup")
    
    args = parser.parse_args()

    if args.internal_run:
        internal_run(args.lib, args.size, args.op, args.path, args.iteration, args.warmup)
        sys.exit(0)

    print(f"System Check: {TOTAL_RAM_GB:.1f}GB RAM detected.")
    print(f"Mode: {'HIGH PERFORMANCE' if IS_POWERFUL_PC else 'SAFETY/LOW RAM'}")

    SCRIPT_PATH = os.path.abspath(__file__)
    SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
    
    datasets = {
        "256MB": os.path.join(PROJECT_ROOT, "data/dataset_256mb.csv"),
        "512MB": os.path.join(PROJECT_ROOT, "data/dataset_512mb.csv"),
        "1024MB": os.path.join(PROJECT_ROOT, "data/dataset_1024mb.csv"),
    }
    
    libs = ["pandas", "polars", "duckdb", "pyspark"]
    ops = ["filter", "aggr", "join", "sort"]
    NUM_ITERATIONS = 36
    results = []


    for label, path in datasets.items():
        if not os.path.exists(path): 
            print(f"Dataset {label} not found at {path}. Skipping.")
            continue
        print(f"\n>>> Dataset: {label}")

        for lib in libs:
            print(f"  Testing {lib}...")
            for op in ops:
                print(f"    Testing {op}...")
                
                # --- MEASUREMENT ---
                for i in range(NUM_ITERATIONS):
                    try:
                        cmd = [sys.executable, SCRIPT_PATH, "--internal-run", "--lib", lib, "--size", label, "--op", op, "--path", path, "--iteration", str(i+1)]
                        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
                        
                        found_result = False
                        status = "SUCCESS"
                        
                        if proc.returncode != 0:
                            status = "FAILED_CRASH"
                        
                        for line in proc.stdout.splitlines():
                            if line.startswith("RESULT_JSON:"):
                                res = json.loads(line.replace("RESULT_JSON:", ""))
                                results.append(res)
                                found_result = True
                            elif line.startswith("STATUS:"):
                                status = line.replace("STATUS:", "")

                        if not found_result:
                            # Handle OOM or other failures
                            if "FAILED_OOM" in status or proc.returncode == 137:
                                status = "FAILED_OOM"
                            
                            error_res = {
                                "library": lib, "dataset_size": label, "operation": op, "iteration": i+1,
                                "status": status, "time_s": None, "mem_mb": None
                            }
                            results.append(error_res)
                            print(f"      Iter {i+1}/{NUM_ITERATIONS}: {status}")
                        else:
                            last_res = results[-1]
                            if (i + 1) % 5 == 0 or (i + 1) == NUM_ITERATIONS:
                                print(f"      Iter {i+1}/{NUM_ITERATIONS}: {last_res['time_s']:.4f}s | CPU(user): {last_res.get('cpu_user_s', 0):.2f}s | RAM: {last_res.get('mem_mb', 0)}MB | DiskR: {last_res['disk_read_mb']}MB")
                                
                    except subprocess.TimeoutExpired:
                        print(f"      Iter {i+1}: TIMEOUT")
                        results.append({
                            "library": lib, "dataset_size": label, "operation": op, "iteration": i+1,
                            "status": "TIMEOUT", "time_s": None, "mem_mb": None
                        })

    with open("benchmark_results_csv.json", "w") as f:
        json.dump(results, f, indent=4)
    print("\nBenchmark complete. Results saved to benchmark_results_csv.json.")
