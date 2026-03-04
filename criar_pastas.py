"""
Cria todas as pastas de saida para cada empresa do empresas.csv.
Execute antes do main.py sempre que adicionar novas empresas.

Uso:
    python criar_pastas.py
"""

import csv
import os
from config import ARQUIVO_EMPRESAS, PASTA_SAIDA


def sanitizar_nome(texto):
    for char in r'<>:"/\|?*':
        texto = texto.replace(char, "-")
    return texto.strip()


with open(ARQUIVO_EMPRESAS, encoding="utf-8-sig") as f:
    leitor = csv.DictReader(f, delimiter=";")
    empresas_vistas = set()

    for linha in leitor:
        nome = sanitizar_nome(linha["nome_empresa"].strip())

        if nome in empresas_vistas:
            continue
        empresas_vistas.add(nome)

        pasta = os.path.join(PASTA_SAIDA, nome)
        os.makedirs(pasta, exist_ok=True)
        print(f"Criada: {pasta}")

print(f"\n{len(empresas_vistas)} pasta(s) criada(s) em '{PASTA_SAIDA}'")
