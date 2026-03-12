# Scanner + Validador eSocial Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar passo_4 (scanner de holerites com CPF), passo_5 (validador eSocial com id_rubrica por evento) e passo_6 (corretor adaptado), integrando os três num pipeline retomável.

**Architecture:** Scripts independentes com JSON intermediário. Passo 4 lê PDFs/CSVs locais e produz `scanner_*.json`. Passo 5 consome esse JSON, acessa o eSocial e produz `validacao_*.json`. Passo 6 é o `corretor.py` adaptado para ler o novo formato.

**Tech Stack:** Python 3.x, pdfplumber, requests, bs4/lxml, passo_3/cookie.py e passo_3/parser.py (reutilizados via sys.path).

---

## Task 1: Adicionar extração de CPF ao scanner (passo_4)

**Files:**
- Modify: `passo_4/scanner_holerites.py` — função `parse_pdf_holerite`

### Contexto

O PDF do holerite Senior ERP contém o CPF do colaborador em algum ponto da página. O layout duplicado (2 colunas) significa que o CPF pode aparecer duas vezes. Precisamos extrair apenas 1 CPF por página.

O CPF tem formato `NNN.NNN.NNN-NN` (formatado) ou `NNNNNNNNNNN` (11 dígitos seguidos). Deve ser diferenciado do CNPJ (14 dígitos) e de outros números.

### Step 1: Identificar onde o CPF aparece no PDF

Rode este script de diagnóstico para ver o texto completo de uma página:

```python
# diagnose_cpf.py  (rodar da raiz do projeto)
import pdfplumber, sys
from pathlib import Path

pdf = Path("dados/saida/153 TECNOLOGIA/FOLHA DE PAGAMENTO/2025/04-2025/HOLERITE.pdf")
with pdfplumber.open(pdf) as doc:
    texto = doc.pages[0].extract_text() or ""
    print(texto)
```

Rodar: `python diagnose_cpf.py`

Procure por um padrão `NNN.NNN.NNN-NN` ou sequência de 11 dígitos no output.

### Step 2: Adicionar função `_extrair_cpf_pagina` em `passo_4/scanner_holerites.py`

Adicionar após a função `normalizar` (linha ~52):

```python
def _extrair_cpf_pagina(texto: str) -> str:
    """
    Extrai o CPF do colaborador do texto de uma página de holerite.
    Retorna string de 11 dígitos ou '' se não encontrado.

    Prioridade:
      1. CPF formatado: NNN.NNN.NNN-NN
      2. 11 dígitos seguidos (que não sejam parte de CNPJ de 14 dígitos)
    """
    # 1. CPF formatado
    m = re.search(r"\b(\d{3})[.\s](\d{3})[.\s](\d{3})[-\s](\d{2})\b", texto)
    if m:
        return m.group(1) + m.group(2) + m.group(3) + m.group(4)

    # 2. 11 dígitos que não são precedidos/seguidos de mais dígitos (evita CNPJ)
    for m in re.finditer(r"(?<!\d)(\d{11})(?!\d)", texto):
        candidato = m.group(1)
        # Descarta sequências óbvias (000, 111... CPFs inválidos)
        if len(set(candidato)) > 1:
            return candidato

    return ""
```

### Step 3: Integrar `_extrair_cpf_pagina` em `parse_pdf_holerite`

Localizar no arquivo a linha onde está o comentário `# Extrair cadastro do cabeçalho` (por volta da linha 354). Logo **antes** desse bloco, adicionar:

```python
                # ── Extrair CPF do colaborador ───────────────────────────
                cpf_colab = _extrair_cpf_pagina(texto)
```

E atualizar o `resultados.append` no final da função (linha ~411) para incluir `cpf`:

```python
                if evs_encontrados and nome_colab:
                    resultados.append({
                        "cadastro": cadastro,
                        "cpf": cpf_colab,
                        "nome": nome_colab,
                        "eventos": evs_encontrados,
                    })
```

