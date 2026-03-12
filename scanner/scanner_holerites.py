#!/usr/bin/env python3
"""
scanner/scanner_holerites.py

Varre holerites locais para identificar colaboradores com eventos específicos.
Período: 11/2024 a 12/2025

Fontes por ordem de preferência por competência:
  1. HOLERITES.pdf ou HOLERITE.pdf  (contém todos os eventos)
  2. CSV de folha (fallback — apenas eventos configurados no export)

Saída: dados/saida/scanner_TIMESTAMP.json
"""

import os
import csv
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    import pdfplumber
    PDF_DISPONIVEL = True
except ImportError:
    PDF_DISPONIVEL = False
    print("[AVISO] pdfplumber não instalado. Meses sem CSV serão ignorados.")
    print("        Instale com: pip install pdfplumber\n")

BASE_DIR = Path(__file__).parent.parent
DADOS_SAIDA = BASE_DIR / "dados" / "saida"
DADOS_ENTRADA = BASE_DIR / "dados" / "entrada"

# Período: 11/2024 a 12/2025 (em ordem cronológica)
COMPETENCIAS = []
for _ano in [2024, 2025]:
    for _mes in range(1, 13):
        if _ano == 2024 and _mes < 11:
            continue
        COMPETENCIAS.append((_mes, _ano))


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def normalizar(texto: str) -> str:
    """Remove acentos e normaliza para comparação (upper, sem duplos espaços)."""
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', texto).strip().upper()


def _extrair_cpf_pagina(texto: str) -> str:
    """
    Extrai o CPF do texto de uma página de holerite.
    Tenta primeiro CPF formatado (NNN.NNN.NNN-NN), depois 11 dígitos contíguos.
    Retorna string com apenas dígitos (11 chars) ou "" se não encontrado.
    """
    # 1. CPF formatado: NNN.NNN.NNN-NN
    m = re.search(r"\b(\d{3})[.\s](\d{3})[.\s](\d{3})[-\s](\d{2})\b", texto)
    if m:
        return m.group(1) + m.group(2) + m.group(3) + m.group(4)
    # 2. 11 dígitos contíguos (não precedidos/seguidos de mais dígitos)
    for m in re.finditer(r"(?<!\d)(\d{11})(?!\d)", texto):
        candidato = m.group(1)
        # Descarta sequências triviais como 00000000000 ou 11111111111
        if len(set(candidato)) > 1:
            return candidato
    return ""


# ---------------------------------------------------------------------------
# Carregamento de dados de entrada
# ---------------------------------------------------------------------------

