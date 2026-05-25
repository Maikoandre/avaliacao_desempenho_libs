import marimo

__generated_with = "0.23.3"
app = marimo.App(width="medium")


@app.cell
def _():
    import polars as pl
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    import altair as alt

    plt.style.use('default')
    return alt, np, pl, plt


@app.cell
def _(pl):
    data = pl.read_json('scripts/benchmark_results_csv.json')
    return (data,)


@app.cell
def _(data):
    data.head()
    return


@app.cell
def _(data):
    data.columns
    return


@app.cell
def _(data, pl):
    rank=data.filter(pl.col('dataset_size')   == '1024MB').sort(['dataset_size','time_s']).group_by('dataset_size')

    rank.head(100)
    return


@app.cell
def _(data, pl):
    df=data.filter(pl.col('dataset_size')   == '1024MB').group_by('library').agg(
        pl.col('time_s').mean().alias('mean_time')
    ).sort('mean_time')

    df_plot=df.to_pandas()
    return (df_plot,)


@app.cell
def _(df_plot, plt):
    plt.figure(figsize=(10,5))

    plt.bar(df_plot['library'], df_plot['mean_time'])

    plt.xlabel('library')
    plt.ylabel('Tempo Médio (s)')
    plt.title('Performance por lib - dataset 1024 MB')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    return


@app.cell
def _(data, pl):
    ram=(data.filter(pl.col("dataset_size") == "1024MB").group_by('library') \
    .agg(pl.col('mem_mb').max().alias('max_ram')) \
    .sort('max_ram')
    )
    df_ram=ram.to_pandas()
    return (df_ram,)


@app.cell
def _(df_ram, plt):
    plt.figure(figsize=(10,5))

    plt.bar(df_ram['library'], df_ram['max_ram'])

    plt.xlabel('library')
    plt.ylabel('Maior Consumo (MB)')
    plt.title('Consumo de RAM por lib - dataset 1024 MB')
    plt.tight_layout()
    plt.show()
    return


@app.cell
def _(df_ram):
    df_ram.head()
    return


@app.cell
def _(data, pl):
    fg = data.filter(pl.col("dataset_size") == "1024MB").group_by('library')
    fg.head()
    return


@app.cell
def _(data, np, pl):

    ram_ic = (
        data
        .filter(pl.col("dataset_size") == "1024MB")
        .group_by("library")
        .agg([
            pl.col("mem_mb").mean().alias("mean_mem"),
            pl.col("mem_mb").std().alias("std_mem"),
            pl.len().alias("n")
        ])
        .with_columns([
            (
                1.96 * pl.col("std_mem") / np.sqrt(pl.col("n"))
            ).alias("ci95")
        ])
        .with_columns([
            (pl.col("mean_mem") - pl.col("ci95")).alias("lower"),
            (pl.col("mean_mem") + pl.col("ci95")).alias("upper")
        ])
    )

    data_ram = ram_ic.to_pandas()
    return (data_ram,)


@app.cell
def _(alt, data_ram):

    bars = alt.Chart(data_ram).mark_bar().encode(
        x=alt.X("library:N", title="Library"),
        y=alt.Y("mean_mem:Q", title="Consumo Médio (MB)")
    )

    error_bars = alt.Chart(data_ram).mark_errorbar().encode(
        x="library:N",
        y="lower:Q",
        y2="upper:Q"
    )

    chart = (bars + error_bars).properties(
        width=700,
        height=400,
        title="Consumo de RAM"
    )

    chart
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
