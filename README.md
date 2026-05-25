# Avaliação de Desempenho de Bibliotecas

Este projeto tem como objetivo realizar a avaliação e comparação de desempenho de diferentes bibliotecas de processamento e manipulação de dados em Python, como **Pandas**, **Polars**, **DuckDB** e **Apache Spark**.

## Principais Resultados do Benchmark

O estudo avaliou o desempenho das quatro bibliotecas executando operações analíticas fundamentais (filtragem, agregação, junção e ordenação) em conjuntos de dados de 256MB, 512MB e 1GB em uma máquina local com hardware limitado (8GB de RAM). Os resultados medidos revelaram conclusões fundamentais sobre o perfil de cada biblioteca:

| Biblioteca | Tempo Médio (s) | Pico de RAM (1GB) | Escalabilidade | Melhor Caso de Uso |
| :--- | :--- | :--- | :--- | :--- |
| **DuckDB** | **Excelente** (Subsegundo / ms) | **Mínimo** (~620 MB) | Excepcional (Linear / *spill-to-disk*) | Análises analíticas embarcadas e computação limitada |
| **Polars** | **Excelente** (Subsegundo / ms) | Baixo (~1.500 MB) | Excepcional (Rust-powered multi-threaded) | Engenharia de dados local de alta velocidade |
| **Pandas** | Moderado (Baixo em Junções) | **Crítico** (~7.400 MB) | Crítico (Em memória, alto risco de OOM) | Análises exploratórias e volumes pequenos ($<256$MB) |
| **PySpark** | Muito Baixo (JVM local local) | Moderado (700-1.700 MB) | Moderado (JVM local / *cold start*) | Processamento distribuído em clusters reais (Big Data) |

### Destaques das Métricas:
* **Consumo Crítico de RAM do Pandas:** Para processar 1GB de dados, o Pandas consome cerca de **7,4 GB (93% da memória total disponível)**, colocando o fluxo à beira de falhas por falta de memória (OOM).
* **Supremacia do DuckDB:** O DuckDB consome **menos de 9% da RAM** demandada pelo Pandas, resultado de sua execução vetorizada e descarregamento dinâmico em disco (*spill-to-disk*).
* **Velocidade de Polars e DuckDB:** Em junções complexas com 1GB, Polars e DuckDB processam dados em **0,01s**, superando o Pandas em até **80 vezes**.
* **Overhead da JVM no PySpark:** O PySpark local levou até **20s** em ordenações, mostrando-se ineficiente para nó único devido ao custo de runtime Java e serialização.

Os gráficos em alta resolução detalhando estes resultados estão salvos na pasta `/assets`:
* [assets/escalabilidade_tempo.png](assets/escalabilidade_tempo.png) - Curva de Escalabilidade Temporal (Escala Log)
* [assets/consumo_ram_1gb.png](assets/consumo_ram_1gb.png) - Pico de Consumo de RAM por Operação
* [assets/estabilidade_tempo.png](assets/estabilidade_tempo.png) - Boxplot de Dispersão e Estabilidade

## Pré-requisitos

Para rodar o projeto, é recomendado instalar o gerenciador de pacotes e ambientes `uv`. O `uv` é extremamente rápido e simplifica o processo de configuração de dependências e ambientes virtuais.

- Caso ainda não tenha o `uv` instalado, instale usando o seguinte comando (Linux/macOS):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Para Windows ou outros métodos de instalação, consulte a [documentação oficial do uv](https://docs.astral.sh/uv/getting-started/installation/).
- É necessário ter a versão **Python 3.11** ou superior instalada em seu sistema.

### Instalando o Java 17 (Requisito para o PySpark)

Para rodar o **PySpark** localmente, é obrigatório ter o Java instalado (o **Java 17** é a versão mais recomendada para compatibilidade e performance).

- **No Linux (Ubuntu/Debian):**
  ```bash
  sudo apt update
  sudo apt install openjdk-17-jdk -y
  ```


- **No Windows:**
  Baixe o instalador do Java 17 através do site de distribuições como o [Adoptium (Eclipse Temurin)](https://adoptium.net/temurin/releases/?version=17) ou do [site oficial da Oracle](https://www.oracle.com/java/technologies/javase/jdk17-archive-downloads.html).
  

  (Lembre-se de configurar as variáveis de ambiente `JAVA_HOME` e adicionar o Java ao `PATH` do sistema, frequentemente isso já é feito automaticamente pelo instalador).

Após a instalação, verifique se ocorreu tudo bem executando `java -version` no seu terminal.


## Instalação e Configuração

Siga os passos abaixo para preparar o ambiente na sua máquina:

1. **Clone do repositório (caso ainda não tenha feito):**
   ```bash
   git clone https://github.com/Maikoandre/avaliacao_desempenho_libs
   cd avaliacao_desempenho_libs
   ```

2. **Sincronize as dependências com o `uv`:**
   O `uv` criará automaticamente o ambiente virtual local (`.venv`) e instalará as bibliotecas descritas no `pyproject.toml` baseando-se no `uv.lock`.
   ```bash
   uv sync
   ```

3. **Ative o ambiente virtual criado:**
   - No **Linux/macOS**:
     ```bash
     source .venv/bin/activate
     ```
   - No **Windows**:
     ```bash
     .venv\Scripts\activate
     ```

## Como Rodar o Projeto

Com o ambiente ativado e as dependências devidamente instaladas, você tem uma rota para analisar os códigos do projeto:

### 1. Via Marimo (Recomendado para análises interativas)
O projeto conta com o notebook `main.py` para análises exploratórias. Para abri-lo:
```bash
marimo edit
```
Isso irá iniciar o servidor Marimo e abrir a interface diretamente em seu navegador padrão. Basta abrir o arquivo `main.py` para visualizar e executar as células.

