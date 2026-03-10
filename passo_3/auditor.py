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
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    if retomar:
        return retomar
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(PASTA_SAIDA, f"auditoria_{ts}.json")


def _salvar(dados, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def _carregar_existente(caminho):
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _encontrar_mais_recente():
    arquivos = sorted(glob.glob(os.path.join(PASTA_SAIDA, "auditoria_*.json")))
    return arquivos[-1] if arquivos else None


def _rubrica_na(nome_evento, irrf_esperado, motivo, cpf=None, competencia=None, guid=None):
    return {
        "id_rubrica": None, "id_evento": None, "guid": guid,
        "nome_evento": nome_evento, "cpf": cpf, "competencia": competencia,
        "irrf_atual": None, "irrf_esperado": irrf_esperado,
        "campos_form": {}, "status": "N/A", "motivo": motivo,
    }


def auditar_empresa(session, guid, cpfs, eventos_ativos, eventos_demissao):
    """
    Itera CPFs × meses × eventos e retorna lista de dicts de rúbrica com status.
    """
    rubricas = []
    ev_por_nome = {ev["nome"]: ev for ev in eventos_ativos}

    # Eventos de demissão → N/A direto
    for ev in eventos_demissao:
        rubricas.append(_rubrica_na(ev["nome"], ev["irrf"], "demissão", guid=guid))

    # Busca códigos: CPF × mês até resolver todos os eventos ativos
    pendentes  = dict(ev_por_nome)
    encontrados = {}  # nome_evento → {codigo, cpf, mes}

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
        rubricas.append(_rubrica_na(nome, ev["irrf"], "não encontrado", guid=guid))

    # Valida IRRF para cada evento encontrado
    for nome, info in encontrados.items():
        ev     = ev_por_nome[nome]
        codigo = info["codigo"]
        cpf    = info["cpf"]
        mes    = info["mes"]

        if len(codigo) < 28:
            rubricas.append(_rubrica_na(nome, ev["irrf"], f"código curto: {codigo}", cpf, mes, guid))
            continue

        html_busca = buscar_rubrica(session, guid, codigo)
        if not html_busca:
            rubricas.append(_rubrica_na(nome, ev["irrf"], "buscar_rubrica falhou", cpf, mes, guid))
            continue

        id_rubrica, id_evento = parsear_busca_rubrica(html_busca)
        if not id_rubrica:
            rubricas.append(_rubrica_na(nome, ev["irrf"], "id_rubrica não encontrado", cpf, mes, guid))
            continue

        html_edicao = abrir_edicao_rubrica(session, id_rubrica, id_evento, guid)
        if not html_edicao:
            rubricas.append({
                "id_rubrica": id_rubrica, "id_evento": id_evento, "guid": guid,
                "nome_evento": nome, "cpf": cpf, "competencia": mes,
                "irrf_atual": None, "irrf_esperado": ev["irrf"],
                "campos_form": {}, "status": "N/A", "motivo": "abrir_edicao falhou",
            })
            continue

        campos = parsear_form_edicao(html_edicao)
        if not campos:
            rubricas.append({
                "id_rubrica": id_rubrica, "id_evento": id_evento, "guid": guid,
                "nome_evento": nome, "cpf": cpf, "competencia": mes,
                "irrf_atual": None, "irrf_esperado": ev["irrf"],
                "campos_form": {}, "status": "N/A", "motivo": "parsear_form falhou",
            })
            continue

        irrf_atual    = str(campos.get("DadosRubrica.CodigoIncidenciaIR", ""))
        irrf_esperado = str(ev["irrf"])
        status        = "CORRETO" if irrf_atual == irrf_esperado else "ERRADO"

        print(f"  [{status}] {nome} | irrf_atual={irrf_atual} | irrf_esperado={irrf_esperado}")

        rubricas.append({
            "id_rubrica":    id_rubrica,
            "id_evento":     id_evento,
            "guid":          guid,
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
            print("  [!] GUID não encontrado")
            trocar_perfil(session, usuario_logado_procurador, cpf_procurador)
            continue

        print(f"  [GUID] {guid}")

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
