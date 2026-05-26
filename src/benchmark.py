import os
import sys
import json
import subprocess
import argparse
import pandas as pd
import polars as pl
import duckdb
from pyspark.sql import SparkSession
from metrics import measure_all, measure_all_spark

# --- COLUMNS AND DTYPES ---
USE_COLS = ["ID_MUNICIP", "CS_SEXO", "NU_IDADE_N", "DT_NOTIFIC"]
PANDAS_DTYPES = {
    "ID_MUNICIP": "int32",
    "CS_SEXO": "category",
    "NU_IDADE_N": "float32",
    "DT_NOTIFIC": "category"
}

# --- SUBPROCESS RUNNER LOGIC ---

def track_metrics_internal(lib, size, op, iteration, pipeline_func, is_warmup=False):
    if is_warmup:
        try:
            pipeline_func()
        except:
            pass
        return

    try:
        metrics = measure_all_spark(pipeline_func) if lib == "pyspark" else measure_all(pipeline_func)
    except MemoryError:
        print("STATUS:FAILED_OOM")
        sys.exit(0)
    except Exception as e:
        print(f"STATUS:FAILED_ERROR:{str(e)}")
        sys.exit(1)

    result = {
        "library": lib,
        "dataset_size": size,
        "operation": op,
        "iteration": int(iteration),
        "status": "SUCCESS",
        "time_s": metrics["time_s"],
        "mem_mb": metrics["mem_peak_mb"],
    }
    print(f"RESULT_JSON:{json.dumps(result)}")
    sys.exit(0)