### Step 4: Atualizar `scan()` para incluir `cpf` no JSON de saída

Localizar o bloco `matches_empresa.append(` (linha ~517). Adicionar `"cpf"`:

```python
                for c in colabs:
                    matches_empresa.append(
                        {
                            "competencia": f"{mes:02d}/{ano}",
                            "cpf": c.get("cpf", ""),
                            "cadastro": c["cadastro"],
                            "nome": c["nome"],
                            "eventos": c["eventos"],
                        }
                    )
```

### Step 5: Verificar extração rodando o scanner numa empresa

```bash
cd C:\Users\Auster\Documents\GitHub\scrapingSenior
python passo_4/scanner_holerites.py
```

Verificar no JSON gerado que os colaboradores têm campo `cpf` preenchido.

### Step 6: Commit

```bash
git add passo_4/scanner_holerites.py
git commit -m "feat(passo_4): adiciona extração de CPF do PDF de holerites"
```

---

## Task 2: Criar estrutura do passo_5

**Files:**
- Create: `passo_5/__init__.py`
- Create: `passo_5/validador_esocial.py`

### Contexto

O `passo_5` precisa importar `cookie.py` e `parser.py` do `passo_3`. Como os módulos do passo_3 usam imports relativos (`from cookie import ...`), a forma mais simples é adicionar `passo_3/` ao `sys.path` no início do script.

O validador lê o `scanner_*.json` mais recente (ou o arquivo passado por argumento), processa empresa por empresa, e salva progresso incremental em `validacao_*.json`.

### Step 1: Criar `passo_5/__init__.py`

Criar arquivo vazio:

```python
# passo_5/__init__.py
```

### Step 2: Criar `passo_5/validador_esocial.py` — esqueleto + imports

```python
#!/usr/bin/env python3
"""
passo_5/validador_esocial.py

Para cada empresa do scanner JSON:
  - Acessa o eSocial e busca 1 id_rubrica por evento (o primeiro que achar)
  - Compara irrf_atual vs irrf_esperado
  - Salva validacao_TIMESTAMP.json (retomável com --retomar)

Uso:
  python passo_5/validador_esocial.py [scanner_*.json] [--retomar validacao_*.json]
"""

import sys
import os
import glob
import json
import csv
import re
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import requests

# Importar módulos do passo_3 via sys.path
_PASSO3 = str(Path(__file__).parent.parent / "passo_3")
if _PASSO3 not in sys.path:
    sys.path.insert(0, _PASSO3)

from cookie import (
    ler_cookies,
    selecionar_empresa,
    trocar_perfil,
    acessar_home_empresa,
    acessar_tabela_funcionário,
    buscar_rubrica,
    abrir_edicao_rubrica,
)
from parser import (
    extrair_guid_home,
    parsear_tabela_funcionario,
    parsear_busca_rubrica,
    parsear_form_edicao,
)

BASE_DIR     = Path(__file__).parent.parent
DADOS_SAIDA  = BASE_DIR / "dados" / "saida"
DADOS_ENTRADA = BASE_DIR / "dados" / "entrada"
COOKIES_FILE = BASE_DIR / "passo_3" / "cookies.txt"

MAX_RETRIES = 3
```

### Step 3: Adicionar funções de carregamento de dados

Continuar no mesmo arquivo, após os imports:

```python
def _json_mais_recente(prefixo: str) -> str | None:
    arquivos = sorted(glob.glob(str(DADOS_SAIDA / f"{prefixo}_*.json")))
    return arquivos[-1] if arquivos else None


def _carregar_json(caminho: str) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _salvar_json(dados: dict, caminho: str) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def carregar_esocial_map() -> dict:
    """
    Retorna dict: id_evento → {nome_esocial, nome_esocial_aux, irrf, tabela}
    Para eventos com múltiplas linhas (mesmo id_evento), guarda TODOS como lista.
    """
    mapa = {}
    caminho = DADOS_ENTRADA / "esocial.csv"
    with open(caminho, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            id_ev = row["id_evento"].strip()
            entrada = {
                "nome_esocial": row["nome_esocial"].strip(),
                "nome_esocial_aux": row["nome_esocial_aux"].strip(),
                "irrf": row["irrf"].strip(),
                "tabela": row["tabela"].strip(),
            }
            if id_ev not in mapa:
                mapa[id_ev] = entrada
    return mapa
```

