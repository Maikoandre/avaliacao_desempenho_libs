import marimo

__generated_with = "0.23.3"
app = marimo.App(width="medium")


@app.cell
def _():
    import polars as pl
    import matplotlib.pyplot as plt

    return pl, plt


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
        pl.col('time_s').min().alias('best_time')
    ).sort('best_time')

    df_plot=df.to_pandas()
    return (df_plot,)


@app.cell
def _(df_plot, plt):
    plt.figure(figsize=(10,5))

    plt.bar(df_plot['library'], df_plot['best_time'])

    plt.xlabel('library')
    plt.ylabel('Menor Tempo (s)')
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


if __name__ == "__main__":
    app.run()