def carregar_empresas() -> dict:
    """
    Retorna dict com lookups múltiplos por:
      nome_normalizado  → info
      'ID:{id_empresa}' → info
      'CNPJ:{cnpj}'     → info  (apenas dígitos)
    """
    empresas = {}
    with open(DADOS_ENTRADA / "empresas.csv", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            info = {
                "id_empresa": row["id_empresa"].strip(),
                "cnpj": re.sub(r"\D", "", row["cnpj"].strip()),
                "nome_empresa": row["nome_empresa"].strip(),
            }
            nome_n = normalizar(row["nome_empresa"])
            id_emp = row["id_empresa"].strip()
            cnpj = re.sub(r"\D", "", row["cnpj"].strip())

            empresas[nome_n] = info
            empresas[f"ID:{id_emp}"] = info
            if cnpj:
                empresas[f"CNPJ:{cnpj}"] = info
    return empresas


def carregar_eventos_alvo() -> list:
    """
    Carrega eventos alvo diretamente do esocial.csv.
    Eventos com múltiplas linhas (mesmo id_evento, tabelas diferentes)
    são deduplicados — apenas a primeira ocorrência é usada para busca no PDF.

    Retorna lista de dicts:
      id_evento, nome_evento, nome_esocial, nome_esocial_aux, col_prefixo
    """
    eventos = []
    vistos: set = set()
    with open(DADOS_ENTRADA / "esocial.csv", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            id_ev = row["id_evento"].strip()
            if not id_ev or id_ev in vistos:
                continue
            vistos.add(id_ev)
            nome_esocial = row.get("nome_esocial", "").strip()
            eventos.append({
                "id_evento": id_ev,
                "nome_evento": nome_esocial,
                "nome_esocial": nome_esocial,
                "nome_esocial_aux": row.get("nome_esocial_aux", "").strip(),
                "col_prefixo": id_ev.zfill(5),  # "00216" para FPLA150
            })
    return eventos


# ---------------------------------------------------------------------------
# Identificação de empresa
# ---------------------------------------------------------------------------

def encontrar_empresa(pasta_nome: str, empresas: dict, folha_path: Path | None = None) -> dict | None:
    """
    Tenta encontrar a empresa:
      1. Pelo nome da pasta (match exato ou parcial normalizado)
      2. Lendo linha 0 do primeiro CSV disponível (id_empresa ou nome)
    """
    nome_n = normalizar(pasta_nome)

    if nome_n in empresas:
        return empresas[nome_n]

    # Match parcial: pasta ⊆ empresa ou empresa ⊆ pasta
    for key, emp in empresas.items():
        if key.startswith(("ID:", "CNPJ:")):
            continue
        if nome_n in key or key in nome_n:
            return emp

    # Fallback: ler linha 0 do primeiro CSV da empresa
    if folha_path and folha_path.exists():
        for csv_file in folha_path.rglob("*.csv"):
            emp = _empresa_de_csv(csv_file, empresas)
            if emp:
                return emp

    return None


def _empresa_de_csv(csv_path: Path, empresas: dict) -> dict | None:
    """Extrai id_empresa e nome da linha 0 do CSV de folha."""
    try:
        with open(csv_path, encoding="utf-8", errors="ignore") as f:
            linha0 = f.readline().strip()
        # Formato: "0;dez/24;85;2245;153 TECNOLOGIA LTDA"
        if not linha0.startswith("0;"):
            return None
        partes = [p.strip() for p in linha0.split(";")]
        if len(partes) >= 5:
            id_emp = partes[3]
            nome_csv = partes[4]
            if f"ID:{id_emp}" in empresas:
                return empresas[f"ID:{id_emp}"]
            nome_n = normalizar(nome_csv)
            if nome_n in empresas:
                return empresas[nome_n]
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Parsing de CSV
# ---------------------------------------------------------------------------

def encontrar_csv_folha(comp_path: Path) -> Path | None:
    """
    Retorna o CSV de folha mais adequado na pasta de competência.
    Preferência: FPLA150*.csv → qualquer .csv no formato 0;/1;/2;
    Ignora arquivos que não seguem o formato de folha.
    """
    candidatos = list(comp_path.glob("FPLA150*.csv"))
    if not candidatos:
        candidatos = list(comp_path.glob("*.csv"))

    for c in sorted(candidatos):
        try:
            with open(c, encoding="utf-8", errors="ignore") as f:
                primeira = f.readline()
            if primeira.startswith("0;") and primeira.count(";") >= 3:
                return c
        except Exception:
            continue
    return None


def parse_csv_folha(csv_path: Path, eventos: list) -> list:
    """
    Extrai colaboradores que possuem os eventos alvo.
    Retorna lista de {cadastro, nome, eventos}.

    Formato esperado:
      Linha 0 (id=0): metadados
      Linha 1 (id=1): headers  → "1;Empresa;Tipo;Cadastro;Nome;Admissao;Cargo;NNNNN-EVENTO;..."
      Linhas 2+(id=2): dados   → "2;id_emp;tipo;cadastro;nome;admissao;cargo;val;val;..."
    """
    try:
        with open(csv_path, encoding="utf-8", errors="ignore") as f:
            linhas = f.readlines()
    except Exception as e:
        print(f"    [ERRO CSV] {csv_path.name}: {e}")
        return []

    if len(linhas) < 2:
        return []

    # Localizar linha de headers (começa com "1;")
    header_idx = None
    for i, linha in enumerate(linhas[:6]):
        if linha.startswith("1;"):
            header_idx = i
            break
    if header_idx is None:
        return []

    headers = [h.strip() for h in linhas[header_idx].split(";")]

    # Mapear colunas dos eventos alvo
    # Formato da coluna: "00216-MÉDIAS VARIAVEIS 13 INTEGRADO"
    target_cols: dict[int, str] = {}  # índice → id_evento
    for ev in eventos:
        prefixo = ev["col_prefixo"]  # ex: "00216"
        for i, h in enumerate(headers):
            h_clean = h.strip()
            if h_clean.startswith(prefixo + "-") or h_clean.startswith(prefixo + " "):
                target_cols[i] = ev["id_evento"]
                break

    if not target_cols:
        return []

    # Índices fixos dos campos de identificação do colaborador:
    # headers: [0]"1" [1]"Empresa" [2]"Tipo" [3]"Cadastro" [4]"Nome" [5]"Admissao" [6]"Cargo" [7+]eventos
    IDX_CADASTRO = 3
    IDX_NOME = 4

    resultados = []
    for linha in linhas[header_idx + 1:]:
        if not linha.startswith("2;"):
            continue
        cols = [c.strip() for c in linha.split(";")]
        if len(cols) <= max(target_cols.keys(), default=0):
            continue

        cadastro = cols[IDX_CADASTRO] if IDX_CADASTRO < len(cols) else ""
        nome = cols[IDX_NOME] if IDX_NOME < len(cols) else ""

        evs_encontrados = []
        for col_idx, id_ev in target_cols.items():
            if col_idx < len(cols):
                val = cols[col_idx].replace(",", ".").strip()
                try:
                    if val and float(val) != 0.0:
                        evs_encontrados.append(id_ev)
                except ValueError:
                    pass

        if evs_encontrados:
            resultados.append({
                "cadastro": cadastro,
                "nome": nome,
                "eventos": evs_encontrados,
            })

    return resultados


# ---------------------------------------------------------------------------
# Parsing de PDF
# ---------------------------------------------------------------------------

def parse_pdf_holerite(pdf_path: Path, eventos: list) -> list:
    """
    Extrai colaboradores com eventos alvo do PDF de holerites.
    Cada página = um colaborador (formato padrão Senior ERP).
    Busca por nome_esocial_aux → nome_esocial → nome_evento.
    Retorna lista de {cadastro, nome, eventos}.
    """
    if not PDF_DISPONIVEL:
        return []

    # Montar termos de busca por ordem de confiança
    termos_busca: list[tuple[str, str]] = []
    for ev in eventos:
        for campo in ("nome_esocial_aux", "nome_esocial", "nome_evento"):
            n = ev.get(campo, "").strip()
            if n:
                n_norm = normalizar(n)
                if n_norm and (n_norm, ev["id_evento"]) not in termos_busca:
                    termos_busca.append((n_norm, ev["id_evento"]))

    resultados = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text() or ""
                if not texto.strip():
                    continue

                linhas = texto.splitlines()
                texto_n = normalizar(texto)

                # ── Extrair nome do colaborador ──────────────────────────────
                # Formato Senior ERP:
                #   "NOME CARGO DATA ADMISSÃO  NOME CARGO DATA ADMISSÃO"  ← cabeçalho duplicado
                #   "FULANO DE TAL  Cargo Misto 01/01/2024  FULANO DE TAL ..."  ← dado
                #
                # O nome está em MAIÚSCULAS; o cargo começa com letra maiúscula
                # seguida de minúsculas. Usamos o texto original (antes de normalizar)
                # para distinguir maiúsculas/minúsculas.
                nome_colab = ""
                cadastro = ""
                cpf_colab = _extrair_cpf_pagina(texto)

                nome_header_idx = None
                for i, linha in enumerate(linhas):
                    if "NOME" in linha and "CARGO" in linha and "ADMISS" in linha:
                        nome_header_idx = i
                        break

                if nome_header_idx is not None and nome_header_idx + 1 < len(linhas):
                    linha_nome = linhas[nome_header_idx + 1].strip()
                    # Nome = sequência de palavras MAIÚSCULAS antes do cargo (misto)
                    # Cargo começa onde aparece letra minúscula após palavra maiúscula
                    m_nome = re.match(r"^([A-ZÁÀÂÃÉÈÊÍÎÓÔÕÚÇÜÑ][A-ZÁÀÂÃÉÈÊÍÎÓÔÕÚÇÜÑ\s.]+?)\s+(?=[A-ZÁÀÂÃÉÈÊÍÎÓÔÕÚÇÜÑ][a-záàâãéèêíîóôõúçüñ(]|\d)", linha_nome)
                    if m_nome:
                        nome_colab = m_nome.group(1).strip()
                    elif linha_nome:
                        # Fallback: pegar até a primeira data (DD/MM/AAAA)
                        m_data = re.match(r"^(.+?)\s+\d{2}/\d{2}/\d{4}", linha_nome)
                        if m_data:
                            # Remove o cargo no final — fica com tudo antes da data
                            candidato = m_data.group(1).strip()
                            # Tenta extrair só a parte em MAIÚSCULAS do início
                            m_nome2 = re.match(r"^([A-ZÁÀÂÃÉÈÊÍÎÓÔÕÚÇÜÑ][A-ZÁÀÂÃÉÈÊÍÎÓÔÕÚÇÜÑ\s.]+)", candidato)
                            nome_colab = m_nome2.group(1).strip() if m_nome2 else candidato

                # Extrair cadastro do cabeçalho (ex: "Cadastro: 46" ou da linha da empresa)
                for linha in linhas[:20]:
                    m_cad = re.search(r"(?:CADASTRO|MATR[IÍ]CULA|MAT\.?)[:\s]*(\d+)", normalizar(linha))
                    if m_cad:
                        cadastro = m_cad.group(1)
                        break

                # ── Verificar eventos na página ──────────────────────────────
                # Para cada evento, busca pelo código (ex: "216 ") ou pelos nomes
                evs_encontrados = []

                for ev in eventos:
                    id_ev = ev["id_evento"]
                    if id_ev in evs_encontrados:
                        continue

                    # 1. Busca pelo código numérico: "216 DESCRICAO REFERENCIA VALOR"
                    cod_padrao = re.compile(
                        r"(?:^|\s)0*" + re.escape(id_ev) + r"\s+\S.{0,50}?(\d[\d.]*,\d{2})",
                        re.MULTILINE,
                    )
                    m_cod = cod_padrao.search(texto_n)
                    if m_cod:
                        val_str = m_cod.group(1).replace(".", "").replace(",", ".")
                        try:
                            if float(val_str) != 0.0:
                                evs_encontrados.append(id_ev)
                                continue
                        except ValueError:
                            evs_encontrados.append(id_ev)
                            continue

                    # 2. Busca pelos nomes eSocial
                    for campo in ("nome_esocial_aux", "nome_esocial", "nome_evento"):
                        nome_ev = ev.get(campo, "").strip()
                        if not nome_ev:
                            continue
                        termo = normalizar(nome_ev)
                        idx = texto_n.find(termo)
                        if idx >= 0:
                            # Verifica valor não-zero logo após o nome
                            trecho = texto_n[idx: idx + len(termo) + 40]
                            m_val = re.search(r"(\d[\d.]*,\d{2})", trecho)
                            if m_val:
                                val_str = m_val.group(1).replace(".", "").replace(",", ".")
                                try:
                                    if float(val_str) != 0.0:
                                        evs_encontrados.append(id_ev)
                                        break
                                except ValueError:
                                    evs_encontrados.append(id_ev)
                                    break
                            else:
                                evs_encontrados.append(id_ev)
                                break

                if evs_encontrados and nome_colab:
                    resultados.append({
                        "cadastro": cadastro,
                        "cpf": cpf_colab,
                        "nome": nome_colab,
                        "eventos": evs_encontrados,
                    })

    except Exception as e:
        print(f"    [ERRO PDF] {pdf_path.name}: {e}")

    return resultados


# ---------------------------------------------------------------------------
# Processamento de competência
# ---------------------------------------------------------------------------

def processar_competencia(comp_path: Path, eventos: list) -> tuple[list, str | None]:
    """
    Tenta HOLERITE PDF primeiro (contém TODOS os eventos).
    Fallback para CSV de folha (contém apenas eventos configurados no export).
    Retorna (lista_matches, fonte) onde fonte é 'pdf', 'csv' ou None.
    """
    # 1. Preferência: HOLERITES.pdf ou HOLERITE.pdf (têm todos os eventos)
    for nome_pdf in ("HOLERITES.pdf", "HOLERITE.pdf"):
        pdf_path = comp_path / nome_pdf
        if pdf_path.exists():
            matches = parse_pdf_holerite(pdf_path, eventos)
            return matches, "pdf"

    # 2. Fallback: CSV de folha
    csv_path = encontrar_csv_folha(comp_path)
    if csv_path:
        matches = parse_csv_folha(csv_path, eventos)
        return matches, "csv"

    return [], None


# ---------------------------------------------------------------------------
# Entry point principal
# ---------------------------------------------------------------------------

def scan():
    print("=" * 55)
    print("  Scanner de Holerites")
    print(f"  Periodo: 11/2024 -> 12/2025 ({len(COMPETENCIAS)} competencias)")
    print("=" * 55)

    empresas = carregar_empresas()
    eventos = carregar_eventos_alvo()

    if not eventos:
        print("[ERRO] Nenhum evento em dados/entrada/eventos.csv")
        return {}

    print("\nEventos alvo:")
    for ev in eventos:
        print(f"  [{ev['id_evento']}] {ev['nome_evento']}")
        if ev["nome_esocial"]:
            print(f"        eSocial: {ev['nome_esocial']} / {ev['nome_esocial_aux']}")
    print()

    resultados: dict = {}
    stats = {"processadas": 0, "puladas": 0, "matches_total": 0}

    for pasta in sorted(os.listdir(DADOS_SAIDA)):
        pasta_path = DADOS_SAIDA / pasta

        # Ignorar arquivos e resultados anteriores
        if not pasta_path.is_dir():
            continue
        if any(pasta.startswith(p) for p in ("scanner_", "auditoria_", "validacao_")):
            continue

        folha_path = pasta_path / "FOLHA DE PAGAMENTO"
        empresa_info = encontrar_empresa(pasta, empresas, folha_path)

        if not empresa_info:
            stats["puladas"] += 1
            print(f"[SKIP] {pasta}")
            continue

        stats["processadas"] += 1
        id_emp = empresa_info["id_empresa"]
        print(
            f"\n[{stats['processadas']}] {pasta}\n"
            f"     -> ID:{id_emp} | CNPJ:{empresa_info['cnpj']} | {empresa_info['nome_empresa']}"
        )

        if not folha_path.exists():
            print("     Sem pasta 'FOLHA DE PAGAMENTO'")
            continue

        matches_empresa = []

        for mes, ano in COMPETENCIAS:
            comp_str = f"{mes:02d}-{ano}"
            comp_path = folha_path / str(ano) / comp_str

            if not comp_path.exists():
                continue

            colabs, fonte = processar_competencia(comp_path, eventos)

            if colabs:
                print(f"     ✓ {comp_str}: {len(colabs)} colaborador(es) [{fonte}]")
                for c in colabs:
                    matches_empresa.append(
                        {
                            "competencia": f"{mes:02d}/{ano}",
                            "cadastro": c.get("cadastro", ""),
                            "cpf": c.get("cpf", ""),
                            "nome": c["nome"],
                            "eventos": c["eventos"],
                        }
                    )
                    stats["matches_total"] += 1
            else:
                fonte_str = f" [{fonte}]" if fonte else " [sem arquivo]"
                print(f"     - {comp_str}: nenhum evento encontrado{fonte_str}")

        if matches_empresa:
            resultados[id_emp] = {
                "id_empresa": id_emp,
                "cnpj": empresa_info["cnpj"],
                "nome_empresa": empresa_info["nome_empresa"],
                "pasta": pasta,
                "colaboradores": matches_empresa,
            }

    # Salvar JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = DADOS_SAIDA / f"scanner_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 55}")
    print(f"Empresas processadas : {stats['processadas']}")
    print(f"Empresas puladas     : {stats['puladas']}")
    print(f"Total de matches     : {stats['matches_total']}")
    print(f"Arquivo salvo        : {output_path.name}")
    print("=" * 55)

    return resultados


if __name__ == "__main__":
    scan()
