import pandas as pd
import sqlite3
import os

# --- CONFIGURAÇÕES ---
ARQUIVO_CSV = 'cnaes_para_importar.csv'  # Alterado para o nome do arquivo CSV
NOME_BANCO_DADOS = 'vigilancia.db'
NOME_TABELA = 'cnae'

# --- INÍCIO DO SCRIPT ---

if not os.path.exists(ARQUIVO_CSV):
    print(f"Erro: Arquivo '{ARQUIVO_CSV}' não encontrado!")
else:
    try:
        # Alterado para pd.read_csv para ler o novo formato
        print(f"Lendo dados do arquivo '{ARQUIVO_CSV}'...")
        df = pd.read_csv(ARQUIVO_CSV)
        
        # Limpeza de dados: preenche células vazias em 'perguntas' com texto vazio
        df['perguntas'] = df['perguntas'].fillna('')

        print("Leitura concluída com sucesso.")
        
        print(f"Conectando ao banco de dados '{NOME_BANCO_DADOS}'...")
        conn = sqlite3.connect(NOME_BANCO_DADOS)
        
        print(f"Populando a tabela '{NOME_TABELA}'...")
        # O resto do script funciona da mesma forma
        df.to_sql(NOME_TABELA, conn, if_exists='replace', index=False)

        print("-" * 50)
        print(f"SUCESSO! O banco de dados foi criado e a tabela '{NOME_TABELA}' foi populada com {len(df)} registros.")
        print("Colunas no banco de dados:", list(df.columns))
        print("-" * 50)

        conn.close()

    except Exception as e:
        print(f"\nOcorreu um erro durante o processo: {e}")