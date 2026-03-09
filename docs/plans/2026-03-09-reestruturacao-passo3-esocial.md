# Reestruturação passo_3 — Busca de Rúbricas por CPF/CNPJ

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reestruturar o `passo_3` para buscar rúbricas de cada colaborador iterando meses (12/2025 → 11/2024), validar IRRF conforme `esocial.csv` e corrigir quando necessário, gerando logs e planilha de resultado.

**Architecture:** Quatro arquivos com responsabilidade única — `entradas.py` lê os CSVs, `saida.py` escreve logs e planilha, `cookie.py` ganha `extrair_nome_empresa`, `main.py` orquestra. `planilha.py` é removido.

**Tech Stack:** Python 3, requests, openpyxl, BeautifulSoup4 (lxml), csv (stdlib).

---

## Task 1: `passo_3/entradas.py` — Leitura dos CSVs de entrada

**Files:**
- Create: `passo_3/entradas.py`
- Delete: `passo_3/planilha.py`

### Step 1: Criar `entradas.py`

```python
# passo_3/entradas.py
import csv
import os

CAMINHO_CNPJ_CPF = os.path.join(os.path.dirname(__file__), "..", "dados", "entrada", "cnpj_cpf.csv")
CAMINHO_ESOCIAL  = os.path.join(os.path.dirname(__file__), "..", "dados", "entrada", "esocial.csv")


def carregar_empresas():
    """
    Lê cnpj_cpf.csv (colunas: cnpj;cpf) e retorna dict {cnpj: [cpf1, cpf2, ...]}.
    CPFs duplicados por CNPJ são ignorados.
    """
    empresas = {}
    with open(CAMINHO_CNPJ_CPF, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            cnpj = row["cnpj"].strip()
            cpf  = row["cpf"].strip()
            if cnpj not in empresas:
                empresas[cnpj] = []
            if cpf not in empresas[cnpj]:
                empresas[cnpj].append(cpf)
    return empresas


def carregar_eventos():
    """
    Lê esocial.csv e retorna (eventos_ativos, eventos_demissao).

    eventos_ativos:  lista de dicts para eventos onde demissão=Não
    eventos_demissao: lista de dicts para eventos onde demissão=Sim

    Cada dict: {"nome": str, "aux": str, "irrf": str, "tabela": str}
    """
    ativos   = []
    demissao = []
    with open(CAMINHO_ESOCIAL, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            evento = {
                "nome":   row["nome_esocial"].strip(),
                "aux":    row["nome_esocial_aux"].strip(),
                "irrf":   row["irrf"].strip(),
                "tabela": row["tabela"].strip(),
            }
            if row["demissão"].strip().lower() == "sim":
                demissao.append(evento)
            else:
                ativos.append(evento)
    return ativos, demissao
```

### Step 2: Remover `planilha.py`

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
git rm passo_3/planilha.py
```

### Step 3: Verificar sintaxe

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior/passo_3
python -c "import entradas; print('OK')"
```

Expected: `OK`

### Step 4: Commit

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
git add passo_3/entradas.py
git commit -m "feat(passo_3): add entradas.py, remove planilha.py"
```

---

## Task 2: `passo_3/saida.py` — Logs e planilha de resultado

**Files:**
- Create: `passo_3/saida.py`

### Step 1: Criar `saida.py`

```python
# passo_3/saida.py
import os
from datetime import datetime

import openpyxl

_TS    = datetime.now().strftime("%Y%m%d_%H%M%S")
_PASTA = os.path.dirname(__file__)

ARQUIVO_DESCOBERTAS = os.path.join(_PASTA, f"log_descobertas_{_TS}.txt")
ARQUIVO_AJUSTES     = os.path.join(_PASTA, f"log_ajustes_{_TS}.txt")
ARQUIVO_PLANILHA    = os.path.join(_PASTA, f"resultado_{_TS}.xlsx")


def log_descoberta(nome_empresa, codigo_rubrica, cpf, irrf_ok):
    """
    Grava linha no log de descobertas.
    Formato: NOME EMPRESA (CODIGO - CPF) - IRRF CORRETO/INCORRETO
    """
    status = "IRRF CORRETO" if irrf_ok else "IRRF INCORRETO"
    linha  = f"{nome_empresa} ({codigo_rubrica} - {cpf}) - {status}\n"
    with open(ARQUIVO_DESCOBERTAS, "a", encoding="utf-8") as f:
        f.write(linha)
    print(f"  [log] {linha.strip()}")


