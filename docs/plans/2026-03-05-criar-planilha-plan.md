# criar_planilha.py (passo_2) — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Gerar `passo_2/planilha_empresas.xlsx` consolidando todos os TXT de scraping com os CSVs de entrada.

**Architecture:** Script linear `passo_2/criar_planilha.py` com funções por responsabilidade. Lê CSVs de entrada para montar mapeamentos em memória, parseia TXTs por empresa/evento com regex, e escreve o Excel com openpyxl.

**Tech Stack:** Python 3, `openpyxl`, `re`, `os`, `csv` (sem pandas).

---

## Paths de referência

```
scrapingSenior/
├── dados/
│   ├── entrada/
│   │   ├── esocial.csv       ; id_evento;nome_esocial;irf;tabela;demissão
│   │   ├── eventos.csv       ; id_evento;nome_evento
│   │   └── empresas.csv      ; nome_empresa;id_empresa
│   └── saida/
│       └── {EMPRESA}/        ; pasta por empresa
│           └── {EVENTO}.TXT  ; arquivo por evento
├── passo_2/
│   ├── criar_planilha.py     ; ← CRIAR
│   └── planilha_empresas.xlsx; ← GERADO
└── docs/plans/
    └── 2026-03-05-criar-planilha-design.md
```

BASE_DIR é o diretório pai de `passo_2/` (raiz do projeto).

---

## Task 1: Criar estrutura da pasta passo_2 e esqueleto do script

**Files:**
- Create: `passo_2/criar_planilha.py`

**Step 1: Criar pasta e esqueleto**

```python
# passo_2/criar_planilha.py
import os
import csv
import re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRADA_DIR = os.path.join(BASE_DIR, "dados", "entrada")
SAIDA_DIR   = os.path.join(BASE_DIR, "dados", "saida")
OUTPUT_PATH = os.path.join(BASE_DIR, "passo_2", "planilha_empresas.xlsx")


def ler_esocial():
    pass

def ler_eventos():
    pass

def ler_empresas():
    pass

def parsear_txt(path):
    pass

def gerar_excel(esocial_rows, eventos, empresas, pastas_existentes):
    pass

if __name__ == "__main__":
    esocial_rows       = ler_esocial()
    eventos            = ler_eventos()
    empresas           = ler_empresas()
    pastas_existentes  = sorted(os.listdir(SAIDA_DIR))
    gerar_excel(esocial_rows, eventos, empresas, pastas_existentes)
    print("Planilha gerada:", OUTPUT_PATH)
```

**Step 2: Verificar que o script roda sem erros (com funções vazias)**

```bash
cd passo_2 && python criar_planilha.py
```
Esperado: `Planilha gerada: ...` (sem exceções)

**Step 3: Commit**

```bash
git add passo_2/criar_planilha.py
git commit -m "feat: add passo_2/criar_planilha.py skeleton"
```

---

## Task 2: Implementar `ler_esocial()`

**Files:**
- Modify: `passo_2/criar_planilha.py`

**Sobre o arquivo:** `dados/entrada/esocial.csv` — separador `;`, encoding UTF-8.
Colunas: `id_evento;nome_esocial;irf;tabela;demissão`
Pode ter múltiplas rows com o mesmo `id_evento` (tabelas diferentes OU nomes diferentes com mesma tabela).

**Step 1: Implementar**

```python
def ler_esocial():
    """Retorna lista de dicts na ordem do CSV."""
    path = os.path.join(ENTRADA_DIR, "esocial.csv")
    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if not row.get("id_evento", "").strip():
                continue
            rows.append({
                "id_evento":   int(row["id_evento"].strip()),
                "nome_esocial": row["nome_esocial"].strip(),
                "irf":         row["irf"].strip(),
                "tabela":      row["tabela"].strip(),
                "demissao":    row["demissão"].strip(),
            })
    return rows
```

**Step 2: Testar manualmente**

Adicione temporariamente ao `if __name__ == "__main__"`:
```python
rows = ler_esocial()
for r in rows:
    print(r)
```
Execute: `python criar_planilha.py`
Esperado: 21 linhas impressas, cada uma com dict completo.

