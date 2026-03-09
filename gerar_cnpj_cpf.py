"""
Lê dados/entrada/colaboradores.csv e gera dados/entrada/cnpj_cpf.csv
no formato cnpj;cpf.

Linhas cujo campo 'cnpj' não seja um CNPJ válido (14 dígitos numéricos)
são ignoradas e registradas no log.
"""

import csv
import os

ENTRADA  = os.path.join("dados", "entrada", "colaboradores.csv")
SAIDA    = os.path.join("dados", "entrada", "cnpj_cpf.csv")


def eh_cnpj(valor):
    return valor.isdigit() and len(valor) == 14


def main():
    gerados          = 0
    invalidos        = set()  # cnpjs inválidos únicos
    vistos           = set()  # evita duplicatas cnpj+cpf

    with (
        open(ENTRADA, encoding="utf-8-sig") as f_in,
        open(SAIDA, "w", encoding="utf-8", newline="") as f_out,
    ):
        writer = csv.writer(f_out, delimiter=";")
        writer.writerow(["cnpj", "cpf"])

        for row in csv.DictReader(f_in, delimiter=";"):
            cpf  = row["cpf"].strip()
            cnpj = row["cnpj"].strip()

            if not eh_cnpj(cnpj):
                invalidos.add(cnpj)
                continue

            chave = (cnpj, cpf)
            if chave in vistos:
                continue
            vistos.add(chave)

            cnpj_fmt = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
            writer.writerow([cnpj_fmt, cpf])
            gerados += 1

    for cnpj in sorted(invalidos):
        print(f"[IGNORADO] cnpj={cnpj!r} (inválido)")

    print(f"\n[OK] {gerados} linhas geradas em {SAIDA}")
    print(f"[IGNORADOS] {len(invalidos)} CNPJs inválidos únicos")


if __name__ == "__main__":
    main()
