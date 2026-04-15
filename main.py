import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import pandas as pd
    from pyspark.sql import SparkSession
    import duckdb
    import polars as pl
    import time
    import statistics

    return SparkSession, duckdb, pd, pl, statistics, time


@app.cell
def _(pd):
    data = pd.read_parquet('data/sinan_dengue_sample_2024.parquet')
    data.head(5)
    return


@app.cell
def _(pl):
    polars = pl.scan_parquet('data/sinan_dengue_sample_2024.parquet')
    polars.head(5)
    return


@app.cell
def _(SparkSession):
    session = SparkSession.builder.appName("ReadParquet").getOrCreate()
    return (session,)


@app.cell
def _(session):
    spark = session.read.parquet('data/sinan_dengue_sample_2024.parquet')
    spark.show(5)
    return


@app.cell
def _(duckdb):
    df = duckdb.sql("""
        SELECT *
        FROM 'data/sinan_dengue_sample_2024.parquet'
        LIMIT 5
    """).df()

    print(df)
    return


@app.cell
def _(statistics, time):
    def benchmark(func, n=10, warmup=2):
        # warm-up (importante pra coisas tipo DuckDB / Spark)
        for _ in range(warmup):
            func()

        times = []
        for _ in range(n):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append(end - start)

        print(f"runs: {n}")
        print(f"mean: {statistics.mean(times):.6f}s")
        print(f"min:  {min(times):.6f}s")
        print(f"max:  {max(times):.6f}s")
        print(f"std:  {statistics.stdev(times):.6f}s")

    return (benchmark,)


@app.cell
def _(benchmark, duckdb):
    def read_duckdb():
        return duckdb.sql("""
            SELECT *
            FROM 'data/sinan_dengue_sample_2024.parquet'
            LIMIT 5
        """).df()

    benchmark(read_duckdb)
    return (read_duckdb,)


@app.cell
def _(benchmark, pd, read_duckdb):
    def read_pandas():
        return pd.read_parquet("data/sinan_dengue_sample_2024.parquet").head(5)

    benchmark(read_duckdb)
    print('\n')
    benchmark(read_pandas)
    return


if __name__ == "__main__":
    app.run()
