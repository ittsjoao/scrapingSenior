# passo_3/saida.py
import os
from datetime import datetime

import openpyxl
from bs4 import BeautifulSoup

_TS    = datetime.now().strftime("%Y%m%d_%H%M%S")
_PASTA = os.path.dirname(__file__)

ARQUIVO_DESCOBERTAS = os.path.join(_PASTA, f"log_descobertas_{_TS}.txt")
ARQUIVO_AJUSTES     = os.path.join(_PASTA, f"log_ajustes_{_TS}.txt")
ARQUIVO_PLANILHA    = os.path.join(_PASTA, f"resultado_{_TS}.xlsx")
PASTA_TABELAS = os.path.join(_PASTA, f"tabelas_{_TS}")

_ROTULOS_TABELA = {0: "HOLERITE", 1: "FÉRIAS"}


def _nome_seguro(texto):
    """Remove caracteres inválidos para nomes de arquivo/pasta."""
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in texto).strip()


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


def salvar_tabelas_validacao(html, nome_empresa, cpf, mes):
    """
    Salva as tabelas do HTML em PASTA_TABELAS/<empresa>/<cpf>.txt
    A 1ª tabela é rotulada HOLERITE, a 2ª é FÉRIAS.
    Cada mês é anexado ao mesmo arquivo do colaborador.
    No terminal exibe apenas: CPF | MÊS | TABELA | N rúbricas
    """
    soup    = BeautifulSoup(html, "lxml")
    tabelas = soup.find_all("table", class_=lambda c: c and "sem-paginacao" in c)

    if not tabelas:
        return

    pasta_empresa = os.path.join(PASTA_TABELAS, _nome_seguro(nome_empresa))
    os.makedirs(pasta_empresa, exist_ok=True)

    caminho = os.path.join(pasta_empresa, f"{cpf}.txt")

    with open(caminho, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*70}\nMÊS: {mes}\n{'='*70}\n")

        for i, tabela in enumerate(tabelas):
            rotulo = _ROTULOS_TABELA.get(i, f"TABELA {i+1}")
            linhas_dados = tabela.find_all("tr")[1:]  # exclui cabeçalho
            total = len(linhas_dados)

            print(f"  CPF {cpf} | {mes} | {rotulo} | {total} rúbricas")

            f.write(f"\n--- {rotulo} ---\n")
            # cabeçalho
            cabecalho_tr = tabela.find("tr")
            if cabecalho_tr:
                cols = [td.get_text(strip=True) for td in cabecalho_tr.find_all(["th", "td"])]
                f.write(" | ".join(cols) + "\n")
            for tr in linhas_dados:
                cols = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
                f.write(" | ".join(cols) + "\n")


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