def log_na(nome_empresa, nome_evento, motivo):
    """
    Grava linha N/A no log de descobertas.
    Formato: NOME EMPRESA | EVENTO - N/A (motivo)
    """
    linha = f"{nome_empresa} | {nome_evento} - N/A ({motivo})\n"
    with open(ARQUIVO_DESCOBERTAS, "a", encoding="utf-8") as f:
        f.write(linha)
    print(f"  [log] {linha.strip()}")


def log_ajuste(nome_empresa, nome_evento, irrf_antigo, irrf_novo):
    """
    Grava linha no log de ajustes.
    Formato: NOME EMPRESA | EVENTO | IRRF antigo: X → novo: Y
    """
    linha = f"{nome_empresa} | {nome_evento} | IRRF antigo: {irrf_antigo} → novo: {irrf_novo}\n"
    with open(ARQUIVO_AJUSTES, "a", encoding="utf-8") as f:
        f.write(linha)
    print(f"  [ajuste] {linha.strip()}")


def salvar_planilha(resultados, eventos_ativos, eventos_demissao):
    """
    Salva planilha Excel com uma linha por empresa e uma coluna por evento.

    resultados: lista de dicts:
        {"nome_empresa": str, "cnpj": str, "status_eventos": {nome_evento: str}}

    Valores possíveis por célula de evento:
        "RETIFICADO"     → rúbrica encontrada (IRRF correto ou corrigido)
        "N/A"            → rúbrica não encontrada
        "N/A (Demissão)" → evento ignorado por ser demissão
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultado"

    nomes_eventos = [e["nome"] for e in eventos_ativos] + [e["nome"] for e in eventos_demissao]
    ws.append(["EMPRESA", "CNPJ"] + nomes_eventos)

    for r in resultados:
        linha = [r["nome_empresa"], r["cnpj"]]
        for nome in nomes_eventos:
            linha.append(r["status_eventos"].get(nome, "N/A"))
        ws.append(linha)

    wb.save(ARQUIVO_PLANILHA)
    print(f"\n[Planilha salva] {ARQUIVO_PLANILHA}")
```

### Step 2: Verificar sintaxe

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior/passo_3
python -c "import ast; ast.parse(open('saida.py', encoding='utf-8').read()); print('OK')"
```

Expected: `OK`

### Step 3: Commit

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
git add passo_3/saida.py
git commit -m "feat(passo_3): add saida.py — logs de descobertas, ajustes e planilha Excel"
```

---

## Task 3: Adicionar `extrair_nome_empresa` em `cookie.py`

**Files:**
- Modify: `passo_3/cookie.py`

O cookie `UsuarioLogado` retornado após `selecionar_empresa` contém `Nome=NOME DA EMPRESA&...`. Basta extrair com regex.

### Step 1: Inserir função antes de `acessar_home_empresa`

```python
def extrair_nome_empresa(session):
    """
    Extrai o nome da empresa do cookie UsuarioLogado.
    Retorna string com o nome ou "Empresa desconhecida" se não encontrar.
    """
    valor = session.cookies.get("UsuarioLogado", "")
    m = re.search(r"Nome=([^&]+)", valor)
    return m.group(1) if m else "Empresa desconhecida"
```

### Step 2: Verificar sintaxe

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior/passo_3
python -c "import ast; ast.parse(open('cookie.py', encoding='utf-8').read()); print('OK')"
```

Expected: `OK`

### Step 3: Commit

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
git add passo_3/cookie.py
git commit -m "feat(passo_3): add extrair_nome_empresa to cookie.py"
```

---

## Task 4: Reescrever `passo_3/main.py`

**Files:**
- Modify: `passo_3/main.py`

### Step 1: Substituir conteúdo de `main.py`

```python
# passo_3/main.py
import os
import subprocess
import tempfile

import requests

from cookie import (
    ler_cookies,
    selecionar_empresa,
    trocar_perfil,
    extrair_nome_empresa,
    acessar_home_empresa,
    acessar_tabela_funcionário,
    buscar_rubrica,
    abrir_edicao_rubrica,
    salvar_edicao,
    acessar_assinadoc,
    baixar_jnlp,
)
from parser import (
    extrair_guid_home,
    parsear_tabela_funcionario,
    parsear_busca_rubrica,
    parsear_form_edicao,
    extrair_link_jnlp,
)
from entradas import carregar_empresas, carregar_eventos
from saida import log_descoberta, log_na, log_ajuste, salvar_planilha

# ── Configuração ───────────────────────────────────────────────────────────────

COOKIES_FILE   = os.path.join(os.path.dirname(__file__), "cookies.txt")
PASTA_TEMP_JNLP = os.path.join(tempfile.gettempdir(), "esocial_jnlp")

# Meses de busca: 12/2025 → 11/2024 (ordem decrescente)
MESES = [
    "202512", "202511", "202510", "202509", "202508", "202507",
    "202506", "202505", "202504", "202503", "202502", "202501",
    "202412", "202411",
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def assinar_jnlp(session):
    """Acessa Assinadoc, baixa .jnlp e executa com javaws. Retorna True se sucesso."""
    html = acessar_assinadoc(session)
    if not html:
        print("  [!] Assinadoc não retornou HTML")
        return False

    url_jnlp = extrair_link_jnlp(html)
    if not url_jnlp:
        print("  [!] Link .jnlp não encontrado")
        return False

    caminho = baixar_jnlp(session, url_jnlp, PASTA_TEMP_JNLP)
    if not caminho:
        return False

    try:
        r = subprocess.run(["javaws", caminho], timeout=120, capture_output=True)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"  [!] javaws: {e}")
        return False


def buscar_codigos(session, cpfs, eventos_ativos):
    """
    Itera CPFs × meses até encontrar todos os eventos pendentes ou esgotar as opções.

    Retorna dict: {nome_evento: {"codigo": str, "cpf": str, "mes": str}}
    """
    pendentes  = {e["nome"]: e for e in eventos_ativos}
    encontrados = {}

    for cpf in cpfs:
        if not pendentes:
            break
        for mes in MESES:
            if not pendentes:
                break
            html = acessar_tabela_funcionário(session, cpf, mes)
            if not html:
                continue
            for nome, evento in list(pendentes.items()):
                codigo = parsear_tabela_funcionario(html, evento["nome"], evento["aux"], evento["tabela"])
                if codigo:
                    encontrados[nome] = {"codigo": codigo, "cpf": cpf, "mes": mes}
                    del pendentes[nome]

    return encontrados


def validar_e_corrigir(session, guid, nome_empresa, evento, info):
    """
    Abre a rúbrica encontrada, verifica o IRRF e corrige se necessário.
    Grava nos logs e retorna True se a rúbrica está/ficou correta.
    """
    codigo = info["codigo"]
    cpf    = info["cpf"]

    if len(codigo) < 28:
        print(f"  [!] Código {codigo} não é do domínio (< 28 chars)")
        return False

    html_busca = buscar_rubrica(session, guid, codigo)
    if not html_busca:
        return False

    id_rubrica, id_evento = parsear_busca_rubrica(html_busca)
    if not id_rubrica:
        return False

    html_edicao = abrir_edicao_rubrica(session, id_rubrica, id_evento, guid)
    if not html_edicao:
        return False

    campos = parsear_form_edicao(html_edicao)
    if not campos:
        return False

    irrf_atual    = str(campos.get("DadosRubrica.CodigoIncidenciaIR", ""))
    irrf_esperado = str(evento["irrf"])

    if irrf_atual == irrf_esperado:
        log_descoberta(nome_empresa, codigo, cpf, irrf_ok=True)
        return True

    # IRRF incorreto — corrige
    campos["DadosRubrica.CodigoIncidenciaIR"] = irrf_esperado
    status_code, _ = salvar_edicao(session, id_rubrica, id_evento, campos)

    ok = assinar_jnlp(session) if status_code == 302 else False

    log_descoberta(nome_empresa, codigo, cpf, irrf_ok=False)
    if ok:
        log_ajuste(nome_empresa, evento["nome"], irrf_atual, irrf_esperado)

    return ok


# ── Loop principal ─────────────────────────────────────────────────────────────

def main():
    session = requests.Session()
    cookies_base = ler_cookies(COOKIES_FILE)
    session.cookies.update(cookies_base)

    usuario_logado_procurador = cookies_base.get("UsuarioLogado", "")
    cpf_procurador            = cookies_base.get("usuario_logado_ws", "")

    empresas                   = carregar_empresas()
    eventos_ativos, eventos_demissao = carregar_eventos()

    resultados = []  # acumula para a planilha final

    for cnpj, cpfs in empresas.items():
        print(f"\n{'='*60}")
        print(f"[EMPRESA] {cnpj}")

        ok = selecionar_empresa(session, cnpj)
        if not ok:
            print(f"  [!] Falha ao selecionar {cnpj}")
            trocar_perfil(session, usuario_logado_procurador, cpf_procurador)
            continue

        nome_empresa = extrair_nome_empresa(session)
        print(f"  [Nome] {nome_empresa}")

        html_home = acessar_home_empresa(session)
        guid = extrair_guid_home(html_home) if html_home else None
        if not guid:
            print(f"  [!] GUID não encontrado para {cnpj}")
            trocar_perfil(session, usuario_logado_procurador, cpf_procurador)
            continue

        print(f"  [GUID] {guid}")

        # ── Busca: CPF × mês até encontrar todos os eventos ──────────────
        encontrados = buscar_codigos(session, cpfs, eventos_ativos)

        # ── Validação e correção ──────────────────────────────────────────
        status_eventos = {}

        for evento in eventos_ativos:
            nome = evento["nome"]
            if nome not in encontrados:
                log_na(nome_empresa, nome, "não encontrado")
                status_eventos[nome] = "N/A"
                continue
            ok = validar_e_corrigir(session, guid, nome_empresa, evento, encontrados[nome])
            status_eventos[nome] = "RETIFICADO" if ok else "N/A"

        for evento in eventos_demissao:
            log_na(nome_empresa, evento["nome"], "Demissão")
            status_eventos[evento["nome"]] = "N/A (Demissão)"

        resultados.append({
            "nome_empresa":   nome_empresa,
            "cnpj":           cnpj,
            "status_eventos": status_eventos,
        })

        trocar_perfil(session, usuario_logado_procurador, cpf_procurador)

    salvar_planilha(resultados, eventos_ativos, eventos_demissao)


if __name__ == "__main__":
    main()
```

### Step 2: Verificar sintaxe

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior/passo_3
python -c "import ast; ast.parse(open('main.py', encoding='utf-8').read()); print('OK')"
```

Expected: `OK`

### Step 3: Commit

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
git add passo_3/main.py
git commit -m "feat(passo_3): rewrite main.py — CPF/mês loop, IRRF validation, logs and spreadsheet"
```

---

## Task 5: Criar arquivo de teste e smoke test

**Files:**
- Create: `dados/entrada/cnpj_cpf.csv`

### Step 1: Criar `cnpj_cpf.csv` com 1 empresa e 1 colaborador

```csv
cnpj;cpf
35.237.328/0001-00;61749621800
```

### Step 2: Verificar que todos os arquivos necessários existem

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior/passo_3
python -c "
from entradas import carregar_empresas, carregar_eventos
e = carregar_empresas()
a, d = carregar_eventos()
print(f'Empresas: {len(e)} | Eventos ativos: {len(a)} | Demissão: {len(d)}')
"
```

Expected: `Empresas: 1 | Eventos ativos: 18 | Demissão: 3` (ou similar conforme esocial.csv)

### Step 3: Rodar smoke test

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior/passo_3
python main.py
```

Verificar nos prints:
- `[EMPRESA] 35.237.328/0001-00`
- `[Nome] <nome da empresa>`
- `[GUID] <guid>`
- `[tabela] Status: 200`
- `[log]` linhas geradas
- `[Planilha salva]` ao final

### Step 4: Commit final

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
git add dados/entrada/cnpj_cpf.csv
git commit -m "test(passo_3): add cnpj_cpf.csv test input for smoke test"
```
