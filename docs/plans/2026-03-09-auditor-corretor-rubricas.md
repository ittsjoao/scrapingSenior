# Auditor + Corretor de Rúbricas — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Criar dois scripts independentes: `auditor.py` (escaneia e classifica rúbricas em CORRETO/ERRADO/N/A, salva JSON) e `corretor.py` (lê JSON, re-verifica e corrige apenas as ERRADAS).

**Architecture:** Dois scripts em `passo_3/` que reutilizam `cookie.py`, `parser.py`, `entradas.py` sem modificá-los. JSON intermediário em `dados/saida/auditoria_TIMESTAMP.json` com chave por CNPJ. Auditor tem resume por CNPJ; corretor re-abre form antes de salvar (evita sobrescrever valor já corrigido).

**Tech Stack:** Python 3, requests, BeautifulSoup4 (bs4/lxml), subprocess (javaws), json, glob, sys

---

### Task 1: Criar `passo_3/auditor.py`

**Files:**
- Create: `passo_3/auditor.py`

**Step 1: Confirmar estrutura do diretório de saída**

```bash
ls dados/saida 2>/dev/null || echo "criar"
```

Se não existir, o script criará automaticamente.

**Step 2: Escrever `auditor.py`**

```python
# passo_3/auditor.py
import json
import os
import sys
import glob
from datetime import datetime

import requests

from cookie import (
    ler_cookies,
    selecionar_empresa,
    trocar_perfil,
    extrair_nome_empresa,
    acessar_home_empresa,
    acessar_lista_remuneracao,
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
from entradas import carregar_empresas, carregar_eventos

COOKIES_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")
PASTA_SAIDA  = os.path.join(os.path.dirname(__file__), "..", "dados", "saida")

MESES = [
    "202512", "202511", "202510", "202509", "202508", "202507",
    "202506", "202505", "202504", "202503", "202502", "202501",
    "202412", "202411",
]


def _caminho_saida(retomar=None):
    """Retorna caminho do JSON de saída. Se retomar=caminho, usa esse arquivo."""
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    if retomar:
        return retomar
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(PASTA_SAIDA, f"auditoria_{ts}.json")


def _salvar(dados, caminho):
    """Salva JSON no disco (sobrescreve)."""
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def _carregar_existente(caminho):
    """Carrega JSON existente ou retorna dict vazio."""
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _encontrar_mais_recente():
    """Retorna o arquivo auditoria_*.json mais recente em dados/saida/, ou None."""
    arquivos = sorted(glob.glob(os.path.join(PASTA_SAIDA, "auditoria_*.json")))
    return arquivos[-1] if arquivos else None


def auditar_empresa(session, guid, cpfs, eventos_ativos, eventos_demissao):
    """
    Itera CPFs × meses × eventos e retorna lista de dicts de rúbrica com status.
    Cada dict: id_rubrica, id_evento, nome_evento, cpf, competencia,
               irrf_atual, irrf_esperado, campos_form, status
    """
    # Eventos de demissão → direto N/A
    rubricas = []
    for ev in eventos_demissao:
        rubricas.append({
            "id_rubrica": None, "id_evento": None,
            "nome_evento": ev["nome"], "cpf": None, "competencia": None,
            "irrf_atual": None, "irrf_esperado": ev["irrf"],
            "campos_form": {}, "status": "N/A",
            "motivo": "demissão",
        })

    pendentes = {ev["nome"]: ev for ev in eventos_ativos}
    encontrados = {}  # nome_evento → {codigo, cpf, mes}

    # Busca códigos: CPF × mês até resolver todos
    for cpf in cpfs:
        if not pendentes:
            break
        for mes in MESES:
            if not pendentes:
                break
            html_lista = acessar_lista_remuneracao(session, mes, guid)
            if not html_lista:
                continue
            html = acessar_tabela_funcionário(session, cpf, mes, guid)
            if not html:
                continue
            for nome, ev in list(pendentes.items()):
                codigo = parsear_tabela_funcionario(html, ev["nome"], ev["aux"], ev["tabela"])
                if codigo:
                    encontrados[nome] = {"codigo": codigo, "cpf": cpf, "mes": mes}
                    del pendentes[nome]
                    print(f"  [ENCONTRADO] {nome} → {codigo} | CPF {cpf} | {mes}")

    # Eventos não encontrados → N/A
    for nome, ev in pendentes.items():
        rubricas.append({
            "id_rubrica": None, "id_evento": None,
            "nome_evento": nome, "cpf": None, "competencia": None,
            "irrf_atual": None, "irrf_esperado": ev["irrf"],
            "campos_form": {}, "status": "N/A",
            "motivo": "não encontrado",
        })

    # Valida IRRF para eventos encontrados
    for nome, info in encontrados.items():
        ev     = {e["nome"]: e for e in eventos_ativos}[nome]
        codigo = info["codigo"]
        cpf    = info["cpf"]
        mes    = info["mes"]

        if len(codigo) < 28:
            rubricas.append({
                "id_rubrica": None, "id_evento": None,
                "nome_evento": nome, "cpf": cpf, "competencia": mes,
                "irrf_atual": None, "irrf_esperado": ev["irrf"],
                "campos_form": {}, "status": "N/A",
                "motivo": f"código curto: {codigo}",
            })
            continue

        html_busca = buscar_rubrica(session, guid, codigo)
        if not html_busca:
            rubricas.append({
                "id_rubrica": None, "id_evento": None,
                "nome_evento": nome, "cpf": cpf, "competencia": mes,
                "irrf_atual": None, "irrf_esperado": ev["irrf"],
                "campos_form": {}, "status": "N/A",
                "motivo": "buscar_rubrica falhou",
            })
            continue

        id_rubrica, id_evento = parsear_busca_rubrica(html_busca)
        if not id_rubrica:
            rubricas.append({
                "id_rubrica": None, "id_evento": None,
                "nome_evento": nome, "cpf": cpf, "competencia": mes,
                "irrf_atual": None, "irrf_esperado": ev["irrf"],
                "campos_form": {}, "status": "N/A",
                "motivo": "id_rubrica não encontrado",
            })
            continue

        html_edicao = abrir_edicao_rubrica(session, id_rubrica, id_evento, guid)
        if not html_edicao:
            rubricas.append({
                "id_rubrica": id_rubrica, "id_evento": id_evento,
                "nome_evento": nome, "cpf": cpf, "competencia": mes,
                "irrf_atual": None, "irrf_esperado": ev["irrf"],
                "campos_form": {}, "status": "N/A",
                "motivo": "abrir_edicao falhou",
            })
            continue

        campos = parsear_form_edicao(html_edicao)
        if not campos:
            rubricas.append({
                "id_rubrica": id_rubrica, "id_evento": id_evento,
                "nome_evento": nome, "cpf": cpf, "competencia": mes,
                "irrf_atual": None, "irrf_esperado": ev["irrf"],
                "campos_form": {}, "status": "N/A",
                "motivo": "parsear_form falhou",
            })
            continue

        irrf_atual    = str(campos.get("DadosRubrica.CodigoIncidenciaIR", ""))
        irrf_esperado = str(ev["irrf"])
        status        = "CORRETO" if irrf_atual == irrf_esperado else "ERRADO"

        print(f"  [{status}] {nome} | irrf_atual={irrf_atual} | irrf_esperado={irrf_esperado}")

        rubricas.append({
            "id_rubrica":    id_rubrica,
            "id_evento":     id_evento,
            "nome_evento":   nome,
            "cpf":           cpf,
            "competencia":   mes,
            "irrf_atual":    irrf_atual,
            "irrf_esperado": irrf_esperado,
            "campos_form":   campos,
            "status":        status,
        })

    return rubricas


def main():
    # Detecta flag --retomar para continuar arquivo existente
    retomar = None
    if "--retomar" in sys.argv:
        retomar = _encontrar_mais_recente()
        if retomar:
            print(f"[RESUME] Continuando: {retomar}")
        else:
            print("[RESUME] Nenhum arquivo encontrado, iniciando novo.")

    caminho = _caminho_saida(retomar)
    dados   = _carregar_existente(caminho)
    ja_auditados = set(dados.keys())
    print(f"[JSON] {caminho}")
    print(f"[RESUME] CNPJs já auditados: {len(ja_auditados)}")

    session = requests.Session()
    cookies_base = ler_cookies(COOKIES_FILE)
    session.cookies.update(cookies_base)

    usuario_logado_procurador = cookies_base.get("UsuarioLogado", "")
    cpf_procurador            = cookies_base.get("usuario_logado_ws", "")

    empresas                         = carregar_empresas()
    eventos_ativos, eventos_demissao = carregar_eventos()

    for cnpj, cpfs in empresas.items():
        print(f"\n{'='*60}")
        print(f"[EMPRESA] {cnpj}")

        if cnpj in ja_auditados:
            print("  [SKIP] já auditado")
            continue

        ok = selecionar_empresa(session, cnpj)
        if not ok:
            print(f"  [!] Falha ao selecionar {cnpj}")
            trocar_perfil(session, usuario_logado_procurador, cpf_procurador)
            continue

        nome = extrair_nome_empresa(session)
        print(f"  [Nome] {nome}")

        html_home = acessar_home_empresa(session)
        guid = extrair_guid_home(html_home) if html_home else None
        if not guid:
            print(f"  [!] GUID não encontrado")
            trocar_perfil(session, usuario_logado_procurador, cpf_procurador)
            continue

        rubricas = auditar_empresa(session, guid, cpfs, eventos_ativos, eventos_demissao)

        dados[cnpj] = {
            "nome":        nome,
            "auditado_em": datetime.now().isoformat(timespec="seconds"),
            "rubricas":    rubricas,
        }
        _salvar(dados, caminho)
        print(f"  [SALVO] {caminho}")

        trocar_perfil(session, usuario_logado_procurador, cpf_procurador)

    print(f"\n[FIM] Auditoria salva em: {caminho}")


if __name__ == "__main__":
    main()
```

