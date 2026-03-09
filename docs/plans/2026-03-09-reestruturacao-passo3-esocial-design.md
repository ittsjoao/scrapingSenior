# Design — Reestruturação passo_3: Busca de Rúbricas por CPF/CNPJ

**Data:** 2026-03-09

## Objetivo

Reestruturar o `passo_3` para que, ao invés de receber uma planilha com empresa + evento + CPF + competência específicos, receba um CSV com CNPJ + CPF e busque automaticamente os eventos listados em `esocial.csv` iterando por meses (12/2025 → 11/2024) para cada colaborador.

---

## Entradas

| Arquivo | Colunas | Descrição |
|---|---|---|
| `dados/entrada/cnpj_cpf.csv` | `cnpj;cpf` | Colaboradores a processar por empresa |
| `dados/entrada/esocial.csv` | `id_evento;nome_esocial;nome_esocial_aux;irrf;tabela;demissão` | Eventos a buscar e IRRF esperado |

Eventos com `demissão=Sim` → não buscados, registrados como `N/A (Demissão)` nos outputs.

---

## Arquivos

```
passo_3/
  entradas.py   → lê cnpj_cpf.csv e esocial.csv
  cookie.py     → sem mudança (HTTP)
  parser.py     → sem mudança (HTML)
  saida.py      → escreve logs e planilha Excel
  main.py       → orquestra o fluxo
```

`planilha.py` removido (era para o xlsx antigo, não mais usado).

---

## Estrutura de Dados

### `entradas.carregar_empresas()`
```python
{
    "35.237.328/0001-00": ["08208570680", "12928982671"],
    ...
}
```

### `entradas.carregar_eventos()`
```python
# Retorna (eventos_ativos, eventos_demissao)
eventos_ativos = [
    {"nome": "MÉDIAS VARIAVEIS 13º INTEGRADO", "aux": "", "irrf": "12", "tabela": "Holerite"},
    ...
]
eventos_demissao = [
    {"nome": "AVISO PRÉVIO INDENIZADO", ...},
    ...
]
```

---

## Loop Principal (`main.py`)

```
Para cada empresa (CNPJ):
  1. selecionar_empresa → obter GUID da home
  2. pendentes = cópia de todos os eventos_ativos

  Para cada CPF:
    Para cada mês (202512 → 202411):
      html = acessar_tabela_funcionário(cpf, mês)
      Para cada evento pendente:
        codigo = parsear_tabela_funcionario(html, evento)
        Se encontrou → salva {codigo, cpf, mês} → remove dos pendentes
      Se pendentes vazio → break (achou tudo)
    Se pendentes vazio → break

  Para cada evento encontrado:
    buscar_rubrica → abrir_edicao_rubrica → ler IRRF atual
    Se IRRF correto  → log "CORRETO"
    Se IRRF incorreto → salvar_edicao → assinar_jnlp → log "INCORRETO" + log ajuste

  Eventos demissão    → registrar N/A (Demissão)
  Eventos não achados → registrar N/A

  trocar_perfil
```

---

## Outputs (`saida.py`)

### Log de descobertas — `log_descobertas_YYYYMMDD_HHMMSS.txt`
```
ARMACOES VITORIA LTDA (SEARMACOES...067 - ALDENEIDE VIEIRA - 08208570680) - IRRF CORRETO
ARMACOES VITORIA LTDA (SEARMACOES...051 - ALDENEIDE VIEIRA - 08208570680) - IRRF INCORRETO
ARMACOES VITORIA LTDA | AVISO PRÉVIO INDENIZADO - N/A (Demissão)
ARMACOES VITORIA LTDA | INSS RPA - N/A (não encontrado)
```

### Log de ajustes — `log_ajustes_YYYYMMDD_HHMMSS.txt`
```
ARMACOES VITORIA LTDA | MÉDIAS VARIAVEIS 13º INTEGRADO | IRRF antigo: 09 → novo: 12
```

### Planilha — `resultado_YYYYMMDD_HHMMSS.xlsx`

| EMPRESA | CNPJ | MÉDIAS VARIAVEIS 13º | HORAS FÉRIAS DIURNAS | AVISO PRÉVIO |
|---|---|---|---|---|
| ARMACOES VITORIA LTDA | 35.237.328/0001-00 | RETIFICADO | RETIFICADO | N/A (Demissão) |

- `RETIFICADO` → rúbrica encontrada (IRRF correto ou corrigido)
- `N/A (Demissão)` → evento ignorado por ser demissão
- `N/A` → rúbrica não encontrada em nenhum colaborador/mês

---

## Período de busca

Meses em ordem decrescente: `202512, 202511, 202510, 202509, 202508, 202507, 202506, 202505, 202504, 202503, 202502, 202501, 202412, 202411`
