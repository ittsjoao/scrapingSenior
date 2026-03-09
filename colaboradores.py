import os

import automacao
from automacao import (
    aguardar,
    listar_colaboradores,
    loop_colaboradores,
    salvar_colab,
)
from config import PASTA_BOTOES_COLAB
from leitor_planilha import carregar_empresas
from salvador import registrar_log, sanitizar_nome

automacao.PASTA_BOTOES = PASTA_BOTOES_COLAB

print("=" * 55)
print("  Automacao Senior — Coleta de colaboradores")
print("=" * 55)
print("Abra o Senior e deixe-o na tela inicial.")
print("Iniciando em 5 segundos...")
print("(Mouse no canto superior esquerdo = PARAR)")
aguardar(5)

empresas = carregar_empresas()

# Entra na tela de relação uma única vez
ok = listar_colaboradores(
    "btn_relacao.png",
    "tb_principal.png",
    "validador.png",
    "erro_listar.png",
)
if not ok:
    registrar_log("[ERRO] Não foi possível abrir a tela de relação.")
    raise SystemExit(1)

# --------------------------------------------------
# Loop principal — empresa por empresa
# --------------------------------------------------
for empresa in empresas:
    nome_empresa = empresa["nome_empresa"]
    id_empresa = empresa["id_empresa"]
    pasta_empresa = os.path.abspath(
        os.path.join("dados", "saida", sanitizar_nome(nome_empresa))
    )
    registrar_log(f"Iniciando empresa: {nome_empresa} (ID: {id_empresa})")

    ok = loop_colaboradores("erro_listar.png", id_empresa)
    if not ok:
        registrar_log(f"[AVISO] Empresa sem colaboradores: {nome_empresa}")
        continue

    salvar_colab(
        "btn_diskette.png", pasta_empresa + os.sep, "colaboradores", "salvar_again.png"
    )

    registrar_log(f"Empresa concluida: {nome_empresa}")

# --------------------------------------------------
registrar_log("Execucao concluida!")
print("\nFinalizado! Arquivos salvos em dados/saida/")
