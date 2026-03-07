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

linhas_resultado = []


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

def assinar_jnlp(session):
    """Acessa Assinadoc, baixa .jnlp e executa com javaws. Retorna True se sucesso."""
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
        resultado = subprocess.run(["javaws", caminho_jnlp], timeout=120, capture_output=True)
        if resultado.returncode == 0:
            print("  [javaws] Concluído com sucesso")
            return True
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
    session = requests.Session()
    cookies_base = ler_cookies(COOKIES_FILE)
    session.cookies.update(cookies_base)

    usuario_logado_procurador = cookies_base.get("UsuarioLogado", "")
    cpf_procurador = cookies_base.get("usuario_logado_ws", "")

    empresas, puladas = carregar_dados(PLANILHA_ENTRADA)

    for p in puladas:
        registrar(p["cnpj"], p["evento"], "", "", "", p["cpf"], p["competencia"], p["status"])

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

        cache_tabela = {}  # (cpf, competencia) → html
        pendentes = {chave: True for chave in dados["eventos"]}
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
                    cache_tabela[cache_key] = acessar_tabela_funcionário(session, cpf, competencia)

                html = cache_tabela[cache_key]
                if not html:
                    continue

                # Aproveita o HTML para resolver todos os eventos pendentes de uma vez
                for chave2 in dados["eventos"]:
                    if not pendentes[chave2]:
                        continue
                    ev2, ev_aux2, _, tab2 = chave2
                    codigo = parsear_tabela_funcionario(html, ev2, ev_aux2, tab2)
                    if codigo:
                        pendentes[chave2] = False
                        encontrados[chave2] = {"codigo": codigo, "cpf": cpf, "competencia": competencia}

                if not pendentes[chave]:
                    break

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
                        cache_tabela[cache_key] = acessar_tabela_funcionário(session, cpf, mes)

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

            if len(codigo_rubrica) < 28:
                registrar(cnpj, evento, codigo_rubrica, "", "", cpf_encontrado, competencia_encontrada, "Rúbrica não é do domínio")
                continue

            html_busca = buscar_rubrica(session, guid, codigo_rubrica)
            if not html_busca:
                registrar(cnpj, evento, codigo_rubrica, "", "", cpf_encontrado, competencia_encontrada, "Não encontrado")
                continue

            id_rubrica, id_evento = parsear_busca_rubrica(html_busca)
            if not id_rubrica:
                registrar(cnpj, evento, codigo_rubrica, "", "", cpf_encontrado, competencia_encontrada, "Não encontrado")
                continue

            html_edicao = abrir_edicao_rubrica(session, id_rubrica, id_evento, guid)
            if not html_edicao:
                registrar(cnpj, evento, codigo_rubrica, "", "", cpf_encontrado, competencia_encontrada, "Não encontrado")
                continue

            campos = parsear_form_edicao(html_edicao)
            if not campos:
                registrar(cnpj, evento, codigo_rubrica, "", "", cpf_encontrado, competencia_encontrada, "Não encontrado")
                continue

            irrf_atual = campos.get("DadosRubrica.CodigoIncidenciaIR", "")

            if str(irrf_atual) == str(irrf_planilha):
                registrar(cnpj, evento, codigo_rubrica, irrf_atual, irrf_atual, cpf_encontrado, competencia_encontrada, "OK")
                continue

            campos["DadosRubrica.CodigoIncidenciaIR"] = irrf_planilha
            status_code, _ = salvar_edicao(session, id_rubrica, id_evento, campos)

            if status_code == 302:
                ok_jnlp = assinar_jnlp(session)
                status = "Atualizado" if ok_jnlp else "jnlp não assinado"
            else:
                print(f"  [!] POST salvar retornou {status_code} (esperado 302)")
                status = "jnlp não assinado"

            registrar(cnpj, evento, codigo_rubrica, irrf_atual, irrf_planilha, cpf_encontrado, competencia_encontrada, status)

        trocar_perfil(session, usuario_logado_procurador, cpf_procurador)

    salvar_planilha_resultado()


if __name__ == "__main__":
    main()
