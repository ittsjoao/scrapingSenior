# Como usar o Auditor Paralelo

## Preparar sessões do Firefox

1. Abra N janelas do Firefox, cada uma logada no eSocial com o certificado
2. Em cada janela, exporte os cookies (extensão "Export Cookies" ou similar)
3. Salve em `passo_3/cookies/`:
   - `worker_1.txt`
   - `worker_2.txt`
   - ... até `worker_N.txt`

O número de workers é detectado automaticamente pelo número de arquivos.

## Executar

```bash
cd passo_3

# Iniciar do zero (cria novo JSON em dados/saida/)
python auditor_parallel.py

# Retomar após interrupção (continua o JSON mais recente)
python auditor_parallel.py --retomar

# Versão sequencial (1 sessão, sem paralelismo)
python auditor.py
python auditor.py --retomar
```

## Depois da auditoria

```bash
# Corrigir rúbricas ERRADAS (usa o JSON mais recente automaticamente)
python corretor.py

# Ou especificando o arquivo
python corretor.py ../dados/saida/auditoria_20260309_230000.json
```

## Observações

- `passo_3/cookies/*.txt` não são commitados no git (estão no .gitignore)
- O JSON de saída é compartilhado entre os workers com lock — sem risco de corrupção
- Se um worker cair, o `--retomar` garante que as empresas já auditadas sejam puladas
- O `corretor.py` funciona sobre o mesmo JSON gerado pelo auditor paralelo
