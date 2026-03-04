import os

from automacao import (
    aguardar,
    clicar_botao,
    inicio_evento,
    limpar_evento,
    pesquisar_empresa,
    pesquisar_evento,
    salvar_evento,
)
from leitor_planilha import carregar_empresas, carregar_eventos
from salvador import registrar_log, sanitizar_nome

# ============================================================
# ANTES DE RODAR:
#   1. pip install -r requirements.txt
#   2. Capture as imagens dos botões e salve em capturas/botoes/
#   3. Abra o Senior na tela inicial
#   4. python main.py
#
# SEGURANÇA: mova o mouse para o canto SUPERIOR ESQUERDO para parar.
# ============================================================

# Filtros usados em pesquisar_evento — ajuste conforme necessário
PERIODO = "112024"
FIM_PERIODO = "122025"
TIPO_CALCULO = "11"
FILIAL_ATIVA = "N"

print("=" * 55)
print("  Automacao Senior — Coleta de Relatorios")
print("=" * 55)
print("Abra o Senior e deixe-o na tela inicial.")
print("Iniciando em 5 segundos...")
print("(Mouse no canto superior esquerdo = PARAR)")
aguardar(5)

# --------------------------------------------------
# PASSO 1: Carrega empresas e eventos dos CSVs
# --------------------------------------------------
registrar_log("Iniciando execucao")

empresas = carregar_empresas()
eventos = carregar_eventos()

# --------------------------------------------------
# PASSO 2: Loop principal — empresa por empresa
# --------------------------------------------------
for empresa in empresas:
    nome_empresa = empresa["nome_empresa"]
    id_empresa = empresa["id_empresa"]

    registrar_log(f"Iniciando empresa: {nome_empresa} (ID: {id_empresa})")

    # Seleciona a empresa no Senior (1x por empresa)
    ok = pesquisar_empresa(
        "btn_selecionar_empresa.png",
        "btn_preencher_empresa.png",
        "btn_pesquisar_empresa.png",
        "btn_ok_salvar.png",
        id_empresa,
    )
    if not ok:
        registrar_log(f"[ERRO] Empresa nao encontrada, pulando: {nome_empresa}")
        continue

    # Abre a aba de eventos (1x por empresa)
    ok = inicio_evento(
        "btn_ok.png",
        "btn_eventos.png",
    )
    if not ok:
        registrar_log(f"[ERRO] Nao abriu aba de eventos: {nome_empresa}")
        continue

    # Loop de eventos — reutiliza a aba aberta, só limpa o campo entre eventos
    for evento in eventos:
        id_evento = evento["id_evento"]
        nome_evento = evento["nome_evento"]

        print(f"\n  >> Evento {id_evento} - {nome_evento}")

        # Clica no campo de evento e apaga o valor anterior
        clicar_botao("btn_preencher_evento.png")
        limpar_evento()

        # Preenche os filtros — sem fechar a aba se não encontrar dados
        ok = pesquisar_evento(
            id_evento,
            "msg_error.png",
            PERIODO,
            FIM_PERIODO,
            TIPO_CALCULO,
            FILIAL_ATIVA,
            "btn_listar.png",
            "btn_validacao_listar.png",
        )
        if ok is None:
            # Erro de período — fecha a aba e pula para a próxima empresa
            registrar_log(f"[ERRO] Período inválido, pulando empresa: {nome_empresa}")
            clicar_botao("btn_fechar_aba.png")
            break
        if not ok:
            registrar_log(f"[PULOU] Sem dados: {id_evento} - {nome_evento}")
            continue

        # Monta o caminho da pasta da empresa
        pasta_empresa = os.path.abspath(
            os.path.join("dados", "saida", sanitizar_nome(nome_empresa))
        )
        nome_arquivo = f"{nome_evento}"

        # Salva o relatório — sem fechar a aba após salvar
        ok = salvar_evento(
            nome_arquivo,
            pasta_empresa + os.sep,
            id_empresa,
            "btn_ok_salvar.png",
            "btn_diskette.png",
            "btn_ok_2.png",
        )
        if not ok:
            registrar_log(f"[PULOU] Falha ao salvar: {id_evento} - {nome_evento}")
            continue
        registrar_log(f"[OK] {nome_empresa} | {id_evento} - {nome_evento}")

    # Todos os eventos desta empresa concluídos — fecha a aba uma única vez
    clicar_botao("btn_fechar_aba.png")
    registrar_log(f"Empresa concluida: {nome_empresa}")

# --------------------------------------------------
registrar_log("Execucao concluida!")
print("\nFinalizado! Arquivos salvos em dados/saida/")
