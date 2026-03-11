# passo_3/auditor_parallel.py
import glob
import json
import multiprocessing
import os
import signal
import sys
from datetime import datetime

import requests

from cookie import (
    _throttle,
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


def _testar_sessao(worker_id, cookies_path):
    """
    Testa se a sessão do worker está ativa no portal eSocial.
    Retorna (ok: bool, motivo: str|None).
    """
    try:
        cookies_base = ler_cookies(cookies_path)
    except Exception as e:
        return False, f"erro ao ler arquivo: {e}"

    usuario = cookies_base.get("UsuarioLogado", "")
    if not usuario:
        return False, "cookie UsuarioLogado ausente"

    session = requests.Session()
    session.cookies.update(cookies_base)

    try:
        resp = session.get(
            "https://www.esocial.gov.br/portal/Home/Index",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"},
            allow_redirects=False,
            timeout=15,
        )
    except Exception as e:
        return False, f"erro de conexão: {e}"

    location = resp.headers.get("Location", "")
    if resp.status_code in (301, 302) and any(k in location for k in ("login", "Login", "Account")):
        return False, "sessão expirada (redirect para login)"

    if resp.status_code not in (200, 302):
        return False, f"status inesperado: {resp.status_code}"

    return True, None


def _validar_workers(cookies_files):
    """
    Testa todos os workers e solicita troca dos cookies inválidos.
    Loop até o usuário confirmar, pular inválidos ou cancelar.
    Retorna lista de cookies_files válidos.
    """
    while True:
        print("\n[CHECK] Testando conexão dos workers...")
        invalidos = []

        for i, path in enumerate(cookies_files, start=1):
            ok, motivo = _testar_sessao(i, path)
            status = "OK" if ok else f"FALHOU — {motivo}"
            print(f"  [W{i}] {os.path.basename(path)} — {status}")
            if not ok:
                invalidos.append(path)

        if not invalidos:
            print("[CHECK] Todos os workers OK.\n")
            return cookies_files

        print(f"\n[CHECK] {len(invalidos)} worker(s) com sessão inválida.")
        print("  [Enter] Substituí os cookies, testar novamente")
        print("  [s]     Ignorar inválidos e continuar com os válidos")
        print("  [q]     Cancelar")

        escolha = input(">> ").strip().lower()

        if escolha == "q":
            print("[!] Cancelado.")
            sys.exit(0)
        elif escolha == "s":
            invalidos_set = set(invalidos)
            validos = [p for p in cookies_files if p not in invalidos_set]
            if not validos:
                print("[!] Nenhum worker válido. Cancelando.")
                sys.exit(1)
            print(f"[CHECK] Continuando com {len(validos)} worker(s) válido(s).\n")
            return validos
        # [Enter] → re-testa (usuário já substituiu os arquivos)


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


def worker(worker_id, cookies_path, queue, lock, json_path, eventos_ativos, eventos_demissao, empresas, stop_event, shared_times, shared_pause_until, n_workers, shared_req_count, shared_req_lock):
    """
    Processo filho.
    Consome CNPJs da fila, audita cada empresa e salva no JSON compartilhado.
    Verifica stop_event antes de pegar o próximo CNPJ (pause gracioso via Ctrl+C).
    """
    # Workers ignoram SIGINT — o main cuida disso via stop_event
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # Configura throttle compartilhado (pausa coletiva + pausa periódica)
    _throttle.configurar_compartilhado(shared_times, shared_pause_until, worker_id - 1, n_workers, shared_req_count, shared_req_lock)

    print(f"[W{worker_id}] Iniciando | cookies: {os.path.basename(cookies_path)}", flush=True)

    session = requests.Session()
    cookies_base = ler_cookies(cookies_path)
    session.cookies.update(cookies_base)

    usuario_logado_procurador = cookies_base.get("UsuarioLogado", "")
    cpf_procurador            = cookies_base.get("usuario_logado_ws", "")

    while not stop_event.is_set():
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

        try:
            cpfs = empresas.get(cnpj, [])

            ok = selecionar_empresa(session, cnpj)
            if not ok:
                print(f"[W{worker_id}] [!] Falha ao selecionar {cnpj} — devolvendo à fila", flush=True)
                queue.put(cnpj)
                continue

            nome      = extrair_nome_empresa(session)
            html_home = acessar_home_empresa(session)
            guid      = extrair_guid_home(html_home) if html_home else None
            if not guid:
                print(f"[W{worker_id}] [!] GUID não encontrado para {cnpj} — devolvendo à fila", flush=True)
                queue.put(cnpj)
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

        except Exception as e:
            print(f"[W{worker_id}] [ERRO] {cnpj} — {e} — devolvendo à fila", flush=True)
            queue.put(cnpj)

    motivo = "PAUSA solicitada (Ctrl+C)" if stop_event.is_set() else "Fila vazia"
    print(f"[W{worker_id}] {motivo} — encerrando", flush=True)


def main():
    cookies_files = _encontrar_cookies()
    if not cookies_files:
        print(f"[!] Nenhum arquivo em {COOKIES_DIR}/worker_*.txt")
        print("    Exporte cookies do Firefox e salve como worker_1.txt, worker_2.txt, ...")
        sys.exit(1)

    n_workers = len(cookies_files)
    print(f"[PARALLEL] {n_workers} worker(s): {[os.path.basename(f) for f in cookies_files]}")

    cookies_files = _validar_workers(cookies_files)
    n_workers = len(cookies_files)

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
    stop_event = multiprocessing.Event()

    # Estado compartilhado entre workers
    shared_times = multiprocessing.Array("d", [0.0] * n_workers)   # tempo da última request por worker
    shared_pause_until = multiprocessing.Value("d", 0.0)            # timestamp até quando pausar
    shared_req_count = multiprocessing.Value("i", 0)                # contador global de requests
    shared_req_lock = multiprocessing.Lock()                        # lock para incremento atômico

    processos = []
    for i, cookies_path in enumerate(cookies_files, start=1):
        p = multiprocessing.Process(
            target=worker,
            args=(i, cookies_path, queue, lock, json_path,
                  eventos_ativos, eventos_demissao, empresas, stop_event,
                  shared_times, shared_pause_until, n_workers,
                  shared_req_count, shared_req_lock),
        )
        p.start()
        processos.append(p)
        print(f"[PARALLEL] Worker {i} iniciado (PID {p.pid})")

    print("[PARALLEL] Pressione Ctrl+C para pausar (workers terminam a empresa atual e param)")

    try:
        for p in processos:
            p.join()
    except KeyboardInterrupt:
        print("\n[PAUSA] Ctrl+C recebido — sinalizando workers para parar após empresa atual...")
        stop_event.set()
        for p in processos:
            p.join()

    dados   = _ler_json(json_path)
    total   = len(dados)
    faltam  = len(empresas) - total
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

    if stop_event.is_set():
        print(f"\n[PAUSADO] {total} empresas auditadas | {faltam} restantes")
        print(f"[PAUSADO] Para continuar: python auditor_parallel.py --retomar")
    else:
        print(f"\n[FIM] {total} empresas | {corretas} CORRETO | {erradas} ERRADO")
    print(f"[JSON] {json_path}")


if __name__ == "__main__":
    main()
