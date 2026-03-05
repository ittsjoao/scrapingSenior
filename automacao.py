import os
import time

import pyautogui
import pyperclip

from config import INTERVALO, PASTA_BOTOES, PASTA_PRINTS, PAUSA_CURTA, TIMEOUT
from salvador import registrar_log

# Segurança: mover o mouse para o canto SUPERIOR ESQUERDO da tela para parar.
pyautogui.FAILSAFE = True


# ─────────────────────────────────────────────
# Primitivas de imagem
# ─────────────────────────────────────────────


def _decrementar_mes(periodo_str):
    """'122025' → '112025', '012025' → '122024'. Formato: MMYYYY."""
    mes = int(periodo_str[:2])
    ano = int(periodo_str[2:])
    mes -= 1
    if mes == 0:
        mes = 12
        ano -= 1
    return f"{mes:02d}{ano}"


def _encontrar(nome_imagem, confidence=0.8):
    """Localiza a imagem na tela. Retorna posição ou None."""
    try:
        return pyautogui.locateOnScreen(
            os.path.join(PASTA_BOTOES, nome_imagem), confidence=confidence
        )
    except pyautogui.ImageNotFoundException:
        return None


def aguardar_aparecer(nome_imagem, timeout=None):
    """
    Aguarda até que a imagem apareça na tela.
    Retorna a posição se encontrou, None se esgotou o tempo (TIMEOUT segundos).

    Substitui o padrão: time.sleep(PAUSA_LONGA) + _encontrar()
    """
    if timeout is None:
        timeout = TIMEOUT
    inicio = time.time()
    while time.time() - inicio < timeout:
        pos = _encontrar(nome_imagem)
        if pos is not None:
            return pos
        time.sleep(INTERVALO)
    print(f"  [!] Timeout ({timeout}s) aguardando: {nome_imagem}")
    return None


def aguardar_sumir(nome_imagem, timeout=None):
    """
    Aguarda até que a imagem desapareça da tela (ex: tela de carregamento).
    Retorna True se sumiu, False se esgotou o tempo.
    """
    if timeout is None:
        timeout = TIMEOUT
    inicio = time.time()
    while time.time() - inicio < timeout:
        if _encontrar(nome_imagem) is None:
            return True
        time.sleep(INTERVALO)
    print(f"  [!] Timeout ({timeout}s) esperando sumir: {nome_imagem}")
    return False


# ─────────────────────────────────────────────
# Ações de teclado e mouse
# ─────────────────────────────────────────────


def clicar_botao(nome_imagem):
    """Clica no botão assim que ele aparecer na tela. Retorna True/False."""
    posicao = aguardar_aparecer(nome_imagem)
    if posicao is None:
        return False
    pyautogui.click(posicao)
    time.sleep(PAUSA_CURTA)
    return True


def digitar_texto(texto):
    """Cola um texto no campo ativo via Ctrl+V. Suporta acentos."""
    pyperclip.copy(str(texto))
    pyautogui.hotkey("ctrl", "v")
    time.sleep(PAUSA_CURTA)


def limpar_evento():
    pyautogui.press("backspace")
    pyautogui.press("backspace")
    pyautogui.press("backspace")
    pyautogui.press("backspace")
    time.sleep(PAUSA_CURTA)


def pressionar_tab():
    pyautogui.press("tab")
    time.sleep(PAUSA_CURTA)


def pressionar_enter():
    pyautogui.press("enter")
    time.sleep(PAUSA_CURTA)


def pressionar_baixo():
    pyautogui.press("down")
    time.sleep(PAUSA_CURTA)


def fechar():
    pyautogui.hotkey("alt", "f4")
    time.sleep(PAUSA_CURTA)


def aguardar(segundos):
    time.sleep(segundos)


def tirar_screenshot(nome_arquivo):
    os.makedirs(PASTA_PRINTS, exist_ok=True)
    caminho = os.path.join(PASTA_PRINTS, f"{nome_arquivo}.png")
    pyautogui.screenshot(caminho)
    return caminho


# ─────────────────────────────────────────────
# Fluxos do Senior
# ─────────────────────────────────────────────


