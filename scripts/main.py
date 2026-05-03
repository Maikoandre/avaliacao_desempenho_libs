import pandas as pd
from pyspark.sql import SparkSession
import pyarrow.parquet as pq
import duckdb
import polars as pl
import time
import statistics
import os

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DATA_PATH = os.path.join(PROJECT_ROOT, 'data/sinan_dengue_1gb.parquet')
N_RUNS = 5
WARMUP = 1

def benchmark(name, func, n=N_RUNS, warmup=WARMUP):
    print(f"\n{'='*40}")
    print(f" Benchmarking: {name}")
    print(f"{'='*40}")
    
    # Warmup
    for _ in range(warmup):
        func()

    times = []
    print(f"{'Run':>5} | {'Duration (s)':>15}")
    print("-" * 23)

    for i in range(1, n + 1):
        start = time.perf_counter()
        func()
        end = time.perf_counter()

        duration = end - start
        times.append(duration)
        print(f"{i:>5} | {duration:>15.6f}")

    print("-" * 23)
    print(f"Mean:   {statistics.mean(times):.6f}s")
    print(f"Min:    {min(times):.6f}s")
    print(f"Max:    {max(times):.6f}s")
    print(f"StdDev: {statistics.stdev(times):.6f}s")
    return times

def run_benchmarks():
    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} not found. Run duplicate script first.")
        return

    # Spark Session
    session = SparkSession.builder \
        .appName("LibraryBenchmark") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    session.sparkContext.setLogLevel("ERROR")

    # Functions
    def read_duckdb():
        return duckdb.sql(f"SELECT * FROM '{DATA_PATH}' LIMIT 5").df()

    def read_pandas():
        pf = pq.ParquetFile(DATA_PATH)
        return next(pf.iter_batches(batch_size=5)).to_pandas()

    def read_polars():
        return pl.read_parquet(DATA_PATH, n_rows=5)

    def read_spark():
        return session.read.parquet(DATA_PATH).limit(5).collect()

    # Execution
    benchmark("DuckDB", read_duckdb)
    benchmark("Pandas", read_pandas)
    benchmark("Polars", read_polars)
    benchmark("PySpark", read_spark)

    session.stop()

if __name__ == "__main__":
    run_benchmarks()
