import marimo

__generated_with = "0.23.6"
app = marimo.App(width="medium")


@app.cell
def _():
    import polars as pl
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    import altair as alt

    return alt, np, pl, plt, sns


@app.cell
def _(pl):
    data = pl.read_json('/home/maiko/Projects/avaliacao_desempenho_libs/scripts/benchmark_results_csv.json')
    return (data,)


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
        .sort("mean_mem")
    )

    df_ram = ram_ic.to_pandas()
    return (df_ram,)


@app.cell
def _(df_ram, plt):
    plt.figure(figsize=(10,5))

    plt.bar(
        df_ram['library'],
        df_ram['mean_mem'],
        yerr=df_ram['ci95'],
        capsize=5
    )

    plt.xlabel('library')
    plt.ylabel('Consumo Médio (MB)')
    plt.title('Consumo de RAM por lib - dataset 1024 MB')

    plt.tight_layout()
    plt.show()
    return


@app.cell
def _(alt, data, pl):
    chart = alt.Chart(
        data.filter(pl.col("dataset_size") == "1024MB").to_pandas()
    ).mark_bar().encode(
        x="library:N",
        y="mean(mem_mb):Q"
    )

    error = alt.Chart(
        data.filter(pl.col("dataset_size") == "1024MB").to_pandas()
    ).mark_errorbar(extent="ci").encode(
        x="library:N",
        y="mem_mb:Q"
    )

    (chart + error)
    return


@app.cell
def _(data, sns):
    sns.boxplot(
        data=data,
        x='library',
        y='mem_mb'
    )
    return


@app.cell
def _(data, pl, plt, sns):

    plt.figure(figsize=(12,5))

    sns.boxplot(
        data=data.filter(pl.col("dataset_size") == "1024MB").to_pandas(),
        x='library',
        y='mem_mb'
    )

    plt.title('Distribuição de RAM')
    plt.show()
    return


@app.cell
def _(df_ram, plt):
    plt.figure(figsize=(10,5))

    plt.bar(
        df_ram['library'],
        df_ram['mean_mem'],
        yerr=df_ram['ci95'],
        capsize=5
    )

    '''
    plt.ylim(
        df_ram['mean_mem'].min() - 5,
        df_ram['mean_mem'].max() + 5
    )
    '''


    plt.xlabel('library')
    plt.ylabel('RAM média (MB)')
    plt.title('Consumo de RAM com IC95%')

    plt.tight_layout()
    plt.show()
    return


@app.cell
def _(df_ram, plt):
    plt.figure(figsize=(10,5))

    plt.errorbar(
        df_ram['library'],
        df_ram['mean_mem'],
        yerr=df_ram['ci95'],
        fmt='o',
        capsize=5
    )

    plt.ylabel('RAM média (MB)')
    plt.title('IC95% do pico de RAM')

    plt.grid(True, axis='y', alpha=0.3)

    plt.show()
    return


@app.cell
def _(df_ram):
    df_ram['relative'] = (
        df_ram['mean_mem'] /
        df_ram['mean_mem'].min()
    )
    return


@app.cell
def _(df_ram, plt):
    plt.figure(figsize=(10,5))

    plt.bar(
        df_ram['library'],
        df_ram['mean_mem'],
        yerr=df_ram['ci95'],
        capsize=5
    )

    plt.yscale('log')

    plt.xlabel('library')
    plt.ylabel('RAM média (MB) - escala log')
    plt.title('Consumo de RAM com IC de 95%')

    plt.tight_layout()
    plt.show()
    return


