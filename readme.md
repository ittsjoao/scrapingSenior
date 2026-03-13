# scrapingSenior (descontinuado)

Automação para validar e corrigir códigos de incidência IRRF de rubricas no portal eSocial, a partir de holerites gerados pelo sistema Senior.

## O que o projeto faz

O fluxo opera em 3 etapas:

1. **Scanner** (`scanner/scanner_holerites.py`) — extrai nomes, CPFs e eventos dos PDFs/CSVs de holerite gerados pelo Senior, produzindo um JSON estruturado.
2. **Validador** (`validador/validador_esocial.py`) — navega no portal eSocial via HTTP autenticado, localiza cada rubrica, compara o código IRRF atual com o esperado (definido em `esocial.csv`) e marca como `CORRETO` ou `ERRADO`.
3. **Corretor** (`corretor/corretor.py`) — para cada rubrica marcada como `ERRADO`, atualiza o código no portal e dispara a assinatura digital via JNLP.

## Por que foi descontinuado

### 1. Rate limiting severo do portal eSocial

O portal não expõe uma API pública — toda interação é feita via scraping de páginas HTML com sessão autenticada por cookies. Após ~500 requests com 10 workers paralelos, o tempo de resposta degrada para **~20 segundos por request**. Considerando que o volume de trabalho gira em torno de **~100k requests**, o tempo total estimado seria de **~23 dias ininterruptos** de execução — inviável.

Foram implementados mecanismos de throttle adaptativo (delays por worker, pausas coletivas de 2 min quando todos os workers ficam lentos, pausa de 5 min a cada 1000 requests), mas nenhuma estratégia foi suficiente para contornar a degradação do lado do servidor.

### 2. Dependência da API SeniorX

Para saber **quais funcionários tiveram quais eventos em quais competências**, o projeto depende de dados estruturados vindos do ERP Senior. Sem a API do SeniorX configurada, a alternativa é extrair essas informações dos PDFs de holerite via `pdfplumber` — um processo frágil que depende do layout exato do PDF e quebra com qualquer mudança de formato.

### 3. Sessão HTTP instável

O portal eSocial utiliza load balancer sem sticky sessions. Isso significa que após selecionar uma empresa, requisições subsequentes podem cair em outro servidor que não reconhece a sessão. O workaround implementado (retry de seleção de empresa até 9 vezes até o cookie bater com o servidor correto) funciona, mas adiciona latência e fragilidade ao processo.

### 4. Assinatura digital via JNLP

A etapa de correção depende do Java Web Start (`javaws`) para executar a assinatura digital. Além de ser uma tecnologia descontinuada, a execução automatizada do JNLP é inerentemente instável e difícil de monitorar programaticamente.

### 5. Fragilidade da extração de dados

A identificação de eventos nos holerites depende de regex e posicionamento de texto no PDF. Nomes de funcionários, CPFs e códigos de eventos são extraídos com heurísticas que assumem um formato específico do documento. Qualquer alteração no template do holerite quebra a extração.

## Estrutura

```
scanner/          # Etapa 1: extração de eventos dos holerites
validador/        # Etapa 2: validação no portal eSocial
corretor/         # Etapa 3: correção de rubricas incorretas
lib/              # Utilitários (HTTP/cookies, parsing HTML)
dados/entrada/    # CSVs de configuração (empresas, eventos, colaboradores)
dados/saida/      # Holerites por empresa e JSONs de resultado
```

## Caso queira continuar

O projeto funciona para volumes pequenos (< 500 requests). Para volumes maiores, seria necessário:

- Acesso a uma API oficial do eSocial (ou uma alternativa ao scraping)
- Integração direta com a API do SeniorX para eliminar a extração de PDFs
- Distribuição de requests por múltiplos IPs/sessões para contornar o rate limiting
