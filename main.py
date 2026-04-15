import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import pandas as pd
    from pyspark.sql import SparkSession
    import duckdb
    import polars as pl
    import pytest_benchmark as pb
    import marimo as mo

    return SparkSession, duckdb, pd, pl


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


if __name__ == "__main__":
    app.run()