### Step 4: Commit parcial

```bash
git add passo_5/
git commit -m "feat(passo_5): estrutura inicial do validador eSocial"
```

---

## Task 3: Implementar lógica principal do validador

**Files:**
- Modify: `passo_5/validador_esocial.py`

### Step 1: Adicionar função `validar_empresa`

```python
def validar_empresa(
    session: requests.Session,
    empresa: dict,
    esocial_map: dict,
    usuario_logado_proc: str,
    cpf_proc: str,
) -> dict:
    """
    Processa uma empresa do scanner JSON.
    Retorna dict no formato validacao JSON (rubricas, nao_encontrados, alertas).
    """
    cnpj_digits = empresa["cnpj"]
    # Formatar CNPJ: XX.XXX.XXX/XXXX-XX
    cnpj_fmt = f"{cnpj_digits[:2]}.{cnpj_digits[2:5]}.{cnpj_digits[5:8]}/{cnpj_digits[8:12]}-{cnpj_digits[12:]}"

    resultado = {
        "nome": empresa["nome_empresa"],
        "guid": None,
        "auditado_em": None,
        "rubricas": [],
        "nao_encontrados": [],
        "alertas": [],
    }

    # 1. Selecionar empresa no eSocial
    ok = selecionar_empresa(session, cnpj_fmt)
    if not ok:
        resultado["alertas"].append(f"Falha ao selecionar empresa {cnpj_fmt}")
        trocar_perfil(session, usuario_logado_proc, cpf_proc)
        return resultado

    # 2. Obter GUID
    html_home = acessar_home_empresa(session)
    if not html_home:
        resultado["alertas"].append("Home da empresa não acessível")
        trocar_perfil(session, usuario_logado_proc, cpf_proc)
        return resultado

    guid = extrair_guid_home(html_home)
    if not guid:
        resultado["alertas"].append("GUID não encontrado na home")
        trocar_perfil(session, usuario_logado_proc, cpf_proc)
        return resultado

    resultado["guid"] = guid

    # 3. Montar lista de eventos pendentes
    # Cada id_evento precisa de apenas 1 id_rubrica por empresa
    todos_eventos = set()
    for colab in empresa["colaboradores"]:
        for ev in colab["eventos"]:
            todos_eventos.add(ev)

    eventos_pendentes = deepcopy(todos_eventos)

    # 4. Iterar colaboradores até resolver todos eventos
    for colab in empresa["colaboradores"]:
        if not eventos_pendentes:
            break

        cpf = colab.get("cpf", "")
        if not cpf:
            continue

        # Converter competencia "MM/AAAA" → "YYYYMM"
        comp_raw = colab["competencia"]  # ex: "12/2024"
        try:
            mes, ano = comp_raw.split("/")
            competencia = f"{ano}{mes.zfill(2)}"
        except ValueError:
            continue

        # Acessar tabela do colaborador com retry
        html_tabela = None
        for tentativa in range(MAX_RETRIES):
            html_tabela = acessar_tabela_funcionário(session, cpf, competencia, guid)
            if html_tabela:
                break
            print(f"  [retry {tentativa+1}/{MAX_RETRIES}] tabela {cpf} {competencia}")
            time.sleep(2 ** tentativa)

        if not html_tabela:
            continue

        # Buscar todos os eventos pendentes nesta tabela
        eventos_resolvidos = []
        for id_ev in list(eventos_pendentes):
            info = esocial_map.get(id_ev)
            if not info:
                continue

            nome_esocial = info["nome_esocial"]
            nome_aux = info["nome_esocial_aux"]
            tabela = info["tabela"]
            irrf_esperado = info["irrf"]

            codigo = parsear_tabela_funcionario(html_tabela, nome_esocial, nome_aux, tabela)
            if not codigo:
                continue

            # Encontrou o evento — buscar id_rubrica
            html_busca = buscar_rubrica(session, guid, codigo)
            if not html_busca:
                continue

            id_rubrica, id_evento_rubrica = parsear_busca_rubrica(html_busca)
            if not id_rubrica:
                continue

            # Abrir edição para obter campos_form e irrf_atual
            html_edicao = abrir_edicao_rubrica(session, id_rubrica, id_evento_rubrica, guid)
            if not html_edicao:
                continue

            campos = parsear_form_edicao(html_edicao)
            irrf_atual = str(campos.get("DadosRubrica.CodigoIncidenciaIR", "")) if campos else ""
            status = "CORRETO" if irrf_atual == irrf_esperado else "ERRADO"

            resultado["rubricas"].append({
                "id_rubrica": id_rubrica,
                "id_evento": id_evento_rubrica,
                "guid": guid,
                "nome_evento": nome_esocial,
                "cpf_usado": cpf,
                "competencia_usada": competencia,
                "irrf_atual": irrf_atual,
                "irrf_esperado": irrf_esperado,
                "campos_form": campos or {},
                "status": status,
            })

            eventos_resolvidos.append(id_ev)
            print(f"  [{'OK' if status == 'CORRETO' else 'ERRADO'}] evento {id_ev} | irrf {irrf_atual} vs {irrf_esperado}")

        for ev in eventos_resolvidos:
            eventos_pendentes.discard(ev)

    # 5. Registrar não encontrados
    for id_ev in eventos_pendentes:
        resultado["nao_encontrados"].append(id_ev)
        resultado["alertas"].append(
            f"Evento {id_ev} encontrado no holerite mas não localizado no eSocial"
        )

    resultado["auditado_em"] = datetime.now().isoformat()

    trocar_perfil(session, usuario_logado_proc, cpf_proc)
    return resultado
```

