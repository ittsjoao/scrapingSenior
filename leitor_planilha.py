import csv
from config import ARQUIVO_EMPRESAS, ARQUIVO_EVENTOS


def carregar_empresas():
    """
    Lê empresas.csv e retorna lista de dicionários:
        [{"nome_empresa": "AGRO-S LTDA", "id_empresa": "183"}, ...]
    """
    return _ler_csv(ARQUIVO_EMPRESAS)


def carregar_eventos():
    """
    Lê eventos.csv e retorna lista de dicionários:
        [{"id_evento": "216", "nome_evento": "MÉDIAS VARIAVEIS 13°..."}, ...]
    """
    return _ler_csv(ARQUIVO_EVENTOS)


def _ler_csv(caminho):
    """Lê qualquer CSV com separador ";" e retorna lista de dicionários."""
    registros = []

    # utf-8-sig suporta UTF-8 com ou sem BOM (marca invisível de alguns editores)
    with open(caminho, encoding="utf-8-sig") as f:
        leitor = csv.DictReader(f, delimiter=";")
        for linha in leitor:
            # Remove espaços extras de cada valor
            registros.append({chave: valor.strip() for chave, valor in linha.items()})

    print(f"Carregado: {len(registros)} linha(s) de '{caminho}'")
    return registros