**Step 3: Remover print de teste, commit**

```bash
git add passo_2/criar_planilha.py
git commit -m "feat: implement ler_esocial()"
```

---

## Task 3: Implementar `ler_eventos()`

**Files:**
- Modify: `passo_2/criar_planilha.py`

**Sobre o arquivo:** `dados/entrada/eventos.csv` — separador `;`.
Colunas: `id_evento;nome_evento`
`nome_evento` é o nome exato do arquivo TXT (sem `.TXT`).

**Step 1: Implementar**

```python
def ler_eventos():
    """Retorna dict {id_evento (int): nome_evento (str)}."""
    path = os.path.join(ENTRADA_DIR, "eventos.csv")
    eventos = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if not row.get("id_evento", "").strip():
                continue
            eventos[int(row["id_evento"].strip())] = row["nome_evento"].strip()
    return eventos
```

**Step 2: Testar manualmente**

```python
print(ler_eventos())
```
Esperado: dict com ~16 entradas, ex: `{216: 'MÉDIAS VARIAVEIS 13 INTEGRADO', 100: 'AVISO PRÉVIO INDENIZADO', ...}`

**Step 3: Remover print, commit**

```bash
git add passo_2/criar_planilha.py
git commit -m "feat: implement ler_eventos()"
```

---

## Task 4: Implementar `ler_empresas()`

**Files:**
- Modify: `passo_2/criar_planilha.py`

**Sobre o arquivo:** `dados/entrada/empresas.csv` — separador `;`.
Colunas: `nome_empresa;id_empresa`
Será atualizado pelo usuário posteriormente — pode estar incompleto.

**Step 1: Implementar**

```python
def ler_empresas():
    """Retorna dict {nome_empresa (str): id_empresa (str)}."""
    path = os.path.join(ENTRADA_DIR, "empresas.csv")
    empresas = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            nome = row.get("nome_empresa", "").strip()
            id_  = row.get("id_empresa", "").strip()
            if nome and id_:
                empresas[nome] = id_
    return empresas
```

**Step 2: Testar manualmente**

```python
print(len(ler_empresas()), "empresas")
```
Esperado: número de empresas no CSV atual.

**Step 3: Remover print, commit**

```bash
git add passo_2/criar_planilha.py
git commit -m "feat: implement ler_empresas()"
```

---

## Task 5: Implementar `parsear_txt(path)`

**Files:**
- Modify: `passo_2/criar_planilha.py`

**Sobre os TXT:**
- Encoding: tenta CP1252, fallback latin-1
- Paginação: uma ou mais páginas por arquivo
- Separador de página: linha contendo `FPRF004.OPE`
- Cada página tem cabeçalho (empresa, título, período, coluna-header) antes dos dados
- Linhas de colaborador têm pelo menos 5 espaços no início
- Deduplicação: por nome de colaborador, mantém apenas a primeira ocorrência

**Padrões de linha a IGNORAR:**
```
^\d+\s+-\s+         → cabeçalho da empresa  ex: "2245 - 153 TECNOLOGIA LTDA"
^\s+\d{4}\s+-       → código do evento      ex: " 0100 -Aviso Prévio"
Total de Colaboradores  → linha de total
FPRF004             → rodapé
Período:            → período
Tipo:               → tipo
Evento\s+Colaborador → header de colunas
^\s*$               → linha vazia
```

**Regex de colaborador:**
```python
COLLAB_RE = re.compile(
    r'^\s{5,}'                          # mínimo 5 espaços no início
    r'([A-ZÁÉÍÓÚÃÕÂÊÔÀÇÜ][A-ZÁÉÍÓÚÃÕÂÊÔÀÇÜa-záéíóúãõâêôàçü\s\.\-]+?)'  # NOME
    r'\s{2,}(\d{3})\s+'                 # SIT (3 dígitos)
    r'(\d{2}/\d{4})'                    # COMPETENCIA MM/YYYY
)
```

**Step 1: Implementar**

