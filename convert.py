import os
import pandas as pd
from dbfread import DBF
from pyreaddbc import dbc2dbf

# --- CONFIGURAÇÕES ---
dbc_file = 'data/DENGBR25.dbc'        # seu arquivo de entrada
dbf_file = 'data/DENGBR25.dbf'        # arquivo intermediário
parquet_file = 'data/DENGBR25.parquet'
csv_file = 'data/DENGBR25.csv'    # opcional
dbf_encoding = 'iso-8859-1'      # ajuste se necessário
gerar_csv = False                # coloque True se quiser gerar também o CSV

try:
    print(f"Convertendo '{dbc_file}' para '{dbf_file}'...")
    dbc2dbf(dbc_file, dbf_file)
    print("Conversão para .dbf concluída.")

    print(f"Lendo o arquivo '{dbf_file}'...")
    table = DBF(dbf_file, encoding=dbf_encoding)
    df = pd.DataFrame(iter(table))
    print(f"Leitura concluída: {len(df):,} registros e {len(df.columns)} colunas.")

    print(f"Salvando em formato Parquet...")
    df.to_parquet(parquet_file, index=False)
    print(f"Arquivo Parquet salvo em: {os.path.abspath(parquet_file)}")

    if gerar_csv:
        print(f"Salvando em formato CSV...")
        df.to_csv(csv_file, index=False)
        print(f"Arquivo CSV salvo em: {os.path.abspath(csv_file)}")

except Exception as e:
    print(f"Erro: {e}")
