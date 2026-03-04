import os
from datetime import datetime
from config import PASTA_SAIDA, PASTA_LOGS


def sanitizar_nome(texto):
    """
    Remove caracteres inválidos para nomes de arquivo/pasta no Windows.
    Ex: "1/3 ABONO" vira "1-3 ABONO"
    """
    for char in r'<>:"/\|?*':
        texto = texto.replace(char, "-")
    return texto.strip()


def salvar_resultado(nome_empresa, id_empresa, id_evento, nome_evento, texto):
    """
    Salva o texto extraído pelo OCR em:
        dados/saida/<nome_empresa>/<id_evento>-<nome_evento>.txt

    Cada arquivo começa com um cabeçalho de identificação.
    """
    pasta_empresa = os.path.join(PASTA_SAIDA, sanitizar_nome(nome_empresa))
    os.makedirs(pasta_empresa, exist_ok=True)

    nome_arquivo = sanitizar_nome(f"{id_evento}-{nome_evento}") + ".txt"
    caminho      = os.path.join(pasta_empresa, nome_arquivo)

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(f"Empresa    : {nome_empresa}\n")
        f.write(f"ID Empresa : {id_empresa}\n")
        f.write(f"ID Evento  : {id_evento}\n")
        f.write(f"Evento     : {nome_evento}\n")
        f.write(f"Data       : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("-" * 50 + "\n")
        f.write(texto)

    print(f"  [OK] Salvo: {caminho}")


def registrar_log(mensagem):
    """
    Adiciona uma linha com timestamp ao arquivo logs/execucao.log.
    Também imprime no terminal.
    """
    os.makedirs(PASTA_LOGS, exist_ok=True)
    caminho_log = os.path.join(PASTA_LOGS, "execucao.log")

    linha = f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {mensagem}"

    with open(caminho_log, "a", encoding="utf-8") as f:
        f.write(linha + "\n")

    print(linha)
