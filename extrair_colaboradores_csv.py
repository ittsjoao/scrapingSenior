import csv
import os
import re

import pdfplumber

PASTA_SAIDA    = os.path.join("dados", "saida")
ARQUIVO_CSV    = os.path.join("dados", "colaboradores.csv")
ARQUIVO_EMPRESAS = os.path.join("dados", "entrada", "empresas.csv")

CPF_RE = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")


def sanitizar_nome(texto):
    for char in r'<>:"/\|?*':
        texto = texto.replace(char, "-")
    return texto.strip()


def carregar_cnpjs():
    """
    Lê empresas.csv e retorna dict {nome_pasta: cnpj}.
    A chave é o nome da empresa sanitizado (igual ao nome da pasta em dados/saida/).
    """
    mapa = {}
    with open(ARQUIVO_EMPRESAS, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            nome = sanitizar_nome(row["nome_empresa"].strip())
            cnpj = row.get("cnpj", "").strip()
            mapa[nome] = cnpj
    return mapa


def extrair_nome(pre_cpf):
    # Tudo antes do primeiro dígito (início do RG)
    match = re.match(r"^([^0-9]+?)(?=\s*\d)", pre_cpf)
    if not match:
        # Linha sem RG (ex: colaborador sem nº de RG cadastrado)
        match = re.match(r"^([^0-9]+)", pre_cpf)
    if not match:
        return ""
    nome = match.group(1)
    # Remove prefixo de estado + traço residual no final (ex: "MG-", "MG -", "SP-")
    nome = re.sub(r"(\s+[A-Z]{1,3}\s*-?\s*)+$", "", nome).strip()
    return nome


def extrair_colaboradores(caminho_pdf):
    colaboradores = []
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for linha in text.splitlines():
                    match_cpf = CPF_RE.search(linha)
                    if not match_cpf:
                        continue
                    cpf  = re.sub(r"[.\-]", "", match_cpf.group(0))
                    nome = extrair_nome(linha[: match_cpf.start()])
                    if nome:
                        colaboradores.append((nome, cpf))
    except Exception as e:
        print(f"  [ERRO ao ler] {caminho_pdf}: {e}")
    return colaboradores


def main():
    cnpj_por_empresa = carregar_cnpjs()
    todos = []

    for empresa in sorted(os.listdir(PASTA_SAIDA)):
        pasta_empresa = os.path.join(PASTA_SAIDA, empresa)
        if not os.path.isdir(pasta_empresa):
            continue

        pdf = next(
            (
                os.path.join(pasta_empresa, f)
                for f in os.listdir(pasta_empresa)
                if f.lower() == "colaboradores.pdf"
            ),
            None,
        )
        if not pdf:
            continue

        cnpj = cnpj_por_empresa.get(empresa, "")
        if not cnpj:
            print(f"  [AVISO] CNPJ não encontrado para: {empresa}")

        registros = extrair_colaboradores(pdf)
        print(f"{empresa}: {len(registros)} colaborador(es)")
        todos.extend((nome, cpf, cnpj) for nome, cpf in registros)

    os.makedirs(os.path.dirname(ARQUIVO_CSV), exist_ok=True)
    with open(ARQUIVO_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["colaborador", "cpf", "cnpj"])
        writer.writerows(todos)

    print(f"\nTotal: {len(todos)} registros -> {ARQUIVO_CSV}")


if __name__ == "__main__":
    main()