def internal_run(lib, size, op, file_path, iteration, is_warmup=False, phase="operation"):
    try:
        if lib == "pandas":
            def load():
                return pd.read_csv(file_path, usecols=USE_COLS, dtype=PANDAS_DTYPES, na_values=["NA"], low_memory=False)

            def operation(df):
                lk = pd.DataFrame({"CS_SEXO": ["1", "2", "9"], "SEXO_DESC": ["M", "F", "I"]})
                if op == "filter": return df[df["ID_MUNICIP"] == 355030]
                if op == "aggr": return df.groupby("CS_SEXO", observed=True)["NU_IDADE_N"].sum()
                if op == "join": return df.merge(lk, on="CS_SEXO")
                if op == "sort": return df.sort_values("DT_NOTIFIC")

            if phase == "load":
                op_name = f"load_{op}" if op != "load" else "load"
                track_metrics_internal(lib, size, op_name, iteration, load, is_warmup)
            else:
                df = load()
                track_metrics_internal(lib, size, op, iteration, lambda: operation(df), is_warmup)

        elif lib == "polars":
            def load():
                return pl.read_csv(file_path, columns=USE_COLS, null_values=["NA"], infer_schema_length=10000)

            def operation(df):
                lk = pl.DataFrame({"CS_SEXO": ["1", "2", "9"], "SEXO_DESC": ["M", "F", "I"]})
                if op == "filter": return df.filter(pl.col("ID_MUNICIP") == 355030)
                if op == "aggr": return df.group_by("CS_SEXO").agg(pl.col("NU_IDADE_N").sum())
                if op == "join": return df.join(lk, on="CS_SEXO")
                if op == "sort": return df.sort("DT_NOTIFIC")

            if phase == "load":
                op_name = f"load_{op}" if op != "load" else "load"
                track_metrics_internal(lib, size, op_name, iteration, load, is_warmup)
            else:
                df = load()
                track_metrics_internal(lib, size, op, iteration, lambda: operation(df), is_warmup)

        elif lib == "duckdb":
            def load():
                cols_str = ", ".join(USE_COLS)
                duckdb.sql(f"CREATE OR REPLACE TABLE _bench_data AS SELECT {cols_str} FROM read_csv_auto('{file_path}', nullstr='NA')")
                return duckdb.table("_bench_data")

            def operation(rel):
                lk = pd.DataFrame({"CS_SEXO": ["1", "2", "9"], "SEXO_DESC": ["M", "F", "I"]})
                if op == "filter": return duckdb.sql("SELECT * FROM _bench_data WHERE ID_MUNICIP = 355030").df()
                if op == "aggr": return duckdb.sql("SELECT CS_SEXO, SUM(NU_IDADE_N) FROM _bench_data GROUP BY CS_SEXO").df()
                if op == "join":
                    duckdb.register("_bench_lk", lk)
                    return duckdb.sql("SELECT * FROM _bench_data JOIN _bench_lk ON _bench_data.CS_SEXO = _bench_lk.CS_SEXO").df()
                if op == "sort": return duckdb.sql("SELECT * FROM _bench_data ORDER BY DT_NOTIFIC").df()

            if phase == "load":
                op_name = f"load_{op}" if op != "load" else "load"
                track_metrics_internal(lib, size, op_name, iteration, load, is_warmup)
            else:
                rel = load()
                track_metrics_internal(lib, size, op, iteration, lambda: operation(rel), is_warmup)

        elif lib == "pyspark":
            def load():
                spark_mem = "1g"
                spark = SparkSession.builder.appName("Bench").config("spark.driver.memory", spark_mem).getOrCreate()
                df = spark.read.csv(file_path, header=True, inferSchema=True, nullValue='NA').select(USE_COLS)
                df.count()

            def setup_spark_and_df():
                spark_mem = "1g"
                spark = SparkSession.builder.appName("Bench").config("spark.driver.memory", spark_mem).getOrCreate()
                df = spark.read.csv(file_path, header=True, inferSchema=True, nullValue='NA').select(USE_COLS)
                df.cache().count()
                return spark, df

            def operation(spark, df):
                lk = spark.createDataFrame([("1", "M"), ("2", "F"), ("9", "I")], ["CS_SEXO", "SEXO_DESC"])
                if op == "filter": result = df.filter(df.ID_MUNICIP == 355030).collect()
                elif op == "aggr": result = df.groupBy("CS_SEXO").sum("NU_IDADE_N").collect()
                elif op == "join": result = df.join(lk, "CS_SEXO").collect()
                elif op == "sort": result = df.sort("DT_NOTIFIC").collect()

            if phase == "load":
                op_name = f"load_{op}" if op != "load" else "load"
                track_metrics_internal(lib, size, op_name, iteration, load, is_warmup)
            else:
                spark, df = setup_spark_and_df()
                track_metrics_internal(lib, size, op, iteration, lambda: operation(spark, df), is_warmup)

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
    parser.add_argument("--phase", type=str, default="operation", choices=["load", "operation"], help="Benchmark phase")

    args = parser.parse_args()

    if args.internal_run:
        internal_run(args.lib, args.size, args.op, args.path, args.iteration, args.warmup, args.phase)
        sys.exit(0)

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
    NUM_ITERATIONS = 48
    results = []

    for label, path in datasets.items():
        if not os.path.exists(path):
            print(f"Dataset {label} not found at {path}. Skipping.")
            continue
        print(f"\n>>> Dataset: {label}")

        for lib in libs:
            print(f"  Testing {lib}...")

            # --- PHASE: LOAD ---
            print("    Phase: load")
            warmup_cmd = [sys.executable, SCRIPT_PATH, "--internal-run", "--lib", lib, "--size", label, "--op", "load", "--path", path, "--iteration", "0", "--phase", "load", "--warmup"]
            subprocess.run(warmup_cmd, capture_output=True, text=True, timeout=900)
            for i in range(NUM_ITERATIONS):
                try:
                    cmd = [sys.executable, SCRIPT_PATH, "--internal-run", "--lib", lib, "--size", label, "--op", "load", "--path", path, "--iteration", str(i+1), "--phase", "load"]
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
                        if "FAILED_OOM" in status or proc.returncode == 137:
                            status = "FAILED_OOM"
                        error_res = {
                            "library": lib, "dataset_size": label, "operation": "load", "iteration": i+1,
                            "status": status, "time_s": None, "mem_mb": None
                        }
                        results.append(error_res)
                        print(f"      Iter {i+1}/{NUM_ITERATIONS}: {status}")
                    else:
                        last_res = results[-1]
                        if (i + 1) % 5 == 0 or (i + 1) == NUM_ITERATIONS:
                            print(f"      Iter {i+1}/{NUM_ITERATIONS}: {last_res['time_s']:.4f}s | RAM: {last_res.get('mem_mb', 0)}MB")

                except subprocess.TimeoutExpired:
                    print(f"      Iter {i+1}: TIMEOUT")
                    results.append({
                        "library": lib, "dataset_size": label, "operation": "load", "iteration": i+1,
                        "status": "TIMEOUT", "time_s": None, "mem_mb": None
                    })

            for op in ops:
                # --- PHASE: OPERATION ---
                print(f"    Phase: {op}")
                warmup_cmd = [sys.executable, SCRIPT_PATH, "--internal-run", "--lib", lib, "--size", label, "--op", op, "--path", path, "--iteration", "0", "--phase", "operation", "--warmup"]
                subprocess.run(warmup_cmd, capture_output=True, text=True, timeout=900)
                for i in range(NUM_ITERATIONS):
                    try:
                        cmd = [sys.executable, SCRIPT_PATH, "--internal-run", "--lib", lib, "--size", label, "--op", op, "--path", path, "--iteration", str(i+1), "--phase", "operation"]
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
                                print(f"      Iter {i+1}/{NUM_ITERATIONS}: {last_res['time_s']:.4f}s | RAM: {last_res.get('mem_mb', 0)}MB")

                    except subprocess.TimeoutExpired:
                        print(f"      Iter {i+1}: TIMEOUT")
                        results.append({
                            "library": lib, "dataset_size": label, "operation": op, "iteration": i+1,
                            "status": "TIMEOUT", "time_s": None, "mem_mb": None
                        })

    with open("benchmark_results_csv.json", "w") as f:
        json.dump(results, f, indent=4)
    print("\nBenchmark complete. Results saved to benchmark_results_csv.json.")
