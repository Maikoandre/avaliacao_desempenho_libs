import os
import polars as pl
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# 1. Configurar diretório de destino
assets_dir = "/home/maiko/Projects/avaliacao_desempenho_libs/assets"
os.makedirs(assets_dir, exist_ok=True)

# 2. Carregar os dados
json_path = "/home/maiko/Projects/avaliacao_desempenho_libs/scripts/benchmark_results_csv.json"
data = pl.read_json(json_path)

# Configurar parâmetros de qualidade para publicação científica (SBC)
sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams.update({
    'font.family': 'sans-serif',
    'figure.dpi': 300,        # Alta qualidade para impressão/PDF
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'   # Corta margens brancas extras
})

# ==============================================================================
# GRÁFICO 1: Curva de Escalabilidade (Tempo de Execução por Operação)
# ==============================================================================
print("Gerando Gráfico 1: Curva de Escalabilidade...")
op_pures = ["filter", "aggr", "join", "sort"]
df_clean = (
    data.filter(
        (pl.col("status") == "SUCCESS") & 
        (pl.col("operation").is_in(op_pures))
    )
    .to_pandas()
)

op_map = {
    "filter": "Filtragem",
    "aggr": "Agregação",
    "join": "Junção",
    "sort": "Ordenação"
}
df_clean["operation_pt"] = df_clean["operation"].map(op_map)
df_clean["library"] = df_clean["library"].str.capitalize()

g = sns.relplot(
    data=df_clean,
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
    height=4.5,
    aspect=1.3
)

for ax in g.axes.flat:
    ax.set_yscale("log")
    ax.set_ylabel("Tempo de Execução (s) - Escala Log")
    ax.set_xlabel("Tamanho do Dataset")
    
g.set_titles("{col_name}")
g.fig.subplots_adjust(top=0.88)
g.fig.suptitle("Curva de Escalabilidade (Tempo de Execução) por Operação", fontsize=14, fontweight="bold")

# Salvar em PNG (alta resolução) e PDF (vetorial para LaTeX)
g.savefig(os.path.join(assets_dir, "escalabilidade_tempo.png"))
g.savefig(os.path.join(assets_dir, "escalabilidade_tempo.pdf"))
plt.close()

# ==============================================================================
# GRÁFICO 2: Pico de Memória RAM (Dataset 1024MB) com IC 95%
# ==============================================================================
print("Gerando Gráfico 2: Pico de RAM...")
df_ram_1gb = (
    data.filter(
        (pl.col("dataset_size") == "1024MB") &
        (pl.col("status") == "SUCCESS") &
        (pl.col("operation").is_in(op_pures))
    )
    .to_pandas()
)
df_ram_1gb["operation_pt"] = df_ram_1gb["operation"].map(op_map)
df_ram_1gb["library"] = df_ram_1gb["library"].str.capitalize()

plt.figure(figsize=(10, 6))
ax = sns.barplot(
    data=df_ram_1gb,
    x="operation_pt",
    y="mem_mb",
    hue="library",
    errorbar=("ci", 95),
    capsize=0.08,
    palette="viridis"
)

plt.title("Consumo de RAM Pico (MB) por Operação - Dataset 1024MB (IC 95%)", fontsize=13, fontweight="bold")
plt.xlabel("Operação Analítica", fontsize=11)
plt.ylabel("Consumo Máximo de RAM (MB)", fontsize=11)
plt.legend(title="Biblioteca")
plt.tight_layout()

plt.savefig(os.path.join(assets_dir, "consumo_ram_1gb.png"))
plt.savefig(os.path.join(assets_dir, "consumo_ram_1gb.pdf"))
plt.close()

# ==============================================================================
# GRÁFICO 3: Boxplot de Estabilidade/Dispersão (Tempo no Dataset 1024MB)
# ==============================================================================
print("Gerando Gráfico 3: Boxplot de Estabilidade...")
df_stability = (
    data.filter(
        (pl.col("dataset_size") == "1024MB") &
        (pl.col("status") == "SUCCESS") &
        (pl.col("operation").is_in(op_pures))
    )
    .to_pandas()
)
df_stability["library"] = df_stability["library"].str.capitalize()

plt.figure(figsize=(9, 6))
sns.boxplot(
    data=df_stability,
    x="library",
    y="time_s",
    palette="Set2"
)

plt.yscale("log")
plt.title("Distribuição do Tempo de Execução - Dataset 1024MB (Log)", fontsize=13, fontweight="bold")
plt.xlabel("Biblioteca", fontsize=11)
plt.ylabel("Tempo de Execução (s)", fontsize=11)
plt.tight_layout()

plt.savefig(os.path.join(assets_dir, "estabilidade_tempo.png"))
plt.savefig(os.path.join(assets_dir, "estabilidade_tempo.pdf"))
plt.close()

print(f"Sucesso! Todos os gráficos foram salvos na pasta {assets_dir} nos formatos PNG e PDF.")
