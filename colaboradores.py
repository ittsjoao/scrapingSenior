import os

import automacao
from config import PASTA_BOTOES_COLAB
from automacao import (
    aguardar,
    fechar,
    listar_colaboradores,
    pesquisar_empresa,
    salvar_colab,
)
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

    ok = pesquisar_empresa(
        "btn_selecionar_empresa.png",
        "btn_preencher_empresa.png",
        "btn_pesquisar_empresa.png",
        "btn_ok_salvar.png",
        id_empresa,
    )
    if not ok:
        registrar_log(f"[ERRO] Empresa nao encontrada, pulando: {nome_empresa}")
        fechar()
        continue

    ok = listar_colaboradores(
        "btn_relacao.png",
        "tb_principal.png",
        "validador.png",
        "erro_listar.png",
    )
    if not ok:
        registrar_log(f"[ERRO] Empresa {nome_empresa} sem colaboradores")
        fechar()
        continue

    salvar_colab(
        "btn_diskette.png", pasta_empresa + os.sep, "colaboradores", "btn_ok_2.png"
    )

    registrar_log(f"Empresa concluida: {nome_empresa}")

# --------------------------------------------------
registrar_log("Execucao concluida!")
print("\nFinalizado! Arquivos salvos em dados/saida/")