```python
COLLAB_RE = re.compile(
    r'^\s{5,}'
    r'([A-ZÁÉÍÓÚÃÕÂÊÔÀÇÜ][A-ZÁÉÍÓÚÃÕÂÊÔÀÇÜa-záéíóúãõâêôàçü\s\.\-]+?)'
    r'\s{2,}(\d{3})\s+'
    r'(\d{2}/\d{4})'
)

IGNORE_PATTERNS = [
    re.compile(r'^\s*\d+\s+-\s+'),        # cabeçalho empresa
    re.compile(r'^\s+\d{4}\s+-'),         # código evento
    re.compile(r'Total de Colaboradores'),
    re.compile(r'FPRF004'),
    re.compile(r'Per[íi]odo:'),
    re.compile(r'Tipo:'),
    re.compile(r'Evento\s+Colaborador'),
    re.compile(r'^\s*$'),                  # linha vazia
    re.compile(r'P[áa]g\.'),              # página
]


def _ler_txt(path):
    """Lê arquivo TXT tentando CP1252 depois latin-1."""
    for enc in ("cp1252", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
    return []


def parsear_txt(path):
    """
    Retorna lista de dicts {colaborador, competencia}, deduplicados por colaborador.
    Mantém apenas a primeira ocorrência de cada colaborador.
    """
    if not os.path.exists(path):
        return []

    linhas = _ler_txt(path)
    vistos = {}  # colaborador → competencia (primeira ocorrência)

    for linha in linhas:
        if any(p.search(linha) for p in IGNORE_PATTERNS):
            continue
        m = COLLAB_RE.match(linha)
        if m:
            nome = " ".join(m.group(1).split())  # normaliza espaços internos
            competencia = m.group(3)
            if nome not in vistos:
                vistos[nome] = competencia

    return [{"colaborador": k, "competencia": v} for k, v in vistos.items()]
```

**Step 2: Testar manualmente com um arquivo real**

```python
resultado = parsear_txt(os.path.join(SAIDA_DIR, "153 TECNOLOGIA LTDA", "AVISO PRÉVIO INDENIZADO.TXT"))
for r in resultado:
    print(r)
```
Esperado: 2 colaboradores — GIOVANA MATUSITA SOARES DE REZENDE (09/2025) e THIAGO DA SILVA LOUREIRO (08/2025).

**Step 3: Testar com arquivo de múltiplas páginas**

```python
resultado = parsear_txt(os.path.join(SAIDA_DIR, "153 TECNOLOGIA LTDA", "1-3 FÉRIAS (FÉRIAS).TXT"))
print(len(resultado), "colaboradores únicos")
```
Esperado: ~20 colaboradores únicos (o arquivo tem duplicatas e 2 páginas).

**Step 4: Remover prints, commit**

```bash
git add passo_2/criar_planilha.py
git commit -m "feat: implement parsear_txt() with dedup and pagination"
```

---

## Task 6: Implementar `gerar_excel()`

**Files:**
- Modify: `passo_2/criar_planilha.py`

**Lógica de construção das linhas:**

```
universo_empresas = union(pastas_em_saida, nomes_em_empresas_csv)
com_pasta  = sorted([e for e in universo_empresas if e in pastas_existentes])
sem_pasta  = sorted([e for e in universo_empresas if e not in pastas_existentes])

Para cada empresa em com_pasta + sem_pasta:
    id_senior = empresas.get(empresa, "")
    tem_pasta = empresa in pastas_existentes

    Para cada esocial_row em esocial_rows:
        nome_evento = eventos.get(esocial_row["id_evento"])
        if nome_evento and tem_pasta:
            txt_path = saida/{empresa}/{nome_evento}.TXT
            colaboradores = parsear_txt(txt_path)
        else:
            colaboradores = []

        if colaboradores:
            Para cada colab em colaboradores:
                → linha: [id_senior, empresa, nome_esocial, irf, colab["colaborador"], colab["competencia"]]
        else:
            → linha: [id_senior, empresa, nome_esocial, irf, "", ""]

        Se sem_pasta: aplica fonte vermelha em toda a linha
```

**Formatação:**
- Header: negrito + fundo cinza (`D9D9D9`)
- Sem pasta: `Font(color="FF0000")` em cada célula da linha

