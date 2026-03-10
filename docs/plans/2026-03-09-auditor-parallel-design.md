# Design: Auditor Paralelo de Rúbricas eSocial

**Data:** 2026-03-09
**Escopo:** `passo_3/auditor_parallel.py` (novo)

## Contexto

`auditor.py` processa 182 empresas sequencialmente. Com ~5000 CPFs distribuídos entre elas, o tempo total é proibitivo. A paralelização com N workers independentes (um por sessão do Firefox) reduz o tempo em ~N×.

## Decisões de Design

| Decisão | Escolha | Motivo |
|---|---|---|
| Modelo de concorrência | `multiprocessing` | Isolamento total de cookies/sessão por processo |
| Distribuição de CNPJs | `multiprocessing.Queue` dinâmica | Equilibra carga automaticamente |
| Saída JSON | Arquivo compartilhado + `multiprocessing.Lock` | Resume único, sem merge manual |
| Cookies | `passo_3/cookies/worker_N.txt` | Auto-detecção do número de workers |
| Lock granularity | Apenas na leitura+escrita do JSON (~50ms) | Workers auditam em paralelo sem bloqueio |

## Estrutura de Arquivos

```
passo_3/
  auditor_parallel.py   ← novo
  auditor.py            ← sem alteração
  cookies/
    worker_1.txt        ← uma sessão Firefox por arquivo
    worker_2.txt
    worker_N.txt

dados/saida/
  auditoria_TIMESTAMP.json   ← compartilhado entre workers
```

## Fluxo

### Orquestrador (`main`)

```
1. Glob passo_3/cookies/worker_*.txt → lista de N cookies_paths
2. Carregar CNPJs do CSV → multiprocessing.Queue
3. Criar multiprocessing.Lock
4. Determinar caminho JSON (novo ou --retomar → mais recente)
5. Criar JSON vazio se novo
6. Disparar N Process(target=worker, args=(id, cookies_path, queue, lock, json_path))
7. p.join() para todos
8. Imprimir resumo (total auditados, ERRADO, CORRETO, N/A)
```

### Worker

```
1. Criar requests.Session com cookies_path
2. Extrair usuario_logado_procurador e cpf_procurador dos cookies
3. Loop:
   a. queue.get_nowait() → cnpj (QueueEmpty → encerra)
   b. [lock] ler JSON → se cnpj já presente → continue
   c. selecionar_empresa(session, cnpj)
   d. Auditar empresa (reutiliza auditar_empresa de auditor.py)
   e. [lock] ler JSON → adicionar resultado → salvar JSON
   f. trocar_perfil(session, ...)
```

## Detalhe: Lock Granular

O lock é adquirido **somente** para operações de leitura+escrita no JSON (≈50ms). A auditoria de cada empresa (que pode levar 30–120s) ocorre fora do lock — todos os workers auditam em paralelo.

```
Worker 1: ──[audita A: 45s]──[🔒 salva: 50ms]──[audita D: 30s]──
Worker 2: ──[audita B: 30s]──[🔒 salva: 50ms]──[audita E: 60s]──
Worker 3: ──[audita C: 60s]──[🔒 salva: 50ms]──[audita F: 45s]──
```

## Resume com Paralelo

`--retomar` detecta o JSON mais recente em `dados/saida/`. Antes de cada empresa, o worker adquire o lock, lê o JSON e verifica se o CNPJ já consta. Se sim, descarta e busca o próximo na fila. Correto mesmo com N workers simultâneos pois a verificação é dentro do lock.

## Uso

```bash
# Preparar sessões: uma janela Firefox por worker, exportar cookies
# passo_3/cookies/worker_1.txt, worker_2.txt, ..., worker_N.txt

cd passo_3
python auditor_parallel.py            # inicia do zero
python auditor_parallel.py --retomar  # continua JSON mais recente
```

## O que NÃO muda

- `auditor.py`, `corretor.py`, `cookie.py`, `parser.py`, `entradas.py`, `main.py` — sem alteração.
- `auditar_empresa()` de `auditor.py` é importada diretamente.
- `corretor.py` continua funcionando sobre o mesmo JSON gerado.
