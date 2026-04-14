# Avaliação de Desempenho de Bibliotecas

Este projeto tem como objetivo realizar a avaliação e comparação de desempenho de diferentes bibliotecas de processamento e manipulação de dados em Python, como **Pandas**, **Polars**, **DuckDB** e **Spark**. Ele também utiliza ferramentas de profiling, como `memory-profiler`, `psutil` e `pytest-benchmark`.

## Pré-requisitos

Para rodar o projeto, é recomendado instalar o gerenciador de pacotes e ambientes `uv`. O `uv` é extremamente rápido e simplifica o processo de configuração de dependências e ambientes virtuais.

- Caso ainda não tenha o `uv` instalado, instale usando o seguinte comando (Linux/macOS):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Para Windows ou outros métodos de instalação, consulte a [documentação oficial do uv](https://docs.astral.sh/uv/getting-started/installation/).
- É necessário ter a versão **Python 3.11** ou superior instalada em seu sistema.

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

Com o ambiente ativado e as dependências devidamente instaladas, você tem duas rotas principais para analisar os códigos do projeto:

### 1. Via Marimo (Recomendado para análises interativas)
O projeto conta com o notebook `main.py` para análises exploratórias. Para abri-lo:
```bash
marimo edit
```
Isso irá iniciar o servidor Marimo e abrir a interface diretamente em seu navegador padrão. Basta abrir o arquivo `main.py` para visualizar e executar as células.
