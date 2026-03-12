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

BASE_DIR      = Path(__file__).parent.parent
DADOS_SAIDA   = BASE_DIR / "dados" / "saida"
DADOS_ENTRADA = BASE_DIR / "dados" / "entrada"
COOKIES_FILE  = BASE_DIR / "passo_3" / "cookies.txt"

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
    Retorna dict: id_evento → {nome_esocial, nome_esocial_aux, irrf, tabela}
    """
    mapa = {}
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
            if id_ev not in mapa:
                mapa[id_ev] = entrada
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
    # Formatar CNPJ: XX.XXX.XXX/XXXX-XX
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

    # 3. Montar conjunto de eventos pendentes (1 id_rubrica por evento por empresa)
    todos_eventos = set()
    for colab in empresa["colaboradores"]:
        for ev in colab["eventos"]:
            todos_eventos.add(ev)

    eventos_pendentes = deepcopy(todos_eventos)

    # 4. Iterar colaboradores até resolver todos os eventos pendentes
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

            nome_esocial  = info["nome_esocial"]
            nome_aux      = info["nome_esocial_aux"]
            tabela        = info["tabela"]
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
                "id_rubrica":        id_rubrica,
                "id_evento":         id_evento_rubrica,
                "guid":              guid,
                "nome_evento":       nome_esocial,
                "cpf_usado":         cpf,
                "competencia_usada": competencia,
                "irrf_atual":        irrf_atual,
                "irrf_esperado":     irrf_esperado,
                "campos_form":       campos or {},
                "status":            status,
            })

            eventos_resolvidos.append(id_ev)
            print(
                f"  [{'OK' if status == 'CORRETO' else 'ERRADO'}] "
                f"evento {id_ev} | irrf {irrf_atual} vs {irrf_esperado}"
            )

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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

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
