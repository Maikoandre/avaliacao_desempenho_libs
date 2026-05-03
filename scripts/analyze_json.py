import polars as pl

df = pl.read_json("scripts/benchmark_results.json")

print(df.head(5))

print(df.describe())

print(df.group_by(["operation", "library"]).agg(pl.sum("time_s").alias("total_time")).sort(["operation", "total_time"]))

print(df.group_by(["operation", "library"]).agg(pl.mean("time_s").alias("average_time")).sort(["operation", "average_time"]))