# Performance Optimization — Smart Skip + Rate Control

## Problem

With 10 parallel workers scraping eSocial, requests degrade from 1-2s to 10-30s after a few minutes. Root cause: combinatorial explosion of unnecessary requests (up to 7,476 per large company) triggering server-side rate limiting.

## Solution

### 1. Early-exit per CPF
If a CPF returns no data for 3 consecutive recent months, skip remaining months.
- Before: 14 months × 2 requests = 28 wasted requests per inactive CPF
- After: 3 months × 2 requests = 6 requests, then skip

### 2. Cache `acessar_lista_remuneracao` in auditor.py
Cache by `(guid, mes)` — one request per company/month is enough. main.py already does this; auditor.py doesn't.

### 3. Adaptive throttle
Measure response times. If >5s, add incremental backoff (1s→2s sleep). Reduce delay when responses return to <3s.

### 4. Reduce month range
Default to 10 months (stop at 03/2025) instead of 14. Configurable.

## Files Changed
- `auditor.py` — cache, early-exit, month skip
- `cookie.py` — timing wrapper for adaptive throttle
- `auditor_parallel.py` — pass throttle config to workers

## Impact
Estimated 60-80% reduction in total requests.