@app.cell
def _(data, pl, sns, plt):
    # 1. Filtrar dados de sucesso e operações analíticas (sem ser a carga inicial)
    _op_pures = ["filter", "aggr", "join", "sort"]
    _df_clean = (
        data.filter(
            (pl.col("status") == "SUCCESS") & 
            (pl.col("operation").is_in(_op_pures))
        )
        .to_pandas()
    )
    
    # Mapear para nomes mais legíveis em português para o artigo
    _op_map = {
        "filter": "Filtragem",
        "aggr": "Agregação",
        "join": "Junção",
        "sort": "Ordenação"
    }
    _df_clean["operation_pt"] = _df_clean["operation"].map(_op_map)
    _df_clean["library"] = _df_clean["library"].str.capitalize()
    
    # Configurar estilo
    sns.set_theme(style="whitegrid")
    
    # Criar grade de subplots por operação analítica
    _g = sns.relplot(
        data=_df_clean,
        x="dataset_size",
        y="time_s",
        hue="library",
        style="library",
        col="operation_pt",
        kind="line",
        markers=True,
        dashes=False,
        errorbar=("ci", 95),
        linewidth=2.5,
        markersize=8,
        col_wrap=2,
        height=4,
        aspect=1.3
    )
    
    # Ajustar cada subplot para usar escala logarítmica devido à disparidade de tempos
    for _ax in _g.axes.flat:
        _ax.set_yscale("log")
        _ax.set_ylabel("Tempo de Execução (s) - Escala Log")
        _ax.set_xlabel("Tamanho do Dataset")
        
    _g.set_titles("{col_name}")
    _g.fig.subplots_adjust(top=0.88)
    _g.fig.suptitle("Curva de Escalabilidade (Tempo de Execução) por Operação", fontsize=14, fontweight="bold")
    
    plt.show()
    return


@app.cell
def _(data, pl, sns, plt):
    # Filtrar para exibir a distribuição de pico de RAM no cenário mais desafiador (1024MB)
    _op_pures = ["filter", "aggr", "join", "sort"]
    _df_ram_1gb = (
        data.filter(
            (pl.col("dataset_size") == "1024MB") &
            (pl.col("status") == "SUCCESS") &
            (pl.col("operation").is_in(_op_pures))
        )
        .to_pandas()
    )
    
    _op_map = {
        "filter": "Filtragem",
        "aggr": "Agregação",
        "join": "Junção",
        "sort": "Ordenação"
    }
    _df_ram_1gb["operation_pt"] = _df_ram_1gb["operation"].map(_op_map)
    _df_ram_1gb["library"] = _df_ram_1gb["library"].str.capitalize()
    
    plt.figure(figsize=(12, 6))
    sns.set_theme(style="whitegrid")
    
    # Gráfico de barras agrupadas
    _ax = sns.barplot(
        data=_df_ram_1gb,
        x="operation_pt",
        y="mem_mb",
        hue="library",
        errorbar=("ci", 95),
        capsize=0.08,
        palette="viridis"
    )
    
    plt.title("Consumo de RAM Pico (MB) por Operação - Dataset 1024MB (com IC 95%)", fontsize=13, fontweight="bold")
    plt.xlabel("Operação Analítica", fontsize=11)
    plt.ylabel("Consumo Máximo de RAM (MB)", fontsize=11)
    plt.legend(title="Biblioteca")
    plt.tight_layout()
    plt.show()
    return


@app.cell
def _(data, pl, sns, plt):
    # Filtrar dados para boxplot de estabilidade nas operações do maior dataset
    _op_pures = ["filter", "aggr", "join", "sort"]
    _df_stability = (
        data.filter(
            (pl.col("dataset_size") == "1024MB") &
            (pl.col("status") == "SUCCESS") &
            (pl.col("operation").is_in(_op_pures))
        )
        .to_pandas()
    )
    
    _df_stability["library"] = _df_stability["library"].str.capitalize()
    
    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")
    
    # Boxplot de estabilidade de tempo
    sns.boxplot(
        data=_df_stability,
        x="library",
        y="time_s",
        palette="Set2"
    )
    
    plt.yscale("log") # Escala logarítmica para lidar com discrepâncias (ex: Pandas/Spark vs Polars/DuckDB)
    plt.title("Distribuição do Tempo de Execução (Estabilidade) - Dataset 1024MB (Log)", fontsize=13, fontweight="bold")
    plt.xlabel("Biblioteca", fontsize=11)
    plt.ylabel("Tempo de Execução (s)", fontsize=11)
    
    plt.tight_layout()
    plt.show()
    return


if __name__ == "__main__":
    app.run()
