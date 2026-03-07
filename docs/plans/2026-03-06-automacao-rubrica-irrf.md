# Automação eSocial — Correção de IRRF em Rúbricas

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ler planilha de eventos por empresa, encontrar cada rúbrica no eSocial via HTTP, validar IRRF e corrigir quando necessário, gerando planilha de resultado Excel.

**Architecture:** Quatro arquivos com responsabilidade única — `planilha.py` lê/agrupa dados, `parser.py` parseia HTML, `cookie.py` (já existe, adicionar 3 funções), `main.py` orquestra. A sessão HTTP é mantida por empresa.

**Tech Stack:** Python 3, requests, openpyxl, BeautifulSoup4 (lxml), subprocess (javaws).

---

## Task 1: `passo_3/planilha.py` — Leitura e agrupamento da planilha de entrada

**Files:**
- Create: `passo_3/planilha.py`

### Step 1: Criar o arquivo `planilha.py`

```python
# passo_3/planilha.py
import openpyxl


def carregar_dados(caminho):
    """
    Lê a planilha de entrada e retorna estrutura agrupada por CNPJ.

    Retorna dict:
    {
        cnpj: {
            "eventos": {
                (evento, evento_aux, irrf, tabela): [
                    {"cpf": str, "competencia": str},
                    ...
                ]
            },
            "todos_cpfs": [str, ...]  # CPFs únicos, ordem de aparição
        }
    }

    Linhas com DEMISSÃO=SIM → status "Demissão" (puladas).
    Linhas com CPF vazio → status "CPF em branco" (puladas).
    Ambas são retornadas em lista separada para registro no resultado.
    """
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb.active

    headers = [str(c.value).strip().upper() if c.value else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]

    def col(row, nome):
        idx = headers.index(nome)
        val = row[idx].value
        return str(val).strip() if val is not None else ""

    empresas = {}   # cnpj → {eventos: {}, todos_cpfs: []}
    puladas = []    # lista de dicts com status já definido

    for row in ws.iter_rows(min_row=2):
        cnpj       = col(row, "CNPJ")
        evento     = col(row, "EVENTO")
        evento_aux = col(row, "EVENTO_AUX")
        irrf       = col(row, "IRRF")
        tabela     = col(row, "TABELA")
        demissao   = col(row, "DEMISSÃO").upper()
        cpf        = col(row, "CPF")
        competencia = col(row, "COMPETENCIA")

        if not cnpj:
            continue

        if demissao == "SIM":
            puladas.append({
                "cnpj": cnpj, "evento": evento, "irrf": irrf,
                "cpf": cpf, "competencia": competencia, "status": "Demissão"
            })
            continue

        if not cpf:
            puladas.append({
                "cnpj": cnpj, "evento": evento, "irrf": irrf,
                "cpf": cpf, "competencia": competencia, "status": "CPF em branco"
            })
            continue

        if cnpj not in empresas:
            empresas[cnpj] = {"eventos": {}, "todos_cpfs": []}

        chave = (evento, evento_aux, irrf, tabela)
        if chave not in empresas[cnpj]["eventos"]:
            empresas[cnpj]["eventos"][chave] = []
        empresas[cnpj]["eventos"][chave].append({"cpf": cpf, "competencia": competencia})

        if cpf not in empresas[cnpj]["todos_cpfs"]:
            empresas[cnpj]["todos_cpfs"].append(cpf)

    return empresas, puladas
```

### Step 2: Verificar sintaxe

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior/passo_3
python -c "import planilha; print('OK')"
```

Expected: `OK`

### Step 3: Commit

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
git add passo_3/planilha.py
git commit -m "feat(passo_3): add planilha.py — read and group spreadsheet by CNPJ"
```

---

## Task 2: `passo_3/parser.py` — Parsing de HTML

**Files:**
- Create: `passo_3/parser.py`

### Step 1: Criar o arquivo `parser.py`

