import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

assets_dir = "/home/maiko/Projects/avaliacao_desempenho_libs/assets"
os.makedirs(assets_dir, exist_ok=True)

json_path = "/home/maiko/Projects/avaliacao_desempenho_libs/src/benchmark_results_csv.json"
data = pd.read_json(json_path)

sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams.update({
    'font.family': 'sans-serif',
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'
})

# GRÁFICO 1: Curva de Escalabilidade (Tempo de Execução por Operação)
print("Gerando Gráfico 1: Curva de Escalabilidade...")
op_pures = ["filter", "aggr", "join", "sort"]
df_clean = data[
    (data["status"] == "SUCCESS") & 
    (data["operation"].isin(op_pures))
].copy()

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

# GRÁFICO 2: Pico de Memória RAM (Datasets 256MB, 512MB e 1024MB) com IC 95%
print("Gerando Gráfico 2: Pico de RAM...")
datasets_to_plot = [
    ("256MB", "256mb"),
    ("512MB", "512mb"),
    ("1024MB", "1gb")
]

for size_label, file_suffix in datasets_to_plot:
    df_ram = data[
        (data["dataset_size"] == size_label) &
        (data["status"] == "SUCCESS") &
        (data["operation"].isin(op_pures))
    ].copy()
    df_ram["operation_pt"] = df_ram["operation"].map(op_map)
    df_ram["library"] = df_ram["library"].str.capitalize()

    plt.figure(figsize=(10, 6))
    ax = sns.barplot(
        data=df_ram,
        x="operation_pt",
        y="mem_mb",
        hue="library",
        errorbar=("ci", 95),
        capsize=0.08,
        palette="viridis"
    )

    plt.title(f"Consumo de RAM Pico (MB) por Operação - Dataset {size_label}", fontsize=13, fontweight="bold")
    plt.xlabel("Operação Analítica", fontsize=11)
    plt.ylabel("Consumo Máximo de RAM (MB)", fontsize=11)
    plt.legend(title="Biblioteca")
    plt.tight_layout()

    plt.savefig(os.path.join(assets_dir, f"consumo_ram_{file_suffix}.png"))
    plt.savefig(os.path.join(assets_dir, f"consumo_ram_{file_suffix}.pdf"))
    plt.close()

# GRÁFICO 3: Boxplot de Estabilidade/Dispersão (Tempo no Dataset 1024MB)
print("Gerando Gráfico 3: Boxplot de Estabilidade...")
df_stability = data[
    (data["dataset_size"] == "1024MB") &
    (data["status"] == "SUCCESS") &
    (data["operation"].isin(op_pures))
].copy()
df_stability["library"] = df_stability["library"].str.capitalize()

plt.figure(figsize=(9, 6))
sns.boxplot(
    data=df_stability,
    x="library",
    y="time_s",
    palette="Set2"
)

plt.yscale("log")
plt.title("Distribuição do Tempo de Execução - Dataset 1024MB", fontsize=13, fontweight="bold")
plt.xlabel("Biblioteca", fontsize=11)
plt.ylabel("Tempo de Execução (s)", fontsize=11)
plt.tight_layout()

plt.savefig(os.path.join(assets_dir, "estabilidade_tempo.png"))
plt.savefig(os.path.join(assets_dir, "estabilidade_tempo.pdf"))
plt.close()

print(f"Sucesso! Todos os gráficos foram salvos na pasta {assets_dir} nos formatos PNG e PDF.")
