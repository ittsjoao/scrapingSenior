# passo_3/parser.py
import re
from bs4 import BeautifulSoup


def extrair_guid_home(html):
    """
    Extrai o GUID da página home da empresa.
    Procura por link href contendo 'Rubrica/CadastroCompleto?id='.
    Retorna string GUID ou None.
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        m = re.search(r"Rubrica/CadastroCompleto\?id=([a-f0-9\-]+)", href, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


_TABELA_INDEX = {"HOLERITE": 0, "FÉRIAS": 1}


def parsear_tabela_funcionario(html, evento, evento_aux, tabela_esperada):
    """
    Parseia a(s) tabela(s) de rúbricas de um funcionário.

    tabela_esperada pode ser:
      - "HOLERITE" → busca apenas na 1ª tabela sem-paginacao da página
      - "FÉRIAS"   → busca apenas na 2ª tabela sem-paginacao da página
      - ""         → busca em todas as tabelas

    Retorna código da rúbrica (coluna "Código") ou None.
    """
    soup = BeautifulSoup(html, "lxml")
    todas = soup.find_all("table", class_=lambda c: c and "sem-paginacao" in c)
    if not todas:
        return None

    chave = tabela_esperada.strip().upper() if tabela_esperada else ""
    if chave in _TABELA_INDEX:
        idx = _TABELA_INDEX[chave]
        tabelas = [todas[idx]] if idx < len(todas) else []
    else:
        tabelas = todas

    for tabela in tabelas:
        for tr in tabela.find_all("tr")[1:]:  # pula cabeçalho
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue
            col_codigo    = tds[1].get_text(strip=True)
            col_descricao = tds[3].get_text(strip=True).upper()
            if evento.upper() in col_descricao or (evento_aux and evento_aux.upper() in col_descricao):
                return col_codigo

    return None


def parsear_busca_rubrica(html):
    """
    Parseia o HTML retornado pelo POST de busca de rúbrica.
    Retorna (id_rubrica, id_evento) ou (None, None).

    Procura links com href contendo 'Editar?idRubrica=...&idEvento=...'
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        m = re.search(r"idRubrica=(\d+)&idEvento=(\d+)", href)
        if m:
            return m.group(1), m.group(2)
    return None, None


def parsear_form_edicao(html):
    """
    Parseia o formulário de edição de uma rúbrica.
    Retorna dict com todos os campos do form necessários para o POST de salvar,
    incluindo '__RequestVerificationToken' e 'DadosRubrica.CodigoIncidenciaIR'.

    Retorna None se o form não for encontrado.
    """
    soup = BeautifulSoup(html, "lxml")

    # Localiza o form de edição (action contém 'Editar')
    form = None
    for f in soup.find_all("form"):
        action = f.get("action", "")
        if "Editar" in action:
            form = f
            break

    if not form:
        # Tenta qualquer form com o token
        form = soup.find("form")

    if not form:
        return None

    campos = {}

    # Coleta todos inputs, selects e textareas
    for inp in form.find_all(["input", "select", "textarea"]):
        name = inp.get("name")
        if not name:
            continue

        tag = inp.name
        if tag == "select":
            # Pega o option selecionado
            selected = inp.find("option", selected=True)
            value = selected["value"] if selected and selected.get("value") else ""
        elif tag == "input":
            tipo = inp.get("type", "text").lower()
            if tipo == "checkbox":
                value = inp.get("value", "on") if inp.get("checked") else None
                if value is None:
                    continue
            elif tipo == "radio":
                if not inp.get("checked"):
                    continue
                value = inp.get("value", "")
            else:
                value = inp.get("value", "")
        else:  # textarea
            value = inp.get_text()

        # Campos com mesmo nome (ex: FormularioProcesso) → lista
        if name in campos:
            if not isinstance(campos[name], list):
                campos[name] = [campos[name]]
            campos[name].append(value)
        else:
            campos[name] = value

    # Garante campo obrigatório de submit
    if "editar:rubrica" not in campos:
        campos["editar:rubrica"] = "Salvar"

    return campos


def extrair_link_jnlp(html):
    """
    Extrai o link de download do arquivo .jnlp da página Assinadoc.
    Retorna URL completa ou None.
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.endswith(".jnlp") or ".jnlp" in href:
            if href.startswith("http"):
                return href
            return "https://www.esocial.gov.br" + href
    # fallback: busca em qualquer atributo
    m = re.search(r'(https?://[^\s"\']+\.jnlp)', html)
    if m:
        return m.group(1)
    return None
