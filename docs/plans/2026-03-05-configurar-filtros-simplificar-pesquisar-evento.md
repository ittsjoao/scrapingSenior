# Refatoração: configurar_filtros + pesquisar_evento simplificado

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separar o setup inicial de filtros (1ª execução completa) do loop simplificado de eventos, evitando preencher período/tipo/filial repetidamente para cada evento.

**Architecture:** Nova função `configurar_filtros` em `automacao.py` processa o 1º evento do CSV com o fluxo completo (evento → período → tipo → filial → listar → valida). A função `pesquisar_evento` é simplificada para processar os demais eventos apenas com (evento → btn_mostrar → listar → valida). `main.py` orquestra as duas fases.

**Tech Stack:** Python 3, PyAutoGUI (image recognition + keyboard/mouse), PyPerclip (clipboard paste).

---

## Contexto do projeto

- GUI automation do sistema Senior (RPA) — sem testes unitários automatizados possíveis (depende de tela do sistema externo)
- Verificação é feita via execução real ou dry-run com prints
- Arquivo de botões: `capturas/botoes/` — `btn_mostrar.png` já existe no diretório
- Campos do formulário do Senior (ordem via Tab): **evento → período_início → período_fim → tipo_cálculo → filial_ativa**
- Após Enter/btn_mostrar o sistema carrega `btn_listar`; após clicar em listar aparece `btn_validacao_listar` (confirma que há dados)

---

### Task 1: Criar `configurar_filtros` em `automacao.py`

**Files:**
- Modify: `automacao.py` (adicionar função após `inicio_evento`, antes de `pesquisar_evento`)

**Step 1: Inserir a função `configurar_filtros`**

Adicionar o bloco abaixo em `automacao.py`, logo após a função `inicio_evento` (linha ~189):

```python
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

    # 5. Aguarda btn_listar e clica
    posicao_listar = aguardar_aparecer(nome_imagem_btn_listar)
    if posicao_listar is None:
        print("  [!] btn_listar não apareceu no setup inicial.")
        return None
    pyautogui.click(posicao_listar)

    # 6. Verifica se há dados (validação)
    posicao_validacao = aguardar_aparecer(nome_imagem_validacao, timeout=10)
    tem_dados = posicao_validacao is not None

    return (fim_atual, tem_dados)
```

**Step 2: Verificar que não há erro de sintaxe**

```bash
cd C:/Users/joao.silva/Documents/projetos/scrapingSenior
python -c "import automacao; print('OK')"
```

Expected: `OK` (sem traceback)

**Step 3: Commit**

```bash
git add automacao.py
git commit -m "feat: add configurar_filtros for initial full event setup"
```

---

### Task 2: Simplificar `pesquisar_evento` em `automacao.py`

**Files:**
- Modify: `automacao.py` — substituir corpo de `pesquisar_evento`

**Step 1: Substituir a função `pesquisar_evento`**

Substituir a implementação atual completa de `pesquisar_evento` por:

```python
def pesquisar_evento(
    id_evento,
    nome_imagem_btn_preencher,
    nome_imagem_btn_mostrar,
    nome_imagem_btn_listar,
    nome_imagem_validacao,
):
    """
    Fluxo simplificado para eventos 2..N (período/filtros já configurados).
    Retorna True se há dados, False se não há ou timeout.
    """
    # 1. Clica no campo de evento, limpa e digita o novo código
    posicao = aguardar_aparecer(nome_imagem_btn_preencher)
    if posicao is None:
        return False
    pyautogui.click(posicao)
    limpar_evento()
    digitar_texto(id_evento)

    # 2. Clica em Mostrar (substitui Tab+Tab+Enter do fluxo anterior)
    posicao_mostrar = aguardar_aparecer(nome_imagem_btn_mostrar)
    if posicao_mostrar is None:
        print("  [!] btn_mostrar não encontrado.")
        return False
    pyautogui.click(posicao_mostrar)

    # 3. Aguarda btn_listar aparecer e clica
    posicao_listar = aguardar_aparecer(nome_imagem_btn_listar)
    if posicao_listar is None:
        print("  [!] btn_listar não apareceu — sem dados ou timeout.")
        return False
    pyautogui.click(posicao_listar)

    # 4. Valida se há dados na listagem
    posicao_validacao = aguardar_aparecer(nome_imagem_validacao, timeout=10)
    if posicao_validacao is None:
        print("  [~] Sem dados para este evento.")
        return False

    return True
```