**Step 3: Smoke test manual — uma única empresa**

Coloque apenas 1 CNPJ em `dados/entrada/cnpj_cpf.csv` e execute:
```bash
cd passo_3 && python auditor.py
```
Verifique:
- `dados/saida/auditoria_*.json` criado
- Empresa no JSON com campo `rubricas` não vazio
- Status CORRETO / ERRADO / N/A conforme esperado

**Step 4: Testar resume**

Adicione o CNPJ de volta ao CSV junto com um segundo CNPJ. Execute:
```bash
cd passo_3 && python auditor.py --retomar
```
Verifique que o primeiro CNPJ aparece como `[SKIP]` e o segundo é auditado.

**Step 5: Commit**

```bash
git add passo_3/auditor.py
git commit -m "feat(passo_3): add auditor.py — audit rubricas IRRF and save JSON"
```

---

### Task 2: Criar `passo_3/corretor.py`

**Files:**
- Create: `passo_3/corretor.py`

**Step 1: Escrever `corretor.py`**

```python
# passo_3/corretor.py
import glob
import json
import os
import subprocess
import sys
import tempfile

import requests

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

COOKIES_FILE    = os.path.join(os.path.dirname(__file__), "cookies.txt")
PASTA_SAIDA     = os.path.join(os.path.dirname(__file__), "..", "dados", "saida")
PASTA_TEMP_JNLP = os.path.join(tempfile.gettempdir(), "esocial_jnlp")


def _encontrar_json_mais_recente():
    arquivos = sorted(glob.glob(os.path.join(PASTA_SAIDA, "auditoria_*.json")))
    return arquivos[-1] if arquivos else None


def _carregar(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _salvar(dados, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


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


def corrigir_rubrica(session, rubrica):
    """
    Re-abre o formulário, verifica IRRF atual e corrige se ainda errado.
    Retorna novo status: CORRIGIDO | CORRIGIDO_EXTERNAMENTE | ERRO_FORM | ERRO_ASSINATURA
    """
    id_rubrica    = rubrica["id_rubrica"]
    id_evento     = rubrica["id_evento"]
    irrf_esperado = str(rubrica["irrf_esperado"])
    nome_evento   = rubrica["nome_evento"]

    # Re-abre form para verificar estado atual
    html_edicao = abrir_edicao_rubrica(session, id_rubrica, id_evento, guid=None)
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

    # Ainda errado — aplica correção
    campos["DadosRubrica.CodigoIncidenciaIR"] = irrf_esperado
    status_code, _ = salvar_edicao(session, id_rubrica, id_evento, campos)

    ok = assinar_jnlp(session) if status_code == 302 else False
    if ok:
        print(f"  [CORRIGIDO] {nome_evento} | {irrf_atual} → {irrf_esperado}")
        return "CORRIGIDO"
    else:
        print(f"  [!] {nome_evento} — assinatura falhou (status {status_code})")
        return "ERRO_ASSINATURA"


def main():
    # Determina caminho do JSON
    if len(sys.argv) > 1:
        caminho = sys.argv[1]
    else:
        caminho = _encontrar_json_mais_recente()
        if not caminho:
            print("[!] Nenhum arquivo auditoria_*.json encontrado em dados/saida/")
            sys.exit(1)
    print(f"[JSON] {caminho}")

    dados = _carregar(caminho)

    session = requests.Session()
    cookies_base = ler_cookies(COOKIES_FILE)
    session.cookies.update(cookies_base)

    usuario_logado_procurador = cookies_base.get("UsuarioLogado", "")
    cpf_procurador            = cookies_base.get("usuario_logado_ws", "")

    for cnpj, empresa in dados.items():
        erradas = [r for r in empresa["rubricas"] if r["status"] == "ERRADO"]
        if not erradas:
            continue

        print(f"\n{'='*60}")
        print(f"[EMPRESA] {cnpj} | {empresa['nome']} | {len(erradas)} rúbrica(s) ERRADA(s)")

        ok = selecionar_empresa(session, cnpj)
        if not ok:
            print(f"  [!] Falha ao selecionar {cnpj}")
            trocar_perfil(session, usuario_logado_procurador, cpf_procurador)
            continue

        for rubrica in erradas:
            novo_status = corrigir_rubrica(session, rubrica)
            rubrica["status"] = novo_status
            _salvar(dados, caminho)  # salva após cada rúbrica

        trocar_perfil(session, usuario_logado_procurador, cpf_procurador)

    print(f"\n[FIM] JSON atualizado: {caminho}")


if __name__ == "__main__":
    main()
```