### Step 2: Adicionar função `main`

```python
def main():
    args = sys.argv[1:]

    # Detectar --retomar
    retomar_path = None
    if "--retomar" in args:
        idx = args.index("--retomar")
        retomar_path = args[idx + 1] if idx + 1 < len(args) else _json_mais_recente("validacao")
        args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]

    # Scanner JSON de entrada
    scanner_path = args[0] if args else _json_mais_recente("scanner")
    if not scanner_path:
        print("[ERRO] Nenhum scanner_*.json encontrado em dados/saida/")
        sys.exit(1)
    print(f"[Scanner] {scanner_path}")

    scanner = _carregar_json(scanner_path)

    # Carregar ou criar JSON de validação
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if retomar_path:
        validacao = _carregar_json(retomar_path)
        output_path = retomar_path
        print(f"[Retomando] {retomar_path}")
    else:
        validacao = {}
        output_path = str(DADOS_SAIDA / f"validacao_{timestamp}.json")

    esocial_map = carregar_esocial_map()

    # Sessão HTTP
    session = requests.Session()
    cookies_base = ler_cookies(str(COOKIES_FILE))
    session.cookies.update(cookies_base)
    usuario_logado_proc = cookies_base.get("UsuarioLogado", "")
    cpf_proc = cookies_base.get("usuario_logado_ws", "")

    empresas = list(scanner.values())
    total = len(empresas)

    for i, empresa in enumerate(empresas, 1):
        cnpj = empresa["cnpj"]

        # Pular se já processada (retomada)
        if cnpj in validacao and validacao[cnpj].get("auditado_em"):
            print(f"[{i}/{total}] {empresa['nome_empresa']} — já processada, pulando")
            continue

        print(f"\n[{i}/{total}] {empresa['nome_empresa']} | CNPJ: {cnpj}")

        resultado = validar_empresa(
            session, empresa, esocial_map, usuario_logado_proc, cpf_proc
        )
        validacao[cnpj] = resultado
        _salvar_json(validacao, output_path)

    print(f"\n[FIM] Validação salva em: {output_path}")


if __name__ == "__main__":
    main()
```