```python
# passo_3/parser.py
import re
from bs4 import BeautifulSoup


def extrair_guid_home(html):
    """
    Extrai o GUID da página home da empresa.
    Procura por link href contendo 'Rubrica/CadastroCompleto?id='.
    Retorna string GUID ou None.
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        m = re.search(r"Rubrica/CadastroCompleto\?id=([a-f0-9\-]+)", href, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def parsear_tabela_funcionario(html, evento, evento_aux, tabela_esperada):
    """
    Parseia a tabela de rúbricas de um funcionário.
    Procura linha onde a coluna "Descrição" bate com evento ou evento_aux
    e a coluna "Tabela" bate com tabela_esperada (se informada).

    Retorna código da rúbrica (coluna "Código") ou None.

    Estrutura da tabela:
      Tabela | Código | Tipo | Descrição | Quantidade | Número contrato | Fator | Valor Unitário | Valor | Ações
    Índices:   0         1      2           3             4                 5       6                7       8
    """
    soup = BeautifulSoup(html, "lxml")
    tabela = soup.find("table", class_=lambda c: c and "sem-paginacao" in c)
    if not tabela:
        return None

    for tr in tabela.find_all("tr")[1:]:  # pula cabeçalho
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        col_tabela    = tds[0].get_text(strip=True)
        col_codigo    = tds[1].get_text(strip=True)
        col_descricao = tds[3].get_text(strip=True)

        # Filtra por tabela se informada
        if tabela_esperada and col_tabela != tabela_esperada:
            continue

        descricao_upper = col_descricao.upper()
        if evento.upper() in descricao_upper or (evento_aux and evento_aux.upper() in descricao_upper):
            return col_codigo

    return None


def parsear_busca_rubrica(html):
    """
    Parseia o HTML retornado pelo POST de busca de rúbrica.
    Retorna (id_rubrica, id_evento) ou (None, None).

    Procura links com href contendo 'Editar?idRubrica=...&idEvento=...'
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        m = re.search(r"idRubrica=(\d+)&idEvento=(\d+)", href)
        if m:
            return m.group(1), m.group(2)
    return None, None


def parsear_form_edicao(html):
    """
    Parseia o formulário de edição de uma rúbrica.
    Retorna dict com todos os campos do form necessários para o POST de salvar,
    incluindo '__RequestVerificationToken' e 'DadosRubrica.CodigoIncidenciaIR'.

    Retorna None se o form não for encontrado.
    """
    soup = BeautifulSoup(html, "lxml")

    # Localiza o form de edição (action contém 'Editar')
    form = None
    for f in soup.find_all("form"):
        action = f.get("action", "")
        if "Editar" in action:
            form = f
            break

    if not form:
        # Tenta qualquer form com o token
        form = soup.find("form")

    if not form:
        return None

    campos = {}

    # Coleta todos inputs, selects e textareas
    for inp in form.find_all(["input", "select", "textarea"]):
        name = inp.get("name")
        if not name:
            continue

        tag = inp.name
        if tag == "select":
            # Pega o option selecionado
            selected = inp.find("option", selected=True)
            value = selected["value"] if selected and selected.get("value") else ""
        elif tag == "input":
            tipo = inp.get("type", "text").lower()
            if tipo == "checkbox":
                value = inp.get("value", "on") if inp.get("checked") else None
                if value is None:
                    continue
            elif tipo == "radio":
                if not inp.get("checked"):
                    continue
                value = inp.get("value", "")
            else:
                value = inp.get("value", "")
        else:  # textarea
            value = inp.get_text()

        # Campos com mesmo nome (ex: FormularioProcesso) → lista
        if name in campos:
            if not isinstance(campos[name], list):
                campos[name] = [campos[name]]
            campos[name].append(value)
        else:
            campos[name] = value

    # Garante campo obrigatório de submit
    if "editar:rubrica" not in campos:
        campos["editar:rubrica"] = "Salvar"

    return campos


def extrair_link_jnlp(html):
    """
    Extrai o link de download do arquivo .jnlp da página Assinadoc.
    Retorna URL completa ou None.
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.endswith(".jnlp") or ".jnlp" in href:
            if href.startswith("http"):
                return href
            return "https://www.esocial.gov.br" + href
    # fallback: busca em qualquer atributo
    m = re.search(r'(https?://[^\s"\']+\.jnlp)', html)
    if m:
        return m.group(1)
    return None
```

### Step 2: Verificar sintaxe

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior/passo_3
python -c "import parser; print('OK')"
```

Expected: `OK`

### Step 3: Commit

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
git add passo_3/parser.py
git commit -m "feat(passo_3): add parser.py — HTML parsing for home GUID, employee table, rubrica form, jnlp"
```

---

## Task 3: Adicionar funções HTTP em `passo_3/cookie.py`

**Files:**
- Modify: `passo_3/cookie.py`

Adicionar três funções ao final da seção de funções (antes do bloco `# ── Execução ──`):

### Step 1: Adicionar `acessar_home_empresa`

Inserir antes do bloco `# ── Execução ──`:

