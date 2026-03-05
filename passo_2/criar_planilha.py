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
    pass

def ler_eventos():
    pass

def ler_empresas():
    pass

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
