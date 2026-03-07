# Automação eSocial — Correção de IRRF em Rúbricas

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ler uma planilha de eventos por empresa, encontrar cada rúbrica no eSocial via requests HTTP (reusando a sessão de `cookie.py`), validar o campo IRRF e corrigir quando necessário, gerando uma planilha de resultado.

**Architecture:** Quatro arquivos com responsabilidade única — `planilha.py` lê/agrupa dados, `parser.py` parseia HTML, `cookie.py` faz requests, `main.py` orquestra. A sessão HTTP é mantida por empresa (selecionar_empresa → processar todos eventos → trocar_perfil).

**Tech Stack:** Python 3, requests, openpyxl (leitura e escrita de planilha), BeautifulSoup4 (parsing HTML), subprocess (javaws para assinatura .jnlp).

---

## Contexto técnico

### Endpoints utilizados

| Função | Method | URL |
|---|---|---|
| Selecionar empresa | POST | `/portal/Home/IndexProcuracao?procuradorCnpj=...` |
| Trocar perfil (reset) | GET | `/portal/Home/Index?trocarPerfil=true` |
| Tabela do funcionário | GET | `/portal/FolhaPagamento/RemuneracaoCompleto?cpf=...&competencia=...` |
| Home da empresa | GET | `/portal/Home/Inicial?tipoEmpregador=EMPREGADOR_GERAL` |
| Buscar rúbrica | POST | `/portal/Rubrica/CadastroCompleto?id=<guid>` |
| Abrir edição | GET | `/portal/Rubrica/CadastroCompleto/Editar?idRubrica=...&idEvento=...` |
| Salvar edição | POST | `/portal/Rubrica/CadastroCompleto/Editar` |
| Assinadoc | GET | `/portal/Assinadoc` |

### Campos do POST de edição (salvar rúbrica)

Todos os campos atuais do form são submetidos sem alteração, exceto `DadosRubrica.CodigoIncidenciaIR` que recebe o novo valor da planilha. Campos obrigatórios: `__RequestVerificationToken`, `BloquearCodigo`, `BloquearAntigoPeriodoValidade`, `PermitirExibicaoGrupoProcessoPisPasep`, `Codigo`, `InicioValidade`, `FimValidade`, `IdTabelaRubrica`, `chkIdTabelaRubrica`, `DadosRubrica.*`, `FormularioProcesso*.Id=-1`, `editar:rubrica=Salvar`.

### Estrutura do HTML do colaborador

`table.table.sem-paginacao.mobile-table` — colunas: Tabela | Código | Tipo | Descrição | Quantidade | Número contrato | Fator | Valor Unitário | Valor | Ações.

A coluna "Tabela" distingue Holerite (1) de Férias (2). A coluna "Descrição" é comparada com EVENTO e EVENTO_AUX. A coluna "Código" (ex: `SEASTRALTR000...065`) é usada para buscar a rúbrica no CadastroCompleto.

---

## Planilha de entrada

**Colunas utilizadas:** CNPJ, EVENTO, EVENTO_AUX, IRRF, TABELA, DEMISSÃO, CPF, COMPETENCIA

**Filtros na leitura:**
- `DEMISSÃO = SIM` → status "Demissão", pula
- `CPF` vazio → status "CPF em branco", pula

**Agrupamento:** por CNPJ → lista de eventos, cada evento com lista de colaboradores (CPF + competência) em ordem de aparição na planilha.

---

## Algoritmo principal

```
Para cada CNPJ:
  selecionar_empresa(cnpj)
  Extrair GUID da home (link Rubrica/CadastroCompleto?id=xxx)

  Para cada evento do CNPJ:
    pendente = True

    # Fase 1: colaboradores da própria linha do evento
    Para cada colaborador do evento (CPF, competência):
      resultado = tentar_encontrar_rubrica(cpf, competencia, evento, evento_aux, tabela)
      Se encontrou:
        pendente = False
        colaborador_encontrado = (cpf, competencia)
        break

    # Fase 2: fallback — todos colaboradores da empresa × 12/2024–12/2025
    Se ainda pendente:
      Para cada cpf único da empresa, para cada mes em 12/2024–12/2025:
        resultado = tentar_encontrar_rubrica(cpf, mes, evento, evento_aux, tabela)
        Se encontrou:
          pendente = False
          colaborador_encontrado = (cpf, mes)
          break

    Se ainda pendente:
      registrar("Não encontrado")
      continue

    # Validação de domínio
    Se len(codigo_rubrica) < 28:
      registrar("Rúbrica não é do domínio")
      continue

    # Buscar idRubrica
    POST buscar_rubrica(guid, codigo_rubrica)
    → parsear → idRubrica, idEvento

    # Abrir form de edição
    GET abrir_edicao_rubrica(idRubrica, idEvento)
    → parsear → todos os campos + irrf_atual + __RequestVerificationToken

    # Validar IRRF
    Se irrf_atual == irrf_planilha:
      registrar("OK — já correto", codigo_antes=irrf_atual, codigo_depois=irrf_atual)
      continue

    # Corrigir IRRF
    POST salvar_edicao(todos_campos, CodigoIncidenciaIR=irrf_planilha)
    → 302 → /Assinadoc
    GET /Assinadoc → extrair link .jnlp
    Baixar .jnlp para pasta temp
    subprocess.run(["javaws", arquivo_jnlp], timeout=120)

    Se sucesso:
      registrar("Atualizado", codigo_antes=irrf_atual, codigo_depois=irrf_planilha)
    Se falhou (javaws não encontrado ou timeout):
      registrar("jnlp não assinado")

  trocar_perfil()
```

**Otimização de colaborador:** ao carregar a tabela de um colaborador, tenta resolver TODOS os eventos pendentes da empresa de uma vez — evita requests repetidas.

---

## Planilha de saída

**Arquivo:** `resultado_irrf_YYYYMMDD_HHMMSS.xlsx`

**Colunas:**

| Empresa | Evento | Código Rúbrica | IRRF antes | IRRF depois | Colaborador (CPF) | Competência | Status |
|---|---|---|---|---|---|---|---|

**Valores de Status:**
- `OK` — IRRF já estava correto
- `Atualizado` — IRRF corrigido e .jnlp assinado
- `Demissão` — linha ignorada por DEMISSÃO=SIM
- `CPF em branco` — linha ignorada por CPF vazio
- `Rúbrica não é do domínio` — código com menos de 28 caracteres
- `Não encontrado` — rúbrica não achada em nenhum colaborador/competência
- `jnlp não assinado` — POST feito mas assinatura falhou

---

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `passo_3/planilha.py` | Lê planilha de entrada, filtra, agrupa por CNPJ→eventos→colaboradores |
| `passo_3/parser.py` | Parseia HTML: tabela funcionário, busca rúbrica, form edição, link jnlp, GUID home |
| `passo_3/cookie.py` | Todas as funções HTTP (já existe, adicionar: salvar_edicao, baixar_jnlp, extrair_guid_home) |
| `passo_3/main.py` | Loop principal: empresa → eventos → validar/corrigir → planilha resultado |
| `passo_3/resultado_irrf_*.xlsx` | Planilha de saída gerada a cada execução |

---

## Dependências

```
requests
openpyxl
beautifulsoup4
lxml (parser BS4)
```