**Step 2: Verificar sintaxe**

```bash
python -c "import automacao; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add automacao.py
git commit -m "refactor: simplify pesquisar_evento to event→mostrar→listar→validate"
```

---

### Task 3: Atualizar `main.py` para o novo fluxo

**Files:**
- Modify: `main.py`

**Step 1: Atualizar o import de `automacao`**

Substituir o bloco de imports de `automacao`:

```python
# ANTES
from automacao import (
    aguardar,
    clicar_botao,
    inicio_evento,
    limpar_evento,
    pesquisar_empresa,
    pesquisar_evento,
    salvar_evento,
)

# DEPOIS
from automacao import (
    aguardar,
    clicar_botao,
    configurar_filtros,
    inicio_evento,
    pesquisar_empresa,
    pesquisar_evento,
    salvar_evento,
)
```

> Nota: `limpar_evento` foi removido do import pois agora é chamado internamente por `pesquisar_evento`.

**Step 2: Substituir o loop de eventos dentro do for-empresa**

Localizar o bloco que começa em `time.sleep(PAUSA_CURTA)` (após `inicio_evento`) e vai até o `clicar_botao("btn_fechar_aba.png")` final da empresa. Substituir por:

```python
    time.sleep(PAUSA_CURTA)
    pyautogui.press("1")

    # ── Setup + 1º evento (fluxo completo) ──────────────────────────
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
            registrar_log(f"[OK] {nome_empresa} | {primeiro['id_evento']} - {primeiro['nome_evento']}")
        else:
            registrar_log(f"[PULOU] Falha ao salvar: {primeiro['id_evento']} - {primeiro['nome_evento']}")
    else:
        registrar_log(f"[PULOU] Sem dados: {primeiro['id_evento']} - {primeiro['nome_evento']}")

    # ── Eventos restantes (fluxo simplificado) ──────────────────────
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

    # ── Fecha aba da empresa ─────────────────────────────────────────
    clicar_botao("btn_fechar_aba.png")
    registrar_log(f"Empresa concluida: {nome_empresa}")
```

**Step 3: Verificar sintaxe de main.py**

```bash
python -c "import ast; ast.parse(open('main.py').read()); print('OK')"
```

Expected: `OK`

**Step 4: Verificar que todos os imports resolvem**

```bash
python -c "
from automacao import aguardar, clicar_botao, configurar_filtros, inicio_evento, pesquisar_empresa, pesquisar_evento, salvar_evento
print('imports OK')
"
```

Expected: `imports OK`

**Step 5: Commit final**

```bash
git add main.py
git commit -m "refactor: update main.py to use configurar_filtros + simplified pesquisar_evento"
```

---

### Task 4: Verificação manual (checklist)

Antes de rodar em produção (todas as 166 empresas), testar com 1 empresa e 2–3 eventos editando `empresas.csv` temporariamente.

**Checklist:**
- [ ] `configurar_filtros` preenche evento + período corretamente na tela do Senior
- [ ] Erro de período início retorna `None` e pula empresa
- [ ] Decremento de `fim_periodo` funciona quando período inválido
- [ ] Log registra período ajustado quando decrementa
- [ ] `btn_listar` aparece e é clicado após setup
- [ ] Primeiro evento salvo corretamente em `dados/saida/<empresa>/`
- [ ] `pesquisar_evento` (simplificado) clica em `btn_preencher_evento`, limpa, digita novo evento
- [ ] `btn_mostrar` é clicado e `btn_listar` aparece em seguida
- [ ] Evento sem dados gera log `[PULOU]` e segue para o próximo
- [ ] Empresa concluída fecha aba corretamente

---

## Observações

- `btn_mostrar.png` já existe em `capturas/botoes/` (confirmado na exploração do projeto)
- A variável `_fim_efetivo` retornada por `configurar_filtros` é prefixada com `_` por ser ignorada no loop de empresas (o período foi ajustado uma vez e o Senior mantém o valor na tela)
- O `pyautogui.press("1")` que existia em `main.py` após `inicio_evento` foi mantido no mesmo lugar