**Nota sobre `abrir_edicao_rubrica`:** a função em `cookie.py` recebe `guid` mas usa apenas `id_rubrica` e `id_evento` na URL — passar `guid=None` é seguro. Confirme olhando `cookie.py:206-218` antes de executar.

**Step 2: Verificar assinatura da função `abrir_edicao_rubrica`**

Abra `passo_3/cookie.py` linha 206 e confirme que `guid` só é usado no `Referer` header, não na URL principal. Se for usado na URL, ajuste a chamada passando um valor válido (salvar o `guid` no JSON do auditor).

Se o guid for necessário: adicione `"guid": guid` em cada entrada de rúbrica no `auditor.py` (na função `auditar_empresa`, após obter o `guid`) e use `rubrica["guid"]` no `corretor.py`.

**Step 3: Smoke test manual**

Com o JSON gerado na Task 1 contendo pelo menos uma rúbrica `ERRADO`:
```bash
cd passo_3 && python corretor.py
```
Verifique:
- Empresa com `ERRADO` é processada
- Status no JSON muda para `CORRIGIDO` ou `CORRIGIDO_EXTERNAMENTE`
- Empresa sem `ERRADO` é pulada silenciosamente

Para passar caminho explícito:
```bash
cd passo_3 && python corretor.py ../dados/saida/auditoria_20260309_230000.json
```

