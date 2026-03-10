# passo_3/auditor_parallel.py
import glob
import json
import multiprocessing
import os
import sys
from datetime import datetime

import requests

from cookie import (
    ler_cookies,
    selecionar_empresa,
    trocar_perfil,
    extrair_nome_empresa,
    acessar_home_empresa,
)
from parser import extrair_guid_home
from entradas import carregar_empresas, carregar_eventos
from auditor import auditar_empresa, PASTA_SAIDA

COOKIES_DIR = os.path.join(os.path.dirname(__file__), "cookies")


def _encontrar_cookies():
    """Retorna lista ordenada de worker_*.txt em passo_3/cookies/."""
    return sorted(glob.glob(os.path.join(COOKIES_DIR, "worker_*.txt")))


def _encontrar_json_mais_recente():
    arquivos = sorted(glob.glob(os.path.join(PASTA_SAIDA, "auditoria_*.json")))
    return arquivos[-1] if arquivos else None


def _caminho_saida(retomar=None):
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    if retomar:
        return retomar
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(PASTA_SAIDA, f"auditoria_{ts}.json")


def _ler_json(caminho):
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _salvar_json(dados, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def worker(worker_id, cookies_path, queue, lock, json_path, eventos_ativos, eventos_demissao, empresas):
    """
    Processo filho.
    Consome CNPJs da fila, audita cada empresa e salva no JSON compartilhado.
    """
    print(f"[W{worker_id}] Iniciando | cookies: {os.path.basename(cookies_path)}", flush=True)

    session = requests.Session()
    cookies_base = ler_cookies(cookies_path)
    session.cookies.update(cookies_base)

    usuario_logado_procurador = cookies_base.get("UsuarioLogado", "")
    cpf_procurador            = cookies_base.get("usuario_logado_ws", "")

    while True:
        try:
            cnpj = queue.get_nowait()
        except Exception:
            break

        # Verifica se já auditado — dentro do lock para evitar race condition
        with lock:
            dados = _ler_json(json_path)
            if cnpj in dados:
                print(f"[W{worker_id}] [SKIP] {cnpj}", flush=True)
                continue

        print(f"[W{worker_id}] {'='*50}", flush=True)
        print(f"[W{worker_id}] [EMPRESA] {cnpj}", flush=True)

        cpfs = empresas.get(cnpj, [])

        ok = selecionar_empresa(session, cnpj)
        if not ok:
            print(f"[W{worker_id}] [!] Falha ao selecionar {cnpj}", flush=True)
            trocar_perfil(session, usuario_logado_procurador, cpf_procurador)
            continue

        nome      = extrair_nome_empresa(session)
        html_home = acessar_home_empresa(session)
        guid      = extrair_guid_home(html_home) if html_home else None
        if not guid:
            print(f"[W{worker_id}] [!] GUID não encontrado para {cnpj}", flush=True)
            trocar_perfil(session, usuario_logado_procurador, cpf_procurador)
            continue

        print(f"[W{worker_id}] [Nome] {nome} | [GUID] {guid}", flush=True)

        # Auditoria ocorre FORA do lock — workers rodam em paralelo aqui
        rubricas = auditar_empresa(session, guid, cpfs, eventos_ativos, eventos_demissao)

        # Salva resultado — dentro do lock (~50ms)
        with lock:
            dados = _ler_json(json_path)
            dados[cnpj] = {
                "nome":        nome,
                "worker":      worker_id,
                "auditado_em": datetime.now().isoformat(timespec="seconds"),
                "rubricas":    rubricas,
            }
            _salvar_json(dados, json_path)

        print(f"[W{worker_id}] [SALVO] {cnpj}", flush=True)
        trocar_perfil(session, usuario_logado_procurador, cpf_procurador)

    print(f"[W{worker_id}] Fila vazia — encerrando", flush=True)


def main():
    cookies_files = _encontrar_cookies()
    if not cookies_files:
        print(f"[!] Nenhum arquivo em {COOKIES_DIR}/worker_*.txt")
        print("    Exporte cookies do Firefox e salve como worker_1.txt, worker_2.txt, ...")
        sys.exit(1)

    n_workers = len(cookies_files)
    print(f"[PARALLEL] {n_workers} worker(s): {[os.path.basename(f) for f in cookies_files]}")

    retomar = None
    if "--retomar" in sys.argv:
        retomar = _encontrar_json_mais_recente()
        if retomar:
            print(f"[RESUME] Continuando: {retomar}")
        else:
            print("[RESUME] Nenhum arquivo encontrado, iniciando novo.")

    json_path = _caminho_saida(retomar)
    print(f"[JSON] {json_path}")

    if not os.path.exists(json_path):
        _salvar_json({}, json_path)

    empresas                         = carregar_empresas()
    eventos_ativos, eventos_demissao = carregar_eventos()

    queue = multiprocessing.Queue()
    for cnpj in empresas.keys():
        queue.put(cnpj)
    print(f"[PARALLEL] {queue.qsize()} CNPJs na fila")

    lock = multiprocessing.Lock()

    processos = []
    for i, cookies_path in enumerate(cookies_files, start=1):
        p = multiprocessing.Process(
            target=worker,
            args=(i, cookies_path, queue, lock, json_path,
                  eventos_ativos, eventos_demissao, empresas),
        )
        p.start()
        processos.append(p)
        print(f"[PARALLEL] Worker {i} iniciado (PID {p.pid})")

    for p in processos:
        p.join()

    dados   = _ler_json(json_path)
    total   = len(dados)
    erradas = sum(
        1 for e in dados.values()
        for r in e.get("rubricas", [])
        if r["status"] == "ERRADO"
    )
    corretas = sum(
        1 for e in dados.values()
        for r in e.get("rubricas", [])
        if r["status"] == "CORRETO"
    )
    print(f"\n[FIM] {total} empresas | {corretas} CORRETO | {erradas} ERRADO")
    print(f"[JSON] {json_path}")


if __name__ == "__main__":
    main()
