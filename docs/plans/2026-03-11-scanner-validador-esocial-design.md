# Design: Scanner de Holerites + Validação e Correção eSocial

**Data:** 2026-03-11
**Projeto:** scrapingSenior
**Abordagem escolhida:** Scripts independentes com JSON intermediário (Opção A)

---

## Contexto

O sistema atual (passo_3) acessa o eSocial para TODOS os colaboradores de TODAS as empresas em TODAS as competências — o que é inviável (até 1 minuto por request). A nova abordagem usa os holerites locais (PDFs já salvos) para identificar previamente quais empresas/colaboradores/competências têm os eventos alvo, reduzindo drasticamente as chamadas ao eSocial.

---

## Arquitetura Geral

```
dados/entrada/
  eventos.csv       → eventos alvo (id_evento, nome_evento)
  esocial.csv       → mapeamento eSocial (nome_esocial, nome_esocial_aux, irrf_esperado, tabela)
  empresas.csv      → 166 empresas (nome, id, cnpj)

dados/saida/
  {empresa}/FOLHA DE PAGAMENTO/{ano}/{MM-YYYY}/
    HOLERITE(S).pdf    → fonte primária (todos eventos + CPF + nome)
    FPLA150*.csv       → fallback (apenas eventos configurados no export)

  scanner_YYYYMMDD_HHMMSS.json     ← saída Passo 4
  validacao_YYYYMMDD_HHMMSS.json   ← saída Passo 5

passo_4/scanner_holerites.py       → extração local
passo_5/validador_esocial.py       → validação no eSocial
passo_6/corretor.py (adaptado)     → correção IRRF + assinatura JNLP
```

---

## Passo 4 — Scanner de Holerites

**Objetivo:** Varrer holerites locais e extrair CPF + nome + eventos por empresa/competência.
**Período:** 11/2024 → 12/2025

### Fluxo

```
Para cada pasta em dados/saida/:
  1. Valida empresa contra empresas.csv (nome normalizado)
     Fallback: lê linha 0 do primeiro CSV disponível (id_empresa ou nome)
  2. Para cada competência 11/2024 → 12/2025:
     a. Busca HOLERITES.pdf ou HOLERITE.pdf (primário)
     b. Fallback: CSV de folha no formato 0;/1;/2;
  3. Para cada página do PDF (1 página = 1 colaborador):
     - NOME: linha após cabeçalho "NOME CARGO DATA ADMISSÃO"
             (nome em MAIÚSCULAS antes do cargo em misto)
     - CPF:  regex no texto da página (NNN.NNN.NNN-NN ou 11 dígitos)
     - EVENTOS: código numérico (ex: "216 ") com valor ≠ 0,00
                Fallback: busca nome_esocial_aux ou nome_esocial
  4. Agrupa por empresa → lista de {competencia, cpf, nome, eventos[]}
  5. Salva scanner_TIMESTAMP.json
```

### Formato de Saída

```json
{
  "2245": {
    "id_empresa": "2245",
    "cnpj": "38423532000104",
    "nome_empresa": "153 TECNOLOGIA LTDA",
    "pasta": "153 TECNOLOGIA",
    "colaboradores": [
      {
        "competencia": "12/2024",
        "cpf": "01856551652",
        "nome": "FULANO DE TAL",
        "eventos": ["216"]
      }
    ]
  }
}
```

### Tratamento de Erros

| Situação | Comportamento |
|---|---|
| CPF não encontrado no PDF | `cpf: null`, colaborador incluído |
| Mês sem PDF e sem CSV | Log, pula competência |
| Empresa não encontrada em `empresas.csv` | Log `[SKIP]`, ignora pasta |
| PDF com layout diferente | Tenta extração; se falhar, pula página |

---

## Passo 5 — Validador eSocial

**Objetivo:** Para cada empresa, encontrar **1 id_rubrica por evento** consultando o eSocial. Reaproveita `passo_3/cookie.py` e `passo_3/parser.py`.

### Regra de Ouro

> Uma única entrada na tabela de um colaborador pode resolver múltiplos eventos simultaneamente. Itera colaboradores/competências apenas enquanto houver eventos pendentes.

### Fluxo

