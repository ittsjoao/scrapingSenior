# passo_3/saida.py
import os
from datetime import datetime

import openpyxl

_TS    = datetime.now().strftime("%Y%m%d_%H%M%S")
_PASTA = os.path.dirname(__file__)

ARQUIVO_DESCOBERTAS = os.path.join(_PASTA, f"log_descobertas_{_TS}.txt")
ARQUIVO_AJUSTES     = os.path.join(_PASTA, f"log_ajustes_{_TS}.txt")
ARQUIVO_PLANILHA    = os.path.join(_PASTA, f"resultado_{_TS}.xlsx")


def log_descoberta(nome_empresa, codigo_rubrica, cpf, irrf_ok):
    """
    Grava linha no log de descobertas.
    Formato: NOME EMPRESA (CODIGO - CPF) - IRRF CORRETO/INCORRETO
    """
    status = "IRRF CORRETO" if irrf_ok else "IRRF INCORRETO"
    linha  = f"{nome_empresa} ({codigo_rubrica} - {cpf}) - {status}\n"
    with open(ARQUIVO_DESCOBERTAS, "a", encoding="utf-8") as f:
        f.write(linha)
    print(f"  [log] {linha.strip()}")


def log_na(nome_empresa, nome_evento, motivo):
    """
    Grava linha N/A no log de descobertas.
    Formato: NOME EMPRESA | EVENTO - N/A (motivo)
    """
    linha = f"{nome_empresa} | {nome_evento} - N/A ({motivo})\n"
    with open(ARQUIVO_DESCOBERTAS, "a", encoding="utf-8") as f:
        f.write(linha)
    print(f"  [log] {linha.strip()}")


def log_ajuste(nome_empresa, nome_evento, irrf_antigo, irrf_novo):
    """
    Grava linha no log de ajustes.
    Formato: NOME EMPRESA | EVENTO | IRRF antigo: X → novo: Y
    """
    linha = f"{nome_empresa} | {nome_evento} | IRRF antigo: {irrf_antigo} → novo: {irrf_novo}\n"
    with open(ARQUIVO_AJUSTES, "a", encoding="utf-8") as f:
        f.write(linha)
    print(f"  [ajuste] {linha.strip()}")


def salvar_planilha(resultados, eventos_ativos, eventos_demissao):
    """
    Salva planilha Excel com uma linha por empresa e uma coluna por evento.

    resultados: lista de dicts:
        {"nome_empresa": str, "cnpj": str, "status_eventos": {nome_evento: str}}

    Valores possíveis por célula de evento:
        "RETIFICADO"     → rúbrica encontrada (IRRF correto ou corrigido)
        "N/A"            → rúbrica não encontrada
        "N/A (Demissão)" → evento ignorado por ser demissão
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultado"

    nomes_eventos = [e["nome"] for e in eventos_ativos] + [e["nome"] for e in eventos_demissao]
    ws.append(["EMPRESA", "CNPJ"] + nomes_eventos)

    for r in resultados:
        linha = [r["nome_empresa"], r["cnpj"]]
        for nome in nomes_eventos:
            linha.append(r["status_eventos"].get(nome, "N/A"))
        ws.append(linha)

    wb.save(ARQUIVO_PLANILHA)
    print(f"\n[Planilha salva] {ARQUIVO_PLANILHA}")