def pesquisar_empresa(
    nome_imagem_empresa,
    nome_imagem_buscar,
    nome_imagem_btn_pesquisa,
    nome_imagem_btn_ok,
    id_empresa,
):
    # 1. Abre o seletor de empresa (duplo clique)
    posicao = aguardar_aparecer(nome_imagem_empresa)
    if posicao is None:
        return False
    pyautogui.doubleClick(posicao)

    # 2. Aguarda o campo de busca aparecer (confirma que o dialog abriu)
    posicao_buscar = aguardar_aparecer(nome_imagem_buscar)
    if posicao_buscar is None:
        return False
    pyautogui.click(posicao_buscar)
    digitar_texto(id_empresa)

    # 3. Clica em Pesquisar e aguarda o botão OK aparecer (resultado carregado)
    posicao_pesquisa = aguardar_aparecer(nome_imagem_btn_pesquisa)
    if posicao_pesquisa is None:
        return False
    pyautogui.click(posicao_pesquisa)

    posicao_ok = aguardar_aparecer(nome_imagem_btn_ok)
    if posicao_ok is None:
        return False
    pyautogui.click(posicao_ok)
    time.sleep(PAUSA_CURTA)
    return True


def inicio_evento(nome_imagem_btn_ok, nome_imagem_btn_evento):
    # 1. Duplo clique para abrir a aba de eventos
    posicao = aguardar_aparecer(nome_imagem_btn_evento)
    if posicao is None:
        return False
    pyautogui.doubleClick(posicao)

    # 2. Aguarda o botão OK do dialog aparecer
    posicao_ok = aguardar_aparecer(nome_imagem_btn_ok)
    if posicao_ok is None:
        return False
    pyautogui.click(posicao_ok)
    time.sleep(PAUSA_CURTA)
    pyautogui.click(posicao_ok)  # segundo clique conforme fluxo original
    return True


def configurar_filtros(
    id_evento,
    periodo,
    fim_periodo,
    tipo_calculo,
    filial_ativa,
    nome_imagem_msg_error,
    nome_imagem_btn_listar,
    nome_imagem_validacao,
):
    """
    Executa o 1º evento com o fluxo completo (evento + período + filtros).
    Retorna (fim_periodo_efetivo, tem_dados) ou None em caso de erro de período.
    """
    # 1. Digita o 1º evento e vai para o campo de período
    digitar_texto(id_evento)
    pressionar_tab()

    # 2. Digita período início e verifica erro imediato
    digitar_texto(periodo)
    pressionar_tab()
    if _encontrar(nome_imagem_msg_error) is not None:
        print("  [!] Erro de período início. Pulando empresa.")
        clicar_botao("btn_ok_3.png")
        return None

    # 3. Tenta fim_periodo, decrementa até 12x se necessário
    fim_atual = fim_periodo
    for _ in range(12):
        digitar_texto(fim_atual)
        pressionar_tab()
        if _encontrar(nome_imagem_msg_error) is None:
            break
        clicar_botao("btn_ok_3.png")
        pyautogui.moveRel(50, 0)
        fim_novo = _decrementar_mes(fim_atual)
        registrar_log(
            f"[AJUSTE] Período {fim_atual[:2]}/{fim_atual[2:]} inválido"
            f" → tentando {fim_novo[:2]}/{fim_novo[2:]}"
        )
        fim_atual = fim_novo
        pyautogui.hotkey("ctrl", "a")
    else:
        registrar_log("[ERRO] Nenhum período válido encontrado após 12 tentativas.")
        return None

    if fim_atual != fim_periodo:
        registrar_log(
            f"[AJUSTE] Período utilizado: {periodo[:2]}/{periodo[2:]}"
            f" à {fim_atual[:2]}/{fim_atual[2:]}"
        )

    # 4. Preenche tipo_calculo e filial_ativa
    digitar_texto(tipo_calculo)
    pressionar_tab()
    digitar_texto(filial_ativa)
    pressionar_tab()
    pressionar_tab()
    pressionar_enter()

    # 5. Aguarda btn_listar aparecer e clica
    posicao_listar = aguardar_aparecer(nome_imagem_btn_listar)
    if posicao_listar is None:
        print("  [!] btn_listar não apareceu no setup inicial.")
        return None
    pyautogui.click(posicao_listar)

    # 6. Verifica se há dados (validação)
    posicao_validacao = aguardar_aparecer(nome_imagem_validacao, timeout=10)
    tem_dados = posicao_validacao is not None

    return (fim_atual, tem_dados)


