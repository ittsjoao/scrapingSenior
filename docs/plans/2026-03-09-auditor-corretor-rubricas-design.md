# Design: Auditor + Corretor de Rúbricas eSocial

**Data:** 2026-03-09
**Escopo:** `passo_3/`

## Contexto

O fluxo atual (`main.py`) faz auditoria e correção em uma única passagem, o que torna inviável rodar sem supervisão. A partição em dois scripts permite rodar o auditor à noite e o corretor de forma controlada.

## Decisões de Design

| Decisão | Escolha | Motivo |
|---|---|---|
| Estrutura | Dois scripts independentes | Sem refatoração do código existente |
| Formato intermediário | JSON | Preserva estrutura aninhada dos campos do form |
| Escopo do JSON | Todas as rúbricas (ERRADO/CORRETO/N/A) | Visibilidade completa do estado antes de corrigir |
| Resume do auditor | Por CNPJ | Se cair, pula empresas já auditadas |
| Estratégia do corretor | Re-abre form antes de salvar (opção C) | Evita sobrescrever valor já corrigido manualmente |

## Arquivos Produzidos

```
passo_3/
  auditor.py       ← novo
  corretor.py      ← novo
  cookie.py        ← sem alteração
  parser.py        ← sem alteração (possível adição de parse de campos)
  entradas.py      ← sem alteração
  saida.py         ← sem alteração
  main.py          ← mantido intacto

dados/saida/
  auditoria_YYYYMMDD_HHMMSS.json   ← gerado pelo auditor, consumido pelo corretor
```

## JSON Intermediário

Chave raiz: CNPJ (14 dígitos sem formatação).

```json
{
  "38423532000104": {
    "nome": "153 TECNOLOGIA LTDA",
    "auditado_em": "2026-03-09T23:14:00",
    "rubricas": [
      {
        "id_rubrica": "123",
        "id_evento": "456",
        "nome_evento": "IRRF MENSAL",
        "cpf": "12345678901",
        "competencia": "12/2025",
        "irrf_atual": "09",
        "irrf_esperado": "11",
        "campos_form": {
          "DadosRubrica.CodigoIncidenciaIR": "09",
          "__RequestVerificationToken": "..."
        },
        "status": "ERRADO"
      }
    ]
  }
}
```

### Ciclo de vida do `status`

```
Auditor  → CORRETO | ERRADO | N/A
Corretor → ERRADO → CORRIGIDO | CORRIGIDO_EXTERNAMENTE
```

O corretor ignora `CORRETO`, `N/A` e `CORRIGIDO*`.

## Fluxo do Auditor (`auditor.py`)

```
1. Carregar cookies.txt, cnpj_cpf.csv, esocial.csv
2. Carregar auditoria.json existente → set de CNPJs já auditados
3. Para cada EMPRESA:
   a. Se CNPJ no set → pula (resume)
   b. selecionar_empresa()
   c. acessar_home_empresa() → GUID
   d. Para cada CPF × mês (12/2025 → 11/2024):
      - acessar_tabela_funcionário() → código da rúbrica
      - buscar_rubrica() → id_rubrica, id_evento
      - abrir_edicao_rubrica() → campos_form
      - Comparar CodigoIncidenciaIR → status
   e. Append empresa no JSON (write incremental)
   f. trocar_perfil()
4. Salvar auditoria.json
```

**Write incremental:** após cada empresa, o JSON é salvo em disco. Garante que um crash não perde dados já coletados.

## Fluxo do Corretor (`corretor.py`)

```
1. Receber caminho do auditoria.json (argumento ou mais recente em dados/saida/)
2. Filtrar rubricas com status=ERRADO
3. Para cada EMPRESA com rubricas ERRADAS:
   a. selecionar_empresa()
   b. Para cada rúbrica ERRADA:
      - abrir_edicao_rubrica(id_rubrica, id_evento)
      - Ler CodigoIncidenciaIR atual
      - Se ainda errado: substituir + salvar_edicao() + assinar
        → status = CORRIGIDO
      - Se já correto: status = CORRIGIDO_EXTERNAMENTE
      - Salvar JSON após cada rúbrica
   c. trocar_perfil()
4. Salvar auditoria.json atualizado
```

## Tratamento de Erros

| Situação | Comportamento |
|---|---|
| selecionar_empresa falha | Loga erro, pula empresa, continua |
| abrir_edicao_rubrica retorna None | status = N/A (erro_form) |
| salvar_edicao retorna erro | status permanece ERRADO, loga falha |
| Assinatura falha | status = ERRO_ASSINATURA |
| Crash do auditor | Resume pelo CNPJ no próximo run |

## O que NÃO muda

- `cookie.py`, `parser.py`, `entradas.py`, `saida.py`, `main.py` — sem alteração.
- Pode ser necessário adicionar parsing de campos adicionais em `parser.py` se `parsear_form_edicao` não retornar todos os campos necessários.
