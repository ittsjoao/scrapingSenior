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

    # Ainda errado — aplica correção
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
            rubrica["status"] = corrigir_rubrica(session, rubrica)
            _salvar(dados, caminho)

        trocar_perfil(session, usuario_logado_procurador, cpf_procurador)

    print(f"\n[FIM] JSON atualizado: {caminho}")


if __name__ == "__main__":
    main()