def pesquisar_evento(
    id_evento,
    nome_imagem_msg_error,
    periodo,
    fim_periodo,
    tipo_calculo,
    filial_ativa,
    nome_imagem_btn_listar,
    nome_imagem_validacao,
):
    # Preenche os filtros via Tab
    digitar_texto(id_evento)
    pressionar_tab()
    digitar_texto(periodo)
    pressionar_tab()

    # Verifica se apareceu mensagem de erro de período (resposta imediata)
    if _encontrar(nome_imagem_msg_error) is not None:
        print("  [!] Erro de período. Fechando aba e pulando empresa.")
        clicar_botao("btn_ok_3.png")
        return None  # sinaliza ao main.py para pular a empresa inteira

    # Tenta fim_periodo; se der erro, decrementa mês até 12 tentativas
    fim_atual = fim_periodo
    for _ in range(12):
        digitar_texto(fim_atual)
        pressionar_tab()
        if _encontrar(nome_imagem_msg_error) is None:
            break
        clicar_botao("btn_ok_3.png")
        pyautogui.moveRel(50, 0)  # afasta o mouse do botão OK para não obstruir a próxima busca
        fim_novo = _decrementar_mes(fim_atual)
        registrar_log(
            f"[AJUSTE] Período {fim_atual[:2]}/{fim_atual[2:]} inválido"
            f" → tentando {fim_novo[:2]}/{fim_novo[2:]}"
        )
        fim_atual = fim_novo
        pyautogui.hotkey("ctrl", "a")  # seleciona o campo para sobrescrever
    else:
        registrar_log("[ERRO] Nenhum período válido encontrado após 12 tentativas.")
        return None

    if fim_atual != fim_periodo:
        registrar_log(
            f"[AJUSTE] Período utilizado: {periodo[:2]}/{periodo[2:]}"
            f" À {fim_atual[:2]}/{fim_atual[2:]}"
        )

    digitar_texto(tipo_calculo)
    pressionar_tab()
    digitar_texto(filial_ativa)
    pressionar_tab()
    pressionar_tab()
    pressionar_enter()

    # Aguarda o botão Listar aparecer (o sistema carregou o resultado)
    posicao_listar = aguardar_aparecer(nome_imagem_btn_listar)
    if posicao_listar is None:
        print("  [!] Botão Listar não apareceu — sem dados ou timeout.")
        return False

    pyautogui.click(posicao_listar)

    # Aguarda a validação aparecer (confirma que há dados na listagem)
    posicao_validacao = aguardar_aparecer(nome_imagem_validacao, timeout=10)
    if posicao_validacao is None:
        print("  [~] Sem dados para este evento.")
        return False

    return True


def salvar_evento(
    nome_arquivo,
    caminho_arquivo,
    id_empresa,
    nome_btn_ok_salvar,
    nome_btn_disket,
    nome_btn_ok_confirmar,
):
    # Preenche o formulário via Tab
    digitar_texto(nome_arquivo)
    for _ in range(13):
        pressionar_tab()
    digitar_texto(id_empresa)

    # Clica no primeiro OK e aguarda o botão diskette aparecer
    posicao_ok_salvar = aguardar_aparecer(nome_btn_ok_salvar)
    if posicao_ok_salvar is None:
        return False
    pyautogui.click(posicao_ok_salvar)

    posicao_disket = aguardar_aparecer(nome_btn_disket)
    if posicao_disket is None:
        return False
    pyautogui.click(posicao_disket)

    # Digita o caminho completo do arquivo
    digitar_texto(caminho_arquivo + nome_arquivo + ".txt")

    # Seleciona formato e confirma
    pressionar_tab()
    pressionar_baixo()
    pressionar_tab()
    pressionar_enter()

    # Segundo OK (se aparecer)
    posicao_ok2 = aguardar_aparecer(nome_btn_ok_confirmar, timeout=5)
    if posicao_ok2 is not None:
        pyautogui.click(posicao_ok2)

    fechar()
    return True
