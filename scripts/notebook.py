import marimo

__generated_with = "0.23.3"
app = marimo.App(width="medium")


@app.cell
def _():
    import polars as pl

    return (pl,)


@app.cell
def _(pl):
    data = pl.read_json('benchmark_results_csv.json')
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


if __name__ == "__main__":
    app.run()