```python
def acessar_home_empresa(session):
    """
    Acessa a home da empresa após selecionar_empresa.
    Retorna HTML (contém o link Rubrica/CadastroCompleto?id=GUID) ou None.
    """
    url = "https://www.esocial.gov.br/portal/Home/Inicial?tipoEmpregador=EMPREGADOR_GERAL"
    headers = {**HEADERS_BASE, "Referer": "https://www.esocial.gov.br/portal/Home/Index"}
    resp = session.get(url, headers=headers)
    print(f"  [home] Status: {resp.status_code} | {len(resp.text)} bytes")
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] Home inesperada")
        return None
    return resp.text


def salvar_edicao(session, id_rubrica, id_evento, campos_form):
    """
    POST para salvar a edição de uma rúbrica.
    campos_form: dict retornado por parsear_form_edicao, já com
                 DadosRubrica.CodigoIncidenciaIR atualizado.
    Retorna (status_code, html_resposta).
    allow_redirects=False para detectar 302 → /Assinadoc.
    """
    url = "https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar"
    referer = (
        f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar"
        f"?idRubrica={id_rubrica}&idEvento={id_evento}"
    )
    headers = {
        **HEADERS_BASE,
        "Referer": referer,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    resp = session.post(url, data=campos_form, headers=headers, allow_redirects=False)
    print(f"  [salvar_edicao] Status: {resp.status_code} | Location: {resp.headers.get('Location', '-')}")
    return resp.status_code, resp.text


def acessar_assinadoc(session):
    """
    GET /portal/Assinadoc — página que contém o link .jnlp para assinar.
    Retorna HTML ou None.
    """
    url = "https://www.esocial.gov.br/portal/Assinadoc"
    headers = {
        **HEADERS_BASE,
        "Referer": "https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar",
    }
    resp = session.get(url, headers=headers)
    print(f"  [assinadoc] Status: {resp.status_code} | {len(resp.text)} bytes")
    if resp.status_code != 200:
        return None
    return resp.text


def baixar_jnlp(session, url_jnlp, pasta_temp):
    """
    Baixa o arquivo .jnlp para pasta_temp.
    Retorna caminho do arquivo salvo ou None.
    """
    import tempfile
    os.makedirs(pasta_temp, exist_ok=True)
    headers = {**HEADERS_BASE, "Referer": "https://www.esocial.gov.br/portal/Assinadoc"}
    resp = session.get(url_jnlp, headers=headers)
    if resp.status_code != 200:
        print(f"  [!] Falha ao baixar .jnlp: {resp.status_code}")
        return None
    nome = url_jnlp.split("/")[-1].split("?")[0]
    if not nome.endswith(".jnlp"):
        nome = "rubrica.jnlp"
    caminho = os.path.join(pasta_temp, nome)
    with open(caminho, "wb") as f:
        f.write(resp.content)
    print(f"  [jnlp] Salvo em: {caminho}")
    return caminho
```

### Step 2: Verificar sintaxe

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior/passo_3
python -c "import cookie; print('OK')"
```

Expected: `OK`

### Step 3: Commit

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
git add passo_3/cookie.py
git commit -m "feat(passo_3): add acessar_home_empresa, salvar_edicao, acessar_assinadoc, baixar_jnlp to cookie.py"
```

---

## Task 4: `passo_3/main.py` — Loop principal de orquestração

**Files:**
- Create: `passo_3/main.py`

### Step 1: Criar `passo_3/main.py`