### Step 3: Testar imports e sintaxe

```bash
cd C:\Users\Auster\Documents\GitHub\scrapingSenior
python -c "
import sys; sys.path.insert(0, '.')
import ast
with open('passo_5/validador_esocial.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Sintaxe OK')
"
```

Esperado: `Sintaxe OK`

### Step 4: Testar carregamento sem eSocial (offline)

```bash
python -c "
import sys; sys.path.insert(0, 'passo_3')
from passo_5.validador_esocial import carregar_esocial_map, _json_mais_recente
m = carregar_esocial_map()
print(f'Eventos no mapa: {len(m)}')
p = _json_mais_recente('scanner')
print(f'Scanner mais recente: {p}')
"
```

Esperado: `Eventos no mapa: X` e o caminho do JSON do scanner.

### Step 5: Commit

```bash
git add passo_5/validador_esocial.py passo_5/__init__.py
git commit -m "feat(passo_5): implementa validador eSocial com lógica de id_rubrica por evento"
```

---

## Task 4: Criar passo_6/corretor.py adaptado

**Files:**
- Create: `passo_6/__init__.py`
- Create: `passo_6/corretor.py`

### Contexto

O `passo_3/corretor.py` já funciona perfeitamente. A única diferença é que:
- O formato antigo usa `empresa["rubricas"]` com chave `cnpj` no nível raiz
- O formato novo (passo_5) usa `cnpj` como chave do dict e `empresa["rubricas"]` igual

Portanto a adaptação é mínima — basicamente o `corretor.py` do passo_3 já quase serve. Só precisamos:
1. Mudar o padrão de busca de `auditoria_*.json` para `validacao_*.json`
2. Garantir que o campo `guid` vem de dentro de cada rubrica (passo_5 o inclui)
3. Ajustar o `cnpj` do loop (no novo formato, a chave do dict é o CNPJ formatado com dígitos)

### Step 1: Criar `passo_6/__init__.py`

```python
# passo_6/__init__.py
```

### Step 2: Criar `passo_6/corretor.py`

