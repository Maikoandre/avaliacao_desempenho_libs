import marimo

__generated_with = "0.23.3"
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
    return (data,)


@app.cell
def _(pl):
    polars = pl.read_parquet('data/sinan_dengue_sample_2024.parquet')
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
        # Warmup
        for _ in range(warmup):
            func()

        times = []
        # Cabeçalho da Tabela
        print(f"{'Run':>5} | {'Duração (s)':>15}")
        print("-" * 23)

        for i in range(1, n + 1):
            start = time.perf_counter()
            func()
            end = time.perf_counter()

            duration = end - start
            times.append(duration)
            # Linha da Tabela
            print(f"{i:>5} | {duration:>15.6f}")

        # Estatísticas Finais
        print("-" * 23)
        print(f"Média:  {statistics.mean(times):.6f}s")
        print(f"Mín:    {min(times):.6f}s")
        print(f"Máx:    {max(times):.6f}s")
        print(f"Desvio: {statistics.stdev(times):.6f}s")

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
        return pd.read_parquet("data/sinan_dengue_sample_2024.parquet")

    benchmark(read_duckdb)
    print('\n')
    benchmark(read_pandas)
    return


@app.cell
def _(pl):
    def read_polars():
        return pl.scan_parquet('data/sinan_dengue_sample_2024.parquet')

    return (read_polars,)


@app.cell
def _(benchmark, read_polars):
    benchmark(read_polars)
    return


@app.cell
def _(session):
    def read_spark():
        return session.read.parquet('data/sinan_dengue_sample_2024.parquet')

    return (read_spark,)


@app.cell
def _(benchmark, read_spark):
    benchmark(read_spark)
    return


@app.cell
def _(data):
    data.shape
    return


if __name__ == "__main__":
    app.run()