```python
# passo_3/main.py
import os
import subprocess
import tempfile
from datetime import datetime

import openpyxl
import requests

from cookie import (
    ler_cookies,
    selecionar_empresa,
    trocar_perfil,
    acessar_home_empresa,
    acessar_tabela_funcionário,
    acessar_rubrica,
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
from planilha import carregar_dados

# ── Configuração ───────────────────────────────────────────────────────────────

COOKIES_FILE = os.path.join(os.path.dirname(__file__), "..", "cookies.txt")
PLANILHA_ENTRADA = os.path.join(os.path.dirname(__file__), "..", "dados", "entrada", "eventos_irrf.xlsx")
PASTA_TEMP_JNLP = os.path.join(tempfile.gettempdir(), "esocial_jnlp")

# Meses de fallback: dez/2024 a dez/2025 em formato YYYYMM
MESES_FALLBACK = [
    "202412", "202501", "202502", "202503", "202504", "202505",
    "202506", "202507", "202508", "202509", "202510", "202511", "202512",
]

# ── Resultado ──────────────────────────────────────────────────────────────────

linhas_resultado = []  # lista de dicts


def registrar(cnpj, evento, codigo_rubrica, irrf_antes, irrf_depois, cpf, competencia, status):
    linhas_resultado.append({
        "Empresa": cnpj,
        "Evento": evento,
        "Código Rúbrica": codigo_rubrica,
        "IRRF antes": irrf_antes,
        "IRRF depois": irrf_depois,
        "Colaborador (CPF)": cpf,
        "Competência": competencia,
        "Status": status,
    })
    print(f"  [resultado] {cnpj} | {evento} | {status}")


def salvar_planilha_resultado():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultado"
    colunas = ["Empresa", "Evento", "Código Rúbrica", "IRRF antes", "IRRF depois",
                "Colaborador (CPF)", "Competência", "Status"]
    ws.append(colunas)
    for linha in linhas_resultado:
        ws.append([linha[c] for c in colunas])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = os.path.join(os.path.dirname(__file__), f"resultado_irrf_{ts}.xlsx")
    wb.save(nome)
    print(f"\n[Resultado salvo] {nome}")
    return nome


# ── Helpers ────────────────────────────────────────────────────────────────────

def tentar_encontrar_rubrica(session, cpf, competencia, evento, evento_aux, tabela):
    """
    Acessa tabela do colaborador e procura rúbrica que bate com evento/evento_aux/tabela.
    Retorna (codigo_rubrica, html_tabela) ou (None, None).
    """
    html = acessar_tabela_funcionário(session, cpf, competencia)
    if not html:
        return None, None
    codigo = parsear_tabela_funcionario(html, evento, evento_aux, tabela)
    return codigo, html


def assinar_jnlp(session):
    """
    Acessa Assinadoc, baixa .jnlp e executa com javaws.
    Retorna True se sucesso, False caso contrário.
    """
    html_assinadoc = acessar_assinadoc(session)
    if not html_assinadoc:
        print("  [!] Assinadoc não retornou HTML")
        return False

    url_jnlp = extrair_link_jnlp(html_assinadoc)
    if not url_jnlp:
        print("  [!] Link .jnlp não encontrado na página Assinadoc")
        return False

    caminho_jnlp = baixar_jnlp(session, url_jnlp, PASTA_TEMP_JNLP)
    if not caminho_jnlp:
        return False

    try:
        resultado = subprocess.run(
            ["javaws", caminho_jnlp],
            timeout=120,
            capture_output=True,
        )
        if resultado.returncode == 0:
            print("  [javaws] Concluído com sucesso")
            return True
        else:
            print(f"  [javaws] Retornou código {resultado.returncode}")
            return False
    except FileNotFoundError:
        print("  [!] javaws não encontrado no PATH")
        return False
    except subprocess.TimeoutExpired:
        print("  [!] javaws timeout (120s)")
        return False


# ── Loop principal ─────────────────────────────────────────────────────────────

def main():
    # Carrega sessão
    session = requests.Session()
    cookies_base = ler_cookies(COOKIES_FILE)
    session.cookies.update(cookies_base)

    usuario_logado_procurador = cookies_base.get("UsuarioLogado", "")
    cpf_procurador = cookies_base.get("usuario_logado_ws", "")

    # Carrega planilha
    empresas, puladas = carregar_dados(PLANILHA_ENTRADA)

    # Registra linhas puladas imediatamente
    for p in puladas:
        registrar(p["cnpj"], p["evento"], "", "", "", p["cpf"], p["competencia"], p["status"])

    # Loop por empresa
    for cnpj, dados in empresas.items():
        print(f"\n{'='*60}")
        print(f"[EMPRESA] {cnpj}")

        ok = selecionar_empresa(session, cnpj)
        if not ok:
            print(f"  [!] Falha ao selecionar empresa {cnpj}")
            for chave in dados["eventos"]:
                evento, *_ = chave
                registrar(cnpj, evento, "", "", "", "", "", "Não encontrado")
            trocar_perfil(session, usuario_logado_procurador, cpf_procurador)
            continue

        # Extrai GUID da home
        html_home = acessar_home_empresa(session)
        guid = extrair_guid_home(html_home) if html_home else None
        if not guid:
            print(f"  [!] GUID não encontrado na home de {cnpj}")
            for chave in dados["eventos"]:
                evento, *_ = chave
                registrar(cnpj, evento, "", "", "", "", "", "Não encontrado")
            trocar_perfil(session, usuario_logado_procurador, cpf_procurador)
            continue

        print(f"  [GUID] {guid}")

        # Cache de HTML por (cpf, competencia) para evitar requests repetidas
        cache_tabela = {}  # (cpf, competencia) → html

        # Eventos pendentes: chave → True/False
        pendentes = {chave: True for chave in dados["eventos"]}
        # Resultado de cada evento: chave → dict com codigo_rubrica, cpf, competencia
        encontrados = {}  # chave → {"codigo": str, "cpf": str, "competencia": str}

        # ── Fase 1: colaboradores da própria linha do evento ──────────────
        for chave, colaboradores in dados["eventos"].items():
            if not pendentes[chave]:
                continue
            evento, evento_aux, irrf, tabela = chave

            for colab in colaboradores:
                cpf = colab["cpf"]
                competencia = colab["competencia"]
                cache_key = (cpf, competencia)

                if cache_key not in cache_tabela:
                    html = acessar_tabela_funcionário(session, cpf, competencia)
                    cache_tabela[cache_key] = html
                else:
                    html = cache_tabela[cache_key]

                if not html:
                    continue

                # Tenta resolver TODOS os eventos pendentes com este HTML
                for chave2, colab2_lista in dados["eventos"].items():
                    if not pendentes[chave2]:
                        continue
                    ev2, ev_aux2, _, tab2 = chave2
                    codigo = parsear_tabela_funcionario(html, ev2, ev_aux2, tab2)
                    if codigo:
                        pendentes[chave2] = False
                        encontrados[chave2] = {"codigo": codigo, "cpf": cpf, "competencia": competencia}

                if not pendentes[chave]:
                    break  # este evento já foi resolvido

        # ── Fase 2: fallback — todos CPFs × todos meses ───────────────────
        if any(pendentes.values()):
            print(f"  [fallback] Iniciando busca em todos CPFs × meses")
            for cpf in dados["todos_cpfs"]:
                if not any(pendentes.values()):
                    break
                for mes in MESES_FALLBACK:
                    if not any(pendentes.values()):
                        break
                    cache_key = (cpf, mes)
                    if cache_key not in cache_tabela:
                        html = acessar_tabela_funcionário(session, cpf, mes)
                        cache_tabela[cache_key] = html
                    else:
                        html = cache_tabela[cache_key]

                    if not html:
                        continue

                    for chave2 in list(dados["eventos"].keys()):
                        if not pendentes[chave2]:
                            continue
                        ev2, ev_aux2, _, tab2 = chave2
                        codigo = parsear_tabela_funcionario(html, ev2, ev_aux2, tab2)
                        if codigo:
                            pendentes[chave2] = False
                            encontrados[chave2] = {"codigo": codigo, "cpf": cpf, "competencia": mes}

        # ── Processar cada evento ─────────────────────────────────────────
        for chave in dados["eventos"]:
            evento, evento_aux, irrf_planilha, tabela = chave

            if pendentes[chave]:
                registrar(cnpj, evento, "", "", "", "", "", "Não encontrado")
                continue

            info = encontrados[chave]
            codigo_rubrica = info["codigo"]
            cpf_encontrado = info["cpf"]
            competencia_encontrada = info["competencia"]

            # Validação de domínio
            if len(codigo_rubrica) < 28:
                registrar(cnpj, evento, codigo_rubrica, "", "", cpf_encontrado, competencia_encontrada, "Rúbrica não é do domínio")
                continue

            # Buscar idRubrica e idEvento
            html_busca = buscar_rubrica(session, guid, codigo_rubrica)
            if not html_busca:
                registrar(cnpj, evento, codigo_rubrica, "", "", cpf_encontrado, competencia_encontrada, "Não encontrado")
                continue

            id_rubrica, id_evento = parsear_busca_rubrica(html_busca)
            if not id_rubrica:
                registrar(cnpj, evento, codigo_rubrica, "", "", cpf_encontrado, competencia_encontrada, "Não encontrado")
                continue

            # Abrir form de edição
            html_edicao = abrir_edicao_rubrica(session, id_rubrica, id_evento, guid)
            if not html_edicao:
                registrar(cnpj, evento, codigo_rubrica, "", "", cpf_encontrado, competencia_encontrada, "Não encontrado")
                continue

            campos = parsear_form_edicao(html_edicao)
            if not campos:
                registrar(cnpj, evento, codigo_rubrica, "", "", cpf_encontrado, competencia_encontrada, "Não encontrado")
                continue

            irrf_atual = campos.get("DadosRubrica.CodigoIncidenciaIR", "")

            # Validar IRRF
            if str(irrf_atual) == str(irrf_planilha):
                registrar(cnpj, evento, codigo_rubrica, irrf_atual, irrf_atual, cpf_encontrado, competencia_encontrada, "OK")
                continue

            # Corrigir IRRF
            campos["DadosRubrica.CodigoIncidenciaIR"] = irrf_planilha
            status_code, _ = salvar_edicao(session, id_rubrica, id_evento, campos)

            if status_code == 302:
                ok_jnlp = assinar_jnlp(session)
                if ok_jnlp:
                    registrar(cnpj, evento, codigo_rubrica, irrf_atual, irrf_planilha, cpf_encontrado, competencia_encontrada, "Atualizado")
                else:
                    registrar(cnpj, evento, codigo_rubrica, irrf_atual, irrf_planilha, cpf_encontrado, competencia_encontrada, "jnlp não assinado")
            else:
                print(f"  [!] POST salvar retornou {status_code} (esperado 302)")
                registrar(cnpj, evento, codigo_rubrica, irrf_atual, irrf_planilha, cpf_encontrado, competencia_encontrada, "jnlp não assinado")

        trocar_perfil(session, usuario_logado_procurador, cpf_procurador)

    # Salva resultado
    salvar_planilha_resultado()


if __name__ == "__main__":
    main()
```