```python
#!/usr/bin/env python3
"""
passo_6/corretor.py

Lê validacao_*.json gerado pelo passo_5 e corrige rubricas com status='ERRADO'.
Adaptação mínima do passo_3/corretor.py para o novo formato JSON.

Uso:
  python passo_6/corretor.py [validacao_*.json]
"""

import glob
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

# Importar módulos do passo_3 via sys.path
_PASSO3 = str(Path(__file__).parent.parent / "passo_3")
if _PASSO3 not in sys.path:
    sys.path.insert(0, _PASSO3)

from cookie import (
    ler_cookies,
    selecionar_empresa,
    trocar_perfil,
    acessar_assinadoc,
    abrir_edicao_rubrica,
    salvar_edicao,
    baixar_jnlp,
)
from parser import parsear_form_edicao, extrair_link_jnlp

BASE_DIR        = Path(__file__).parent.parent
COOKIES_FILE    = BASE_DIR / "passo_3" / "cookies.txt"
PASTA_SAIDA     = BASE_DIR / "dados" / "saida"
PASTA_TEMP_JNLP = os.path.join(tempfile.gettempdir(), "esocial_jnlp")


def _encontrar_json_mais_recente() -> str | None:
    arquivos = sorted(glob.glob(str(PASTA_SAIDA / "validacao_*.json")))
    return arquivos[-1] if arquivos else None


def _carregar(caminho: str) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _salvar(dados: dict, caminho: str) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def assinar_jnlp(session: requests.Session) -> bool:
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


def corrigir_rubrica(session: requests.Session, rubrica: dict) -> str:
    """
    Re-abre o formulário, verifica IRRF atual e corrige se ainda errado.
    Retorna: CORRIGIDO | CORRIGIDO_EXTERNAMENTE | ERRO_FORM | ERRO_ASSINATURA
    """
    id_rubrica    = rubrica["id_rubrica"]
    id_evento     = rubrica["id_evento"]
    guid          = rubrica.get("guid")
    irrf_esperado = str(rubrica["irrf_esperado"])
    nome_evento   = rubrica["nome_evento"]

    html_edicao = abrir_edicao_rubrica(session, id_rubrica, id_evento, guid)
    if not html_edicao:
        print(f"  [!] {nome_evento} — abrir_edicao falhou")
        return "ERRO_FORM"

    campos = parsear_form_edicao(html_edicao)
    if not campos:
        print(f"  [!] {nome_evento} — parsear_form falhou")
        return "ERRO_FORM"

    irrf_atual = str(campos.get("DadosRubrica.CodigoIncidenciaIR", ""))

    if irrf_atual == irrf_esperado:
        print(f"  [JA_CORRETO] {nome_evento} — CORRIGIDO_EXTERNAMENTE")
        return "CORRIGIDO_EXTERNAMENTE"

    campos["DadosRubrica.CodigoIncidenciaIR"] = irrf_esperado
    status_code, _ = salvar_edicao(session, id_rubrica, id_evento, campos)

    ok = assinar_jnlp(session) if status_code == 302 else False
    if ok:
        print(f"  [CORRIGIDO] {nome_evento} | {irrf_atual} → {irrf_esperado}")
        return "CORRIGIDO"
    else:
        print(f"  [!] {nome_evento} — assinatura falhou (status_code={status_code})")
        return "ERRO_ASSINATURA"


def main():
    caminho = sys.argv[1] if len(sys.argv) > 1 else _encontrar_json_mais_recente()
    if not caminho:
        print("[!] Nenhum validacao_*.json encontrado em dados/saida/")
        sys.exit(1)
    print(f"[JSON] {caminho}")

    dados = _carregar(caminho)

    session = requests.Session()
    cookies_base = ler_cookies(str(COOKIES_FILE))
    session.cookies.update(cookies_base)
    usuario_logado_proc = cookies_base.get("UsuarioLogado", "")
    cpf_proc = cookies_base.get("usuario_logado_ws", "")

    for cnpj, empresa in dados.items():
        erradas = [r for r in empresa.get("rubricas", []) if r.get("status") == "ERRADO"]
        if not erradas:
            continue

        print(f"\n{'='*60}")
        print(f"[EMPRESA] {cnpj} | {empresa['nome']} | {len(erradas)} rúbrica(s) ERRADA(s)")

        # Formatar CNPJ para selecionar_empresa (XX.XXX.XXX/XXXX-XX)
        d = re.sub(r"\D", "", cnpj) if len(cnpj) > 14 else cnpj
        cnpj_fmt = f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}" if len(d) == 14 else cnpj

        ok = selecionar_empresa(session, cnpj_fmt)
        if not ok:
            print(f"  [!] Falha ao selecionar {cnpj_fmt}")
            trocar_perfil(session, usuario_logado_proc, cpf_proc)
            continue

        for rubrica in erradas:
            rubrica["status"] = corrigir_rubrica(session, rubrica)
            _salvar(dados, caminho)

        trocar_perfil(session, usuario_logado_proc, cpf_proc)

    print(f"\n[FIM] JSON atualizado: {caminho}")


if __name__ == "__main__":
    import re
    main()
```

### Step 3: Adicionar `import re` no topo do arquivo

Verificar que `import re` está no topo (necessário para formatar CNPJ no main).

### Step 4: Testar sintaxe

