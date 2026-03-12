#!/usr/bin/env python3
"""
validador/validador_esocial.py

Para cada empresa do scanner JSON:
  - Acessa o eSocial e busca 1 id_rubrica por evento (o primeiro que achar)
  - Compara irrf_atual vs irrf_esperado
  - Salva validacao_TIMESTAMP.json (retomável com --retomar)

Uso:
  # Worker único (cookie padrão: lib/cookies.txt)
  python validador/validador_esocial.py [scanner_*.json] [--retomar validacao_*.json]

  # Múltiplos workers — um --cookies por worker
  python validador/validador_esocial.py scanner.json --cookies lib/c1.txt --cookies lib/c2.txt
"""

import sys
import os
import glob
import json
import csv
import re
import time
import multiprocessing
from datetime import datetime
from pathlib import Path

import requests

# Importar módulos compartilhados de lib/
_LIB = str(Path(__file__).parent.parent / "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

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

BASE_DIR      = Path(__file__).parent.parent
DADOS_SAIDA   = Path(os.environ.get("DADOS_SAIDA",   BASE_DIR / "dados" / "saida"))
DADOS_ENTRADA = Path(os.environ.get("DADOS_ENTRADA", BASE_DIR / "dados" / "entrada"))
COOKIES_FILE  = Path(os.environ.get("COOKIES_FILE",  BASE_DIR / "lib" / "cookies.txt"))

MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Helpers de I/O
# ---------------------------------------------------------------------------

def _json_mais_recente(prefixo: str) -> str | None:
    arquivos = sorted(glob.glob(str(DADOS_SAIDA / f"{prefixo}_*.json")))
    return arquivos[-1] if arquivos else None


def _carregar_json(caminho: str) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _salvar_json(dados: dict, caminho: str) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Carregamento de dados de entrada
# ---------------------------------------------------------------------------

def carregar_esocial_map() -> dict:
    """
    Retorna dict: id_evento → list[{nome_esocial, nome_esocial_aux, irrf, tabela}]

    Eventos com múltiplas linhas (ex: id 136 com tabelas Holerite e Férias)
    ficam como lista — o validador itera todas as entradas de cada evento.
    """
    mapa: dict = {}
    caminho = DADOS_ENTRADA / "esocial.csv"
    with open(caminho, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            id_ev = row["id_evento"].strip()
            entrada = {
                "nome_esocial":     row["nome_esocial"].strip(),
                "nome_esocial_aux": row["nome_esocial_aux"].strip(),
                "irrf":             row["irrf"].strip(),
                "tabela":           row["tabela"].strip(),
            }
            mapa.setdefault(id_ev, []).append(entrada)
    return mapa


# ---------------------------------------------------------------------------
# Lógica de validação por empresa
# ---------------------------------------------------------------------------

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
    cnpj_fmt = (
        f"{cnpj_digits[:2]}.{cnpj_digits[2:5]}.{cnpj_digits[5:8]}"
        f"/{cnpj_digits[8:12]}-{cnpj_digits[12:]}"
    )

    resultado = {
        "nome":            empresa["nome_empresa"],
        "guid":            None,
        "auditado_em":     None,
        "rubricas":        [],
        "nao_encontrados": [],
        "alertas":         [],
    }

    # 1. Selecionar empresa no eSocial
    ok = selecionar_empresa(session, cnpj_fmt)
    if not ok:
        resultado["alertas"].append(f"Falha ao selecionar empresa {cnpj_fmt}")
        resultado["auditado_em"] = datetime.now().isoformat()
        trocar_perfil(session, usuario_logado_proc, cpf_proc)
        return resultado

    # 2. Obter GUID
    html_home = acessar_home_empresa(session)
    if not html_home:
        resultado["alertas"].append("Home da empresa não acessível")
        resultado["auditado_em"] = datetime.now().isoformat()
        trocar_perfil(session, usuario_logado_proc, cpf_proc)
        return resultado

    guid = extrair_guid_home(html_home)
    if not guid:
        resultado["alertas"].append("GUID não encontrado na home")
        resultado["auditado_em"] = datetime.now().isoformat()
        trocar_perfil(session, usuario_logado_proc, cpf_proc)
        return resultado

    resultado["guid"] = guid

    # 3. Montar entradas pendentes: uma por linha do esocial.csv para cada evento
    #    encontrado nos holerites desta empresa.
    todos_eventos: set = set()
    for colab in empresa["colaboradores"]:
        for ev in colab["eventos"]:
            todos_eventos.add(ev)

    entradas_pendentes: list = []
    for id_ev in todos_eventos:
        for info in esocial_map.get(id_ev, []):
            entradas_pendentes.append((id_ev, info))

    # 4. Iterar colaboradores até resolver todas as entradas pendentes
    for colab in empresa["colaboradores"]:
        if not entradas_pendentes:
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

        # Buscar todas as entradas pendentes nesta tabela
        indices_resolvidos = []
        for idx, (id_ev, info) in enumerate(entradas_pendentes):
            nome_esocial  = info["nome_esocial"]
            nome_aux      = info["nome_esocial_aux"]
            tabela        = info["tabela"]
            irrf_esperado = info["irrf"]

            codigo = parsear_tabela_funcionario(html_tabela, nome_esocial, nome_aux, tabela)
            if not codigo:
                continue

            html_busca = buscar_rubrica(session, guid, codigo)
            if not html_busca:
                continue

            id_rubrica, id_evento_rubrica = parsear_busca_rubrica(html_busca)
            if not id_rubrica:
                continue

            html_edicao = abrir_edicao_rubrica(session, id_rubrica, id_evento_rubrica, guid)
            if not html_edicao:
                continue

            campos = parsear_form_edicao(html_edicao)
            irrf_atual = str(campos.get("DadosRubrica.CodigoIncidenciaIR", "")) if campos else ""
            status = "CORRETO" if irrf_atual == irrf_esperado else "ERRADO"

            resultado["rubricas"].append({
                "id_rubrica":        id_rubrica,
                "id_evento":         id_evento_rubrica,
                "guid":              guid,
                "nome_evento":       nome_esocial,
                "tabela":            tabela,
                "cpf_usado":         cpf,
                "competencia_usada": competencia,
                "irrf_atual":        irrf_atual,
                "irrf_esperado":     irrf_esperado,
                "campos_form":       campos or {},
                "status":            status,
            })

            indices_resolvidos.append(idx)
            print(
                f"  [{'OK' if status == 'CORRETO' else 'ERRADO'}] "
                f"evento {id_ev} ({tabela}) | irrf {irrf_atual} vs {irrf_esperado}"
            )

        for idx in reversed(indices_resolvidos):
            entradas_pendentes.pop(idx)

    # 5. Registrar não encontrados
    for id_ev, info in entradas_pendentes:
        chave = f"{id_ev} ({info['tabela']})"
        resultado["nao_encontrados"].append(chave)
        resultado["alertas"].append(
            f"Evento {chave} encontrado no holerite mas não localizado no eSocial"
        )

    resultado["auditado_em"] = datetime.now().isoformat()

    trocar_perfil(session, usuario_logado_proc, cpf_proc)
    return resultado


# ---------------------------------------------------------------------------
# Worker (multiprocessing)
# ---------------------------------------------------------------------------

def _worker(
    worker_index: int,
    n_workers: int,
    empresas: list,
    cookie_file: str,
    esocial_map: dict,
    output_path: str,
    shared_times,
    shared_pause_until,
    shared_req_count,
    shared_lock,
    file_lock,
):
    """Executado por cada processo worker. Configura o throttle compartilhado e processa sua fatia."""
    # Garantir lib no path (necessário no Windows com spawn)
    if _LIB not in sys.path:
        sys.path.insert(0, _LIB)

    # Conectar o throttle do módulo cookie ao estado compartilhado entre processos
    import cookie as _cookie_mod
    _cookie_mod._throttle.configurar_compartilhado(
        shared_times, shared_pause_until, worker_index, n_workers,
        shared_req_count, shared_lock,
    )

    session = requests.Session()
    cookies_base = ler_cookies(cookie_file)
    session.cookies.update(cookies_base)
    usuario_logado_proc = cookies_base.get("UsuarioLogado", "")
    cpf_proc = cookies_base.get("usuario_logado_ws", "")

    total = len(empresas)
    for i, empresa in enumerate(empresas, 1):
        cnpj = empresa["cnpj"]
        print(
            f"[W{worker_index}][{i}/{total}] {empresa['nome_empresa']} | CNPJ: {cnpj}",
            flush=True,
        )

        resultado = validar_empresa(
            session, empresa, esocial_map, usuario_logado_proc, cpf_proc
        )

        # Escrita thread-safe: lê → atualiza → salva
        with file_lock:
            validacao = _carregar_json(output_path)
            validacao[cnpj] = resultado
            _salvar_json(validacao, output_path)

    print(f"[W{worker_index}] Concluído ({total} empresas).", flush=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    # --retomar
    retomar_path = None
    if "--retomar" in args:
        idx = args.index("--retomar")
        retomar_path = args[idx + 1] if idx + 1 < len(args) else _json_mais_recente("validacao")
        args = [a for i, a in enumerate(args) if i != idx and i != idx + 1]

    # --cookies (pode aparecer múltiplas vezes, uma por worker)
    cookie_files = []
    filtered = []
    i = 0
    while i < len(args):
        if args[i] == "--cookies" and i + 1 < len(args):
            cookie_files.append(args[i + 1])
            i += 2
        else:
            filtered.append(args[i])
            i += 1
    args = filtered

    if not cookie_files:
        cookie_files = [str(COOKIES_FILE)]

    n_workers = len(cookie_files)

    # Scanner JSON
    scanner_path = args[0] if args else _json_mais_recente("scanner")
    if not scanner_path:
        print("[ERRO] Nenhum scanner_*.json encontrado em dados/saida/")
        sys.exit(1)
    print(f"[Scanner] {scanner_path}")

    scanner = _carregar_json(scanner_path)

    # Carregar ou inicializar JSON de validação
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if retomar_path:
        validacao_base = _carregar_json(retomar_path)
        output_path = retomar_path
        print(f"[Retomando] {retomar_path}")
    else:
        validacao_base = {}
        output_path = str(DADOS_SAIDA / f"validacao_{timestamp}.json")

    esocial_map = carregar_esocial_map()

    # Filtrar empresas já processadas
    empresas = [
        e for e in scanner.values()
        if not validacao_base.get(e["cnpj"], {}).get("auditado_em")
    ]
    ja_processadas = len(scanner) - len(empresas)

    print(f"[Info] {n_workers} worker(s) | {len(empresas)} empresas a processar", end="")
    if ja_processadas:
        print(f" ({ja_processadas} já processadas, pulando)", end="")
    print()
    print(f"[Output] {output_path}")

    # Inicializar arquivo de saída com o estado base
    _salvar_json(validacao_base, output_path)

    if n_workers == 1:
        # Modo single — sem overhead de multiprocessing
        session = requests.Session()
        cookies_base = ler_cookies(cookie_files[0])
        session.cookies.update(cookies_base)
        usuario_logado_proc = cookies_base.get("UsuarioLogado", "")
        cpf_proc = cookies_base.get("usuario_logado_ws", "")

        total = len(empresas)
        for i, empresa in enumerate(empresas, 1):
            print(f"\n[{i}/{total}] {empresa['nome_empresa']} | CNPJ: {empresa['cnpj']}")
            resultado = validar_empresa(
                session, empresa, esocial_map, usuario_logado_proc, cpf_proc
            )
            validacao_base[empresa["cnpj"]] = resultado
            _salvar_json(validacao_base, output_path)
    else:
        # Distribuir empresas em round-robin entre workers
        fatias: list[list] = [[] for _ in range(n_workers)]
        for idx, empresa in enumerate(empresas):
            fatias[idx % n_workers].append(empresa)

        for idx, (fatia, cookie) in enumerate(zip(fatias, cookie_files)):
            print(f"  Worker {idx}: {len(fatia)} empresas | cookie: {Path(cookie).name}")

        # Estado compartilhado para o Throttle (coordena pausas entre workers)
        shared_times       = multiprocessing.Array("d", [0.0] * n_workers)
        shared_pause_until = multiprocessing.Value("d", 0.0)
        shared_req_count   = multiprocessing.Value("i", 0)
        shared_lock        = multiprocessing.Lock()
        file_lock          = multiprocessing.Lock()

        processos = [
            multiprocessing.Process(
                target=_worker,
                args=(
                    idx, n_workers, fatias[idx], cookie_files[idx], esocial_map,
                    output_path, shared_times, shared_pause_until,
                    shared_req_count, shared_lock, file_lock,
                ),
            )
            for idx in range(n_workers)
        ]

        for p in processos:
            p.start()
        for p in processos:
            p.join()

    print(f"\n[FIM] Validação salva em: {output_path}")


if __name__ == "__main__":
    main()