### Step 2: Verificar sintaxe

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior/passo_3
python -c "import ast; ast.parse(open('main.py').read()); print('OK')"
```

Expected: `OK`

### Step 3: Commit

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
git add passo_3/main.py
git commit -m "feat(passo_3): add main.py — orchestration loop for IRRF rubrica validation and correction"
```

---

## Task 5: Teste de fumaça com 1 empresa

Antes de rodar em produção, editar `PLANILHA_ENTRADA` em `main.py` apontando para um xlsx de teste com **1 empresa, 1 evento, 1 colaborador**, e verificar o fluxo completo.

### Step 1: Verificar que a planilha de entrada existe

Confirmar que `dados/entrada/eventos_irrf.xlsx` existe com as colunas:
`CNPJ`, `EVENTO`, `EVENTO_AUX`, `IRRF`, `TABELA`, `DEMISSÃO`, `CPF`, `COMPETENCIA`

Se não existir, criar uma planilha de teste com 1 linha válida.

### Step 2: Rodar com 1 empresa

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior/passo_3
python main.py
```

Verificar nos prints:
- `[EMPRESA] <cnpj>` — empresa selecionada
- `[GUID] <guid>` — GUID extraído da home
- `[tabela] Status: 200` — tabela do funcionário carregada
- `[resultado]` — linha registrada com status correto

### Step 3: Verificar planilha gerada

Abrir o arquivo `passo_3/resultado_irrf_*.xlsx` e conferir as colunas e valores.

### Step 4: Commit final

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
git add passo_3/
git commit -m "test(passo_3): smoke test with 1 company — verify full IRRF rubrica flow"
```