```bash
cd C:\Users\Auster\Documents\GitHub\scrapingSenior
python -c "
import ast
with open('passo_6/corretor.py', encoding='utf-8') as f:
    ast.parse(f.read())
print('Sintaxe OK')
"
```

### Step 5: Commit

```bash
git add passo_6/
git commit -m "feat(passo_6): corretor adaptado para formato JSON do passo_5"
```

---

## Task 5: Ajustes finais e integração

**Files:**
- Modify: `passo_4/scanner_holerites.py` — ignorar pasta `validacao_*`
- Modify: `passo_5/validador_esocial.py` — pequeno ajuste no CNPJ formatter
- Modify: `passo_6/corretor.py` — mover `import re` para o topo

### Step 1: Corrigir `import re` em `passo_6/corretor.py`

O `import re` no bloco `main()` deve ficar no topo do arquivo. Mover para junto dos demais imports.

### Step 2: Atualizar `passo_4/scanner_holerites.py` para ignorar pastas `validacao_*`

Localizar o bloco que ignora resultados anteriores (linha ~482):

```python
        if any(pasta.startswith(p) for p in ("scanner_", "auditoria_")):
            continue
```

Atualizar para:

```python
        if any(pasta.startswith(p) for p in ("scanner_", "auditoria_", "validacao_")):
            continue
```

### Step 3: Testar pipeline completo offline

Verificar que os três scripts passam no teste de sintaxe:

```bash
cd C:\Users\Auster\Documents\GitHub\scrapingSenior
python -c "
import ast, sys

for f in ['passo_4/scanner_holerites.py', 'passo_5/validador_esocial.py', 'passo_6/corretor.py']:
    with open(f, encoding='utf-8') as fh:
        ast.parse(fh.read())
    print(f'OK: {f}')
"
```

Esperado: 3 linhas `OK`.

### Step 4: Testar passo_4 completo (sem eSocial)

```bash
python passo_4/scanner_holerites.py
```

Verificar que:
- Gera `dados/saida/scanner_*.json`
- Cada colaborador tem campo `cpf` (pode ser `""` se não encontrado no PDF)

### Step 5: Commit final

```bash
git add passo_4/scanner_holerites.py passo_5/validador_esocial.py passo_6/corretor.py
git commit -m "fix: ajustes de integração entre passos 4, 5 e 6"
```

---

## Task 6: Atualizar memória e documentação

**Files:**
- Modify: `memory/MEMORY.md`

### Step 1: Atualizar MEMORY.md

Atualizar `C:\Users\Auster\.claude\projects\C--Users-Auster-Documents-GitHub-scrapingSenior\memory\MEMORY.md` para refletir a arquitetura final:

```markdown
## passo_5/validador_esocial.py
Valida eventos no eSocial a partir do scanner JSON.
- Importa cookie.py e parser.py do passo_3 via sys.path
- 1 id_rubrica por evento por empresa (para ao achar, vai pro próximo)
- Retomável com --retomar validacao_*.json
- Output: dados/saida/validacao_{timestamp}.json

## passo_6/corretor.py
Adaptação do passo_3/corretor.py para ler validacao_*.json.
- Lógica JNLP idêntica ao corretor original
- Entrada: validacao_*.json (o mais recente em dados/saida/)
```

### Step 2: Commit final de documentação

```bash
git add memory/ docs/
git commit -m "docs: atualiza memória e plano com arquitetura final dos passos 4-6"
```

---

## Resumo de Execução

```bash
# Passo 4 — Varrer holerites locais (sem internet)
python passo_4/scanner_holerites.py

# Passo 5 — Validar no eSocial (requer cookies.txt válido)
python passo_5/validador_esocial.py
# ou retomar:
python passo_5/validador_esocial.py --retomar dados/saida/validacao_*.json

# Passo 6 — Corrigir rubricas ERRADAS
python passo_6/corretor.py
# ou especificar arquivo:
python passo_6/corretor.py dados/saida/validacao_20260311_120000.json
```
