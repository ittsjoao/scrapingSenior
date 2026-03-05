# passo_2/criar_planilha.py
import os
import csv
import re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRADA_DIR = os.path.join(BASE_DIR, "dados", "entrada")
SAIDA_DIR   = os.path.join(BASE_DIR, "dados", "saida")
OUTPUT_PATH = os.path.join(BASE_DIR, "passo_2", "planilha_empresas.xlsx")


def ler_esocial():
    """Retorna lista de dicts na ordem do CSV."""
    path = os.path.join(ENTRADA_DIR, "esocial.csv")
    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if not row.get("id_evento", "").strip():
                continue
            rows.append({
                "id_evento":    int(row["id_evento"].strip()),
                "nome_esocial": row["nome_esocial"].strip(),
                "irf":          row["irf"].strip(),
                "tabela":       row["tabela"].strip(),
                "demissao":     row["demissão"].strip(),
            })
    return rows

def ler_eventos():
    """Retorna dict {id_evento (int): nome_evento (str)}."""
    path = os.path.join(ENTRADA_DIR, "eventos.csv")
    eventos = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if not row.get("id_evento", "").strip():
                continue
            eventos[int(row["id_evento"].strip())] = row["nome_evento"].strip()
    return eventos

def ler_empresas():
    """Retorna dict {nome_empresa (str): id_empresa (str)}."""
    path = os.path.join(ENTRADA_DIR, "empresas.csv")
    empresas = {}
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            nome = row.get("nome_empresa", "").strip()
            id_  = row.get("id_empresa", "").strip()
            if nome and id_:
                empresas[nome] = id_
    return empresas

def parsear_txt(path):
    pass

def gerar_excel(esocial_rows, eventos, empresas, pastas_existentes):
    pass

if __name__ == "__main__":
    esocial_rows       = ler_esocial()
    eventos            = ler_eventos()
    empresas           = ler_empresas()
    pastas_existentes  = sorted(os.listdir(SAIDA_DIR))
    gerar_excel(esocial_rows, eventos, empresas, pastas_existentes)
    print("Planilha gerada:", OUTPUT_PATH)