**Step 4: Commit**

```bash
git add passo_3/corretor.py
git commit -m "feat(passo_3): add corretor.py — fix ERRADO rubricas from audit JSON"
```

---

### Task 3: Ajuste de guid no corretor (condicional)

> Execute esta task **somente se** o Step 2 da Task 2 revelar que `guid` é necessário na URL de `abrir_edicao_rubrica`.

**Files:**
- Modify: `passo_3/auditor.py`
- Modify: `passo_3/corretor.py`

**Step 1: Adicionar `guid` em cada rúbrica no auditor**

Em `auditor.py`, dentro de `auditar_empresa`, antes de montar cada `rubrica` dict, o `guid` já está disponível como parâmetro. Adicione `"guid": guid` em **todos** os dicts de rúbrica da lista `rubricas`.

**Step 2: Usar `rubrica["guid"]` no corretor**

Em `corretor.py`, em `corrigir_rubrica`, mude a chamada:
```python
# antes
html_edicao = abrir_edicao_rubrica(session, id_rubrica, id_evento, guid=None)
# depois
html_edicao = abrir_edicao_rubrica(session, id_rubrica, id_evento, rubrica["guid"])
```

E propague `rubrica` como único argumento (já é o caso).

**Step 3: Re-executar smoke test**

```bash
cd passo_3 && python auditor.py  # gera novo JSON com guid
cd passo_3 && python corretor.py  # usa guid do JSON
```

**Step 4: Commit**

```bash
git add passo_3/auditor.py passo_3/corretor.py
git commit -m "fix(passo_3): pass guid through audit JSON to corretor"
```
