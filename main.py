import os
import time

import pyautogui

from automacao import (
    aguardar,
    clicar_botao,
    configurar_filtros,
    inicio_evento,
    pesquisar_empresa,
    pesquisar_evento,
    salvar_evento,
)
from config import PAUSA_CURTA
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
FIM_PERIODO = "052025"
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
    time.sleep(PAUSA_CURTA)
    pyautogui.press("0")

    # ── Setup + 1º evento (fluxo completo com período e filtros) ────
    primeiro = eventos[0]
    print(f"\n  >> [SETUP] Evento {primeiro['id_evento']} - {primeiro['nome_evento']}")

    resultado = configurar_filtros(
        primeiro["id_evento"],
        PERIODO,
        FIM_PERIODO,
        TIPO_CALCULO,
        FILIAL_ATIVA,
        "msg_error.png",
        "btn_listar.png",
        "btn_validacao_listar.png",
    )

    if resultado is None:
        registrar_log(f"[ERRO] Período inválido, pulando empresa: {nome_empresa}")
        clicar_botao("btn_fechar_aba.png")
        continue

    _fim_efetivo, ok_primeiro = resultado
    pasta_empresa = os.path.abspath(
        os.path.join("dados", "saida", sanitizar_nome(nome_empresa))
    )

    if ok_primeiro:
        ok = salvar_evento(
            primeiro["nome_evento"],
            pasta_empresa + os.sep,
            id_empresa,
            "btn_ok_salvar.png",
            "btn_diskette.png",
            "btn_ok_2.png",
        )
        if ok:
            registrar_log(
                f"[OK] {nome_empresa} | {primeiro['id_evento']} - {primeiro['nome_evento']}"
            )
        else:
            registrar_log(
                f"[PULOU] Falha ao salvar: {primeiro['id_evento']} - {primeiro['nome_evento']}"
            )
    else:
        registrar_log(
            f"[PULOU] Sem dados: {primeiro['id_evento']} - {primeiro['nome_evento']}"
        )

    # ── Eventos restantes — fluxo simplificado ──────────────────────
    for evento in eventos[1:]:
        id_evento = evento["id_evento"]
        nome_evento = evento["nome_evento"]

        print(f"\n  >> Evento {id_evento} - {nome_evento}")

        ok = pesquisar_evento(
            id_evento,
            "btn_preencher_evento.png",
            "btn_mostrar.png",
            "btn_listar.png",
            "btn_validacao_listar.png",
        )

        if not ok:
            registrar_log(f"[PULOU] Sem dados: {id_evento} - {nome_evento}")
            continue

        ok = salvar_evento(
            nome_evento,
            pasta_empresa + os.sep,
            id_empresa,
            "btn_ok_salvar.png",
            "btn_diskette.png",
            "btn_ok_2.png",
        )
        if ok:
            registrar_log(f"[OK] {nome_empresa} | {id_evento} - {nome_evento}")
        else:
            registrar_log(f"[PULOU] Falha ao salvar: {id_evento} - {nome_evento}")

    # ── Fecha a aba da empresa ───────────────────────────────────────
    clicar_botao("btn_fechar_aba.png")
    registrar_log(f"Empresa concluida: {nome_empresa}")

# --------------------------------------------------
registrar_log("Execucao concluida!")
print("\nFinalizado! Arquivos salvos em dados/saida/")
