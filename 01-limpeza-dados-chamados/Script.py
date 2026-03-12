# Importacao de bibliotecas 
import pandas as pd
import os

# O script para encontrar arquivo csv.
local_csv = os.path.dirname(os.path.abspath(__file__))
caminho_csv = os.path.join(local_csv, 'Chamados.csv')

# Criacao DataFrame.
df = pd.read_csv(caminho_csv, encoding='latin-1', sep=',')

# Forcando os nomes das colunas para evitar erros de digitacao ocultos.
df.columns = ['ID', 'Data', 'Categoria', 'Cliente', 'Prioridade']

# Remocao de simbolos.
df['Categoria'] = df['Categoria'].astype(str).str.replace(r'[^\w\s]', '', regex=True)

# Strings para maiusculas e remocao de espacos.
df['Categoria'] = df['Categoria'].str.upper().str.strip()
df['Prioridade'] = df['Prioridade'].str.upper().str.strip()

# Conversao e limpeza de valores coluna Data.
df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)
df['Data'] = df['Data'].fillna('SEM DATA')

# Removendo IDs repetidos.
df = df.drop_duplicates(subset=['ID'], keep='first')

# Criacao tabela limpa em .xlsx na mesma pasta do script.
caminho_saida = os.path.join(local_csv, 'Chamados_limpos.xlsx')
df.to_excel(caminho_saida, index=False)

print("Planilha limpa com sucesso!")