# passo_3/entradas.py
import csv
import os

CAMINHO_CNPJ_CPF = os.path.join(os.path.dirname(__file__), "..", "dados", "entrada", "cnpj_cpf.csv")
CAMINHO_ESOCIAL  = os.path.join(os.path.dirname(__file__), "..", "dados", "entrada", "esocial.csv")


def carregar_empresas():
    """
    Lê cnpj_cpf.csv (colunas: cnpj;cpf) e retorna dict {cnpj: [cpf1, cpf2, ...]}.
    CPFs duplicados por CNPJ são ignorados.
    """
    empresas = {}
    with open(CAMINHO_CNPJ_CPF, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            cnpj = row["cnpj"].strip()
            cpf  = row["cpf"].strip()
            if cnpj not in empresas:
                empresas[cnpj] = []
            if cpf not in empresas[cnpj]:
                empresas[cnpj].append(cpf)
    return empresas


def carregar_eventos():
    """
    Lê esocial.csv e retorna (eventos_ativos, eventos_demissao).

    eventos_ativos:  lista de dicts para eventos onde demissão=Não
    eventos_demissao: lista de dicts para eventos onde demissão=Sim

    Cada dict: {"nome": str, "aux": str, "irrf": str, "tabela": str}
    """
    ativos   = []
    demissao = []
    with open(CAMINHO_ESOCIAL, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            evento = {
                "nome":   row["nome_esocial"].strip(),
                "aux":    row["nome_esocial_aux"].strip(),
                "irrf":   row["irrf"].strip(),
                "tabela": row["tabela"].strip(),
            }
            if row["demissão"].strip().lower() == "sim":
                demissao.append(evento)
            else:
                ativos.append(evento)
    return ativos, demissao
