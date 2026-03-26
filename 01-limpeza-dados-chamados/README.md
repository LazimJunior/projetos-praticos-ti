# Limpeza de chamados — Normalização Determinística de Chamados de TI com Pandas e Saída XLSX Auditável

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.x-green.svg)](https://pandas.pydata.org/)
[![openpyxl](https://img.shields.io/badge/openpyxl-XLSX-orange.svg)](https://openpyxl.readthedocs.io/)

> Script ETL para limpeza e normalização de datasets de chamados de TI exportados de sistemas legados: resolve encoding Latin-1, normaliza categorias e prioridades para uppercase canônico, coerce datas malformadas com fallback explícito, deduplica por ID e serializa o resultado em XLSX auditável — tudo em execução idempotente via path relativo ao script.

---

## Diferencial de Engenharia

### Resolução de Path Relativo ao Script (não ao CWD)

O padrão mais comum em scripts ETL iniciantes é `pd.read_csv('Chamados.csv')` — que funciona apenas se o processo for iniciado no diretório do arquivo. `Script.py` resolve esse problema corretamente:

```python
local_csv = os.path.dirname(os.path.abspath(__file__))
caminho_csv = os.path.join(local_csv, 'Chamados.csv')
```

`__file__` é o path do script em execução; `os.path.abspath` resolve links simbólicos e paths relativos; `os.path.dirname` extrai o diretório. O resultado é um path absoluto que funciona independentemente de onde o processo foi iniciado — comportamento correto para scripts invocados via cron, CI/CD ou outros contextos onde o CWD não é controlado.

### Normalização de Schema com Override Explícito de Colunas

```python
df.columns = ['ID', 'Data', 'Categoria', 'Cliente', 'Prioridade']
```

Essa linha força os nomes de coluna independentemente do header original do CSV. Em exports de sistemas legados, headers frequentemente contêm espaços, acentos, BOM characters (especialmente em Latin-1) ou inconsistências entre versões do sistema. O override garante que o restante do pipeline opere em nomes canônicos conhecidos — é uma forma de **schema enforcement** sem dependência de contrato com o sistema de origem.

---

## Stack Tecnológica

| Tecnologia | Versão | Justificativa Técnica |
|---|---|---|
| **Python** | 3.9+ | Linguagem padrão para ETL data pipelines; ecossistema pandas nativo |
| **Pandas** | 2.x | `read_csv` com `encoding='latin-1'` para arquivos exportados de sistemas Windows legados; `pd.to_datetime` com `errors='coerce'` para datas malformadas; `drop_duplicates` para deduplicação |
| **openpyxl** | 3.x | Backend implícito de `DataFrame.to_excel()` para serialização XLSX; o formato XLSX é auditável (abrível no Excel sem ferramentas adicionais) e preserva tipos de dados melhor que CSV |
| **os** (stdlib) | — | Resolução de path portável sem dependências externas |

---

## Arquitetura & Fluxo de Dados

```
Chamados.csv (Latin-1, separador vírgula)
        │
        ▼ pd.read_csv(encoding='latin-1', sep=',')
DataFrame bruto
        │
        ▼ df.columns = ['ID', 'Data', 'Categoria', 'Cliente', 'Prioridade']
Schema canônico aplicado
        │
        ├─▶ Categoria: str.replace(regex r'[^\w\s]', '') → .upper() → .strip()
        │     Remove símbolos especiais, normaliza para UPPERCASE
        │
        ├─▶ Prioridade: .upper() → .strip()
        │     Normaliza para UPPERCASE (ALTA/MÉDIA/BAIXA canônicos)
        │
        ├─▶ Data: pd.to_datetime(errors='coerce', dayfirst=True)
        │     Interpreta formato BR (DD/MM/YYYY); datas inválidas → NaT → 'SEM DATA'
        │
        └─▶ drop_duplicates(subset=['ID'], keep='first')
              Remove registros com ID duplicado, mantendo a primeira ocorrência
        │
        ▼ df.to_excel('Chamados_limpos.xlsx', index=False)
Chamados_limpos.xlsx (mesmo diretório do script)
```

**Transformações por coluna:**

| Coluna | Problema Tratado | Transformação |
|---|---|---|
| `Categoria` | Símbolos especiais, case inconsistente | Regex strip + UPPER + strip |
| `Prioridade` | Case inconsistente | UPPER + strip |
| `Data` | Formatos inválidos, ordem dia/mês ambígua | `coerce` → fallback `'SEM DATA'` |
| `ID` | Registros duplicados | `drop_duplicates(keep='first')` |

---

## Guia de Setup

```bash
# 1. Clone e configure ambiente
git clone https://github.com/<seu-usuario>/projetos-praticos-ti.git
cd projetos-praticos-ti/01-limpeza-dados-chamados

python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\Activate.ps1     # Windows

# 2. Instale dependências
pip install pandas openpyxl

# 3. Posicione o arquivo de entrada
# O arquivo Chamados.csv deve estar no mesmo diretório que Script.py

# 4. Execute
python Script.py
# Output: Chamados_limpos.xlsx no mesmo diretório
# Saída esperada no terminal: "Planilha limpa com sucesso!"
```

### Formato esperado do CSV de entrada

```
ID,Data,Categoria,Categoria,Cliente,Prioridade
1,01/03/2024,Suporte@TI,João Silva,ALTA
2,2024-03-02,Infraestrutura,Maria Santos,media
```

---

## Análise de Trade-offs

### Por que XLSX em vez de CSV para a saída?

O output em `.xlsx` via `openpyxl` tem custo de serialização maior que `.csv`, mas oferece vantagens operacionais concretas neste contexto: (1) a coluna `Data` é serializada como tipo `datetime` nativo do Excel — preservando a possibilidade de filtros e ordenações temporais sem re-parsing; (2) o arquivo é diretamente abrível pelo time de TI sem configuração de delimitadores ou encoding; (3) headers são preservados com formatação. Para pipelines downstream (ingestão em banco, processamento adicional em Python), `.parquet` ou `.csv` seriam superiores — mas o caso de uso aqui é entrega para consumidores humanos.

### Limitação de idempotência: `keep='first'` sem critério de ordenação

```python
df = df.drop_duplicates(subset=['ID'], keep='first')
```

`keep='first'` mantém a primeira ocorrência na ordem do arquivo CSV. Se o arquivo não estiver ordenado por data ou por algum critério de "mais recente", o resultado pode reter versões desatualizadas de registros. Em um pipeline de produção, o correto seria primeiro ordenar por data (`df.sort_values('Data', ascending=False)`) antes de deduplicar, garantindo que a versão mais recente de cada chamado seja mantida.

### Ausência de validação de schema pós-limpeza

O script não valida se as transformações produziram os valores esperados. Em dados reais, `Prioridade` poderia conter valores fora do conjunto `{ALTA, MÉDIA, BAIXA}` após normalização — typos como `URGENTE` ou `CRITICA` passariam silenciosamente para o XLSX. Uma asserção de validação pós-processamento (ex: `assert df['Prioridade'].isin({'ALTA', 'MEDIA', 'BAIXA', 'NORMAL'}).all()`) tornaria o pipeline verificável e auto-documentado.