```
Para cada empresa no scanner JSON:
  1. selecionar_empresa(cnpj) + acessar_home_empresa() → GUID
  2. eventos_pendentes = todos os eventos distintos da empresa

  Para cada {cpf, competencia, eventos} nos colaboradores:
    Se eventos_pendentes vazio → para

    3. acessar_tabela_funcionário(cpf, competencia, guid)
    4. Para cada evento em eventos_pendentes:
       - parsear_tabela_funcionario(html, nome_esocial, nome_esocial_aux, tabela)
       - Se encontrou código_rubrica:
           buscar_rubrica(guid, codigo_rubrica) → id_rubrica, id_evento
           abrir_edicao_rubrica(id_rubrica, id_evento, guid)
           parsear_form_edicao() → campos_form, irrf_atual
           status = "CORRETO" se irrf_atual == irrf_esperado, senão "ERRADO"
           Remove evento de eventos_pendentes
    5. Se tabela inacessível → tenta próxima entrada

  Após esgotar colaboradores:
    Eventos ainda pendentes → "NÃO_ENCONTRADO" + alerta

  6. trocar_perfil()
  7. Salva progresso (retomável por empresa)
```

### Formato de Saída

```json
{
  "38423532000104": {
    "nome": "153 TECNOLOGIA LTDA",
    "guid": "uuid-da-empresa",
    "auditado_em": "2026-03-11T10:00:00",
    "rubricas": [
      {
        "id_rubrica": "38455370471",
        "id_evento": "38455370471",
        "nome_evento": "Média Variaveis 13º Integ",
        "cpf_usado": "01856551652",
        "competencia_usada": "202412",
        "irrf_atual": "12",
        "irrf_esperado": "12",
        "campos_form": {},
        "status": "CORRETO"
      }
    ],
    "nao_encontrados": ["216"],
    "alertas": ["Evento 216 encontrado no holerite mas não localizado no eSocial"]
  }
}
```

### Tratamento de Erros

| Situação | Comportamento |
|---|---|
| CPF null | Pula entrada, tenta próximo colaborador |
| Tabela vazia/sem dados | Pula, tenta próxima entrada |
| Evento não encontrado após todas entradas | `NÃO_ENCONTRADO` + alerta |
| Erro HTTP / timeout | Retry 3x com pausa, depois registra erro |
| Empresa já processada | Pula (retomada) |

---

## Passo 6 — Correção JNLP

**Objetivo:** Corrigir rubricas com `status: "ERRADO"`. Reaproveita `corretor.py` com adaptação mínima de leitura do JSON.

### Adaptação Necessária

- Adicionar `carregar_validacao(path)` para ler o novo formato do Passo 5
- Mapear `cnpj → guid → rubricas` do novo JSON
- Toda lógica de correção/JNLP permanece intacta

### Fluxo (sem alteração)

```
Para cada empresa com rubricas status="ERRADO":
  1. selecionar_empresa(cnpj)
  2. Para cada rubrica ERRADO:
     - abrir_edicao_rubrica(id_rubrica, id_evento, guid)
     - parsear_form_edicao() → confirma irrf_atual ainda errado
     - Atualiza DadosRubrica.CodigoIncidenciaIR = irrf_esperado
     - salvar_edicao() → POST (302 = sucesso)
     - baixar_jnlp() → subprocess.run(["javaws", path])
     - status = "CORRIGIDO" ou "ERRO_ASSINATURA"
  3. trocar_perfil()
  4. Salva JSON atualizado
```

### Tratamento de Erros

| Situação | Comportamento |
|---|---|
| `javaws` falha | `ERRO_ASSINATURA`, continua próxima rubrica |
| IRRF já correto ao reabrir | `CORRIGIDO` sem reprocessar |
| Sem rubricas ERRADO | Pula empresa silenciosamente |

---

## Decisões de Design

| Decisão | Escolha | Motivo |
|---|---|---|
| 1 id_rubrica por evento | Sim — para ao achar o 1º | Um id_rubrica serve para todos da empresa |
| Identificação do colaborador | CPF extraído do PDF | Não depende de cnpj_cpf.csv |
| Competência no Passo 5 | Tenta qualquer uma, itera se não achar | Flexibilidade máxima |
| Evento não encontrado no eSocial | NÃO_ENCONTRADO + alerta | Visibilidade para revisão manual |
| Fluxo de correção | Passo separado (Passo 6) | Separação clara validação/correção |
| corretor.py | Reutilizar com adaptação mínima | JNLP já funciona, só muda entrada |