**Step 1: Implementar**

```python
def gerar_excel(esocial_rows, eventos, empresas, pastas_existentes):
    wb = Workbook()
    ws = wb.active
    ws.title = "Planilha"

    # Cabeçalho
    cabecalho = ["ID SENIOR", "EMPRESA", "EVENTO", "IRRF", "COLABORADOR", "COMPETENCIA"]
    header_font = Font(bold=True)
    header_fill = PatternFill(fill_type="solid", fgColor="D9D9D9")
    for col, titulo in enumerate(cabecalho, 1):
        cell = ws.cell(row=1, column=col, value=titulo)
        cell.font = header_font
        cell.fill = header_fill

    pastas_set = set(pastas_existentes)
    # Universo de empresas: union pastas + empresas.csv
    todas = sorted(pastas_set | set(empresas.keys()))
    com_pasta = [e for e in todas if e in pastas_set]
    sem_pasta = [e for e in todas if e not in pastas_set]

    fonte_vermelha = Font(color="FF0000")
    linha_atual = 2

    for empresa in com_pasta + sem_pasta:
        tem_pasta = empresa in pastas_set
        id_senior = empresas.get(empresa, "")

        for esocial_row in esocial_rows:
            id_evento   = esocial_row["id_evento"]
            nome_esocial = esocial_row["nome_esocial"]
            irf          = esocial_row["irf"]
            nome_evento  = eventos.get(id_evento)

            if nome_evento and tem_pasta:
                txt_path = os.path.join(SAIDA_DIR, empresa, nome_evento + ".TXT")
                colaboradores = parsear_txt(txt_path)
            else:
                colaboradores = []

            linhas_evento = colaboradores if colaboradores else [{"colaborador": "", "competencia": ""}]

            for colab in linhas_evento:
                valores = [
                    id_senior,
                    empresa,
                    nome_esocial,
                    irf,
                    colab["colaborador"],
                    colab["competencia"],
                ]
                for col, val in enumerate(valores, 1):
                    cell = ws.cell(row=linha_atual, column=col, value=val)
                    if not tem_pasta:
                        cell.font = fonte_vermelha
                linha_atual += 1

    # Ajuste de largura de colunas
    larguras = [12, 45, 45, 8, 50, 14]
    for col, largura in enumerate(larguras, 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = largura

    wb.save(OUTPUT_PATH)
```

**Step 2: Rodar o script completo**

```bash
python criar_planilha.py
```
Esperado: `Planilha gerada: .../passo_2/planilha_empresas.xlsx`

**Step 3: Verificar o Excel gerado**

Abrir `passo_2/planilha_empresas.xlsx` e validar:
- [ ] Cabeçalho em negrito com fundo cinza
- [ ] Empresas com pasta têm colaboradores preenchidos nos eventos que possuem TXT
- [ ] Eventos sem TXT têm COLABORADOR e COMPETENCIA em branco
- [ ] Empresas sem pasta estão em fonte vermelha com COLABORADOR vazio
- [ ] Não há colaboradores duplicados por empresa+evento

**Step 4: Commit**

```bash
git add passo_2/criar_planilha.py passo_2/planilha_empresas.xlsx
git commit -m "feat: implement gerar_excel() and complete criar_planilha.py"
```

---

## Task 7: Ajustes finais e validação

**Step 1: Validar caso de id_evento com múltiplas rows esocial (mesmo TXT)**

Verificar no Excel que eventos com o mesmo `id_evento` e mesma `tabela` (ex: id=12 `HORAS FÉRIAS DIURNAS` e id=12 `1/3 FÉRIAS`, ambos Holerite) têm **exatamente os mesmos colaboradores e competências**.

**Step 2: Validar deduplicação**

Para `153 TECNOLOGIA LTDA`, evento `1-3 FÉRIAS (FÉRIAS).TXT` (que tem colaboradores repetidos entre páginas), verificar que cada colaborador aparece apenas uma vez na planilha.

**Step 3: Commit final**

```bash
git add passo_2/
git commit -m "feat: complete passo_2 criar_planilha with validation"
```
