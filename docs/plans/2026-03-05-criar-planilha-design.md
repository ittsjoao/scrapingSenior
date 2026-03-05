# Design: criar_planilha.py (passo_2)

**Data:** 2026-03-05
**Objetivo:** Ler arquivos TXT de scraping + CSVs de entrada e gerar planilha Excel consolidada.

---

## Entradas

| Arquivo | Uso |
|---------|-----|
| `dados/saida/{empresa}/{evento}.TXT` | Colaboradores e competências por evento |
| `dados/entrada/esocial.csv` | Master list de eventos (nome_esocial, irf, tabela) |
| `dados/entrada/eventos.csv` | Mapeamento id_evento → nome_evento (= nome do TXT) |
| `dados/entrada/empresas.csv` | Mapeamento nome_empresa → id_empresa (ID SENIOR) |

## Saída

`passo_2/planilha_empresas.xlsx`

---

## Arquitetura: Script linear com funções por responsabilidade (Opção A)

Arquivo único `passo_2/criar_planilha.py` com funções:

- `ler_esocial()` → lista de rows `{id_evento, nome_esocial, irf, tabela, demissao}`
- `ler_eventos()` → dict `{id_evento: nome_evento}`
- `ler_empresas()` → dict `{nome_empresa: id_empresa}`
- `parsear_txt(path)` → lista de `{colaborador, competencia}` (deduplicados)
- `gerar_excel(dados)` → escreve `planilha_empresas.xlsx` com openpyxl

---

## Mapeamentos em memória

```
empresas.csv   → dict { nome_empresa → id_empresa }
eventos.csv    → dict { id_evento → nome_evento }
esocial.csv    → lista ordenada de rows (define ordem das linhas no Excel)
```

**TXT → colaboradores:**
- `esocial.id_evento` → `eventos[id_evento]` → `dados/saida/{empresa}/{nome_evento}.TXT`
- Múltiplas rows esocial com mesmo `id_evento + tabela` → mesmo TXT → mesmos colaboradores

**Pasta → ID SENIOR:**
- Match exato entre nome da pasta e `nome_empresa` em `empresas.csv`
- Sem match → ID SENIOR vazio (empresas.csv será atualizado pelo usuário)

**Universo de empresas:**
- Union de: pastas em `dados/saida` + todas as entradas em `empresas.csv`
- Empresas **sem pasta**: incluídas com fonte vermelha, sem colaboradores

---

## Parse dos TXT

**Encoding:** tenta `CP1252`, fallback `latin-1`.

**Paginação:** arquivo pode ter múltiplas páginas. Separador de página:
```
FPRF004.OPE  -  DD/MM/YYYY  -  HH:MM:SS   AUDISYSTEM...
```
Lê o arquivo inteiro; ignora linhas de rodapé e cabeçalho.

**Regex colaborador:**
```python
r'^\s{5,}([A-ZÁÉÍÓÚÃÕÂÊÔÀÇÜÑ][A-Za-záéíóúãõâêôàçüñ\s]+?)\s{2,}(\d{3})\s+(\d{2}/\d{4})\s+'
```
Captura: `(NOME, SIT, COMPETENCIA)`

**Linhas ignoradas:**
- Cabeçalho da empresa: `^\d+ - `
- Código do evento: `^\s+\d{4}\s+-`
- Total: `Total de Colaboradores:`
- Período/Tipo/header de colunas/rodapé/linhas vazias

**Deduplicação:** por TXT, mantém apenas a primeira ocorrência de cada colaborador.

---

## Estrutura do Excel

**Colunas:** ID SENIOR | EMPRESA | EVENTO | IRRF | COLABORADOR | COMPETENCIA

**Ordem das linhas:**
1. Empresas **com pasta** (alfabética) × todos os eventos do esocial (ordem do CSV)
   - Por evento: uma linha por colaborador único; se sem TXT/dados → linha com COLABORADOR e COMPETENCIA vazios
2. Empresas **sem pasta** (alfabética) × todos os eventos: sem colaborador, fonte vermelha

**Formatação:**
- Cabeçalho: negrito, fundo cinza
- Linhas de empresa sem pasta: fonte vermelha em todas as colunas

---

## Dependências

- `openpyxl` — escrita do Excel com formatação
- `re` — parse dos TXT
- `os`, `csv` — stdlib (sem pandas)
