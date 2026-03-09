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
    acessar_lista_remuneracao,
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
from saida import log_descoberta, log_na, log_ajuste, salvar_planilha, salvar_tabelas_validacao

# ── Configuração ───────────────────────────────────────────────────────────────

COOKIES_FILE    = os.path.join(os.path.dirname(__file__), "cookies.txt")
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


def buscar_codigos(session, cpfs, eventos_ativos, nome_empresa, guid):
    """
    Itera CPFs × meses até encontrar todos os eventos pendentes ou esgotar as opções.
    Para cada CPF: percorre meses 12/2025 → 11/2024 até resolver todos os eventos.

    Retorna dict: {nome_evento: {"codigo": str, "cpf": str, "mes": str}}
    """
    pendentes   = {e["nome"]: e for e in eventos_ativos}
    encontrados = {}

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
            salvar_tabelas_validacao(html, nome_empresa, cpf, mes)
            for nome, evento in list(pendentes.items()):
                codigo = parsear_tabela_funcionario(html, evento["nome"], evento["aux"], evento["tabela"])
                if codigo:
                    encontrados[nome] = {"codigo": codigo, "cpf": cpf, "mes": mes}
                    del pendentes[nome]
                    print(f"  [ENCONTRADO] CPF {cpf} | {mes} | {nome} → {codigo}")

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

    empresas                         = carregar_empresas()
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

        # ── Busca: mês × CPF até encontrar todos os eventos ──────────────
        encontrados = buscar_codigos(session, cpfs, eventos_ativos, nome_empresa, guid)

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