---

## Checklist de validação

- [ ] `planilha.py`: linhas com DEMISSÃO=SIM → status "Demissão"
- [ ] `planilha.py`: linhas com CPF vazio → status "CPF em branco"
- [ ] `planilha.py`: agrupamento por CNPJ → eventos → colaboradores correto
- [ ] `parser.py`: `extrair_guid_home` retorna GUID da home da empresa
- [ ] `parser.py`: `parsear_tabela_funcionario` acha rúbrica pela descrição
- [ ] `parser.py`: `parsear_busca_rubrica` retorna idRubrica e idEvento
- [ ] `parser.py`: `parsear_form_edicao` retorna todos os campos do form
- [ ] `cookie.py`: `acessar_home_empresa` retorna HTML com link de rúbrica
- [ ] `cookie.py`: `salvar_edicao` retorna 302 ao salvar
- [ ] `cookie.py`: `acessar_assinadoc` retorna HTML com link .jnlp
- [ ] `cookie.py`: `baixar_jnlp` salva arquivo em pasta temp
- [ ] `main.py`: rúbrica com código <28 chars → "Rúbrica não é do domínio"
- [ ] `main.py`: IRRF já correto → "OK"
- [ ] `main.py`: IRRF corrigido + javaws OK → "Atualizado"
- [ ] `main.py`: javaws falhou → "jnlp não assinado"
- [ ] `main.py`: não encontrado em nenhum CPF/mês → "Não encontrado"
- [ ] Planilha resultado gerada com nome `resultado_irrf_YYYYMMDD_HHMMSS.xlsx`
