#!/usr/bin/env python3
"""
corretor/corretor.py

Lê validacao_*.json gerado pelo validador e corrige rubricas com status='ERRADO'.

Uso:
  python corretor/corretor.py [validacao_*.json]
"""

import glob
import json
import os
import re
import subprocess
import sys
import tempfile
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
    acessar_assinadoc,
    abrir_edicao_rubrica,
    salvar_edicao,
    baixar_jnlp,
)
from parser import parsear_form_edicao, extrair_link_jnlp

BASE_DIR        = Path(__file__).parent.parent
COOKIES_FILE    = BASE_DIR / "lib" / "cookies.txt"
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
        d = re.sub(r"\D", "", cnpj)
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
    main()
