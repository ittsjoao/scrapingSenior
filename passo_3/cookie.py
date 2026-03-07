import os
import re
import time
from urllib.parse import quote

import requests

COOKIES_FILE = "cookies.txt"
PASTA_SAIDA = "saida"
HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


def ler_cookies(arquivo):
    cookies = {}
    with open(arquivo, "r") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            if linha.startswith("#HttpOnly_"):
                linha = linha.replace("#HttpOnly_", "", 1)
            elif linha.startswith("#"):
                continue
            partes = linha.split("\t")
            if len(partes) >= 7:
                cookies[partes[5]] = partes[6]
    return cookies


def selecionar_empresa(session, cnpj_formatado):
    """
    POST para IndexProcuracao — o servidor retorna 302 + Set-Cookie UsuarioLogado.
    Fica tentando até cair no servidor certo (load balancer sem sticky session).
    Após sucesso, segue o redirect para consolidar a sessão naquele servidor.
    Retorna True se empresa selecionada com sucesso.
    """
    url = (
        f"https://www.esocial.gov.br/portal/Home/IndexProcuracao"
        f"?procuradorCnpj={quote(cnpj_formatado)}&procuradorCpf=&tipoEmpregador=geral"
    )
    data = {
        "perfil": "3",
        "trocarPerfil": "False",
        "podeSerMicroPequenaEmpresa": "False",
        "tipoInscricao": "2",
        "EhOrgaoPublico": "False",
        "logadoComCertificadoDigital": "True",
        "permitirRepresentanteLegal": "False",
        "perfilAcesso": "PROCURADOR_PJ",
        "procuradorCpf": "",
        "procuradorCnpj": cnpj_formatado,
        "representanteCnpj": "",
        "inscricao": "",
        "inscricaoJudiciario": "",
        "numeroProcessoJudiciario": "",
    }
    headers = {**HEADERS_BASE, "Referer": "https://www.esocial.gov.br/portal/"}

    match = None
    for tentativa in range(1, 100):
        resp = session.post(url, data=data, headers=headers, allow_redirects=False)
        set_cookie = resp.headers.get("Set-Cookie", "")
        match = re.search(r"UsuarioLogado=([^;]+)", set_cookie)
        if match:
            break
        print(
            f"  [!] Tentativa {tentativa} — servidor sem sessão (status {resp.status_code}), retentando..."
        )
        time.sleep(0.5)

    if not match:
        return False

    usuario_logado = match.group(1)

    # Seta UsuarioLogado da empresa na session
    session.cookies.set(
        "UsuarioLogado", usuario_logado, domain="www.esocial.gov.br", path="/"
    )

    # Atualiza usuario_logado_ws para o CNPJ da empresa (muda de CPF para CNPJ após seleção)
    session.cookies.set(
        "usuario_logado_ws", cnpj_formatado, domain="www.esocial.gov.br", path="/"
    )

    # Segue o redirect — consolida a sessão no servidor que respondeu ao POST
    location = resp.headers.get("Location", "")
    if location.startswith("/"):
        location = "https://www.esocial.gov.br" + location
    if location:
        session.get(location, headers=headers, allow_redirects=False)

    cnpj_digits = cnpj_formatado.replace(".", "").replace("/", "").replace("-", "")
    print(f"  [OK] Tentativa {tentativa} | UsuarioLogado: {usuario_logado[:80]}")
    return "NI=" in usuario_logado and cnpj_digits in usuario_logado


def trocar_perfil(session, usuario_logado_procurador, cpf_procurador):
    """
    Reseta o contexto de volta ao procurador após terminar uma empresa.
    Restaura os cookies do procurador e chama Index?trocarPerfil=true.
    Deve ser chamado após finalizar todas as requisições de uma empresa.
    """
    # Restaura cookies do procurador antes de chamar trocarPerfil
    session.cookies.set(
        "UsuarioLogado",
        usuario_logado_procurador,
        domain="www.esocial.gov.br",
        path="/",
    )
    session.cookies.set(
        "usuario_logado_ws", cpf_procurador, domain="www.esocial.gov.br", path="/"
    )

    headers = {
        **HEADERS_BASE,
        "Referer": "https://www.esocial.gov.br/portal/Home/Inicial?tipoEmpregador=EMPREGADOR_GERAL",
    }
    resp = session.get(
        "https://www.esocial.gov.br/portal/Home/Index?trocarPerfil=true",
        headers=headers,
        allow_redirects=True,
    )
    print(f"  [trocarPerfil] Status: {resp.status_code}")


def salvar_html(html, cnpj, nome_arquivo):
    """
    Salva o HTML em saida/<cnpj_digits>/<nome_arquivo>.html
    cnpj: string formatada ex '10.515.531/0001-70'
    nome_arquivo: ex 'tabela_mes_202512' ou 'funcionario_12345678900_202512'
    """
    cnpj_digits = cnpj.replace(".", "").replace("/", "").replace("-", "")
    pasta = os.path.join(PASTA_SAIDA, cnpj_digits)
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{nome_arquivo}.html")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [salvo] {caminho}")
    return caminho


def cookies_ativos(session):
    """Retorna dict com todos os cookies da session — útil para debug ou reuso."""
    return {c.name: c.value for c in session.cookies}


def acessar_tabela_funcionário(session, cpf, competencia, possui_dae="False"):
    """
    Acessa Lista de Rúbricas de um funcionário específico.
    Retorna o HTML da página ou None em caso de erro.
    """
    url = (
        f"https://www.esocial.gov.br/portal/FolhaPagamento/RemuneracaoCompleto"
        f"?cpf={cpf}&competencia={competencia}&PossuiDae={possui_dae}&tipo=1200&visualizar=True"
    )
    headers = {
        **HEADERS_BASE,
        "Referer": "https://www.esocial.gov.br/portal/FolhaPagamento/GestaoFolha",
    }
    resp = session.get(url, headers=headers)
    print(f"  [tabela] Status: {resp.status_code} | tamanho: {len(resp.text)} bytes")
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] Resposta inesperada — sessão pode ter expirado")
        return None
    return resp.text


def acessar_rubrica(session, guid):
    """
    Passo 1 — Abre a página de busca de rubricas.
    guid: GUID da página ex '890006fb-698b-401f-8c1d-914f6b0761e1'
    Retorna HTML ou None.
    """
    url = f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto?id={guid}"
    headers = {
        **HEADERS_BASE,
        "Referer": "https://www.esocial.gov.br/portal/FolhaPagamento/GestaoFolha",
    }
    resp = session.get(url, headers=headers)
    print(f"  [rubrica] Status: {resp.status_code} | {len(resp.text)} bytes")
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] Resposta inesperada")
        return None
    return resp.text


def buscar_rubrica(session, guid, codigo_rubrica, id_tabela_rubrica="0", pagina=""):
    """
    Passo 2 — POST de busca pelo código da rubrica.
    Retorna HTML com os resultados (contém idRubrica e idEvento).
    guid: mesmo GUID usado em acessar_rubrica
    codigo_rubrica: ex 'SEASTRALTR00000000000000000065'
    """
    url = f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto?id={guid}"
    data = {
        "IdTabelaRubrica": id_tabela_rubrica,
        "Codigo": codigo_rubrica,
        "Pagina": pagina,
    }
    headers = {
        **HEADERS_BASE,
        "Referer": url,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    resp = session.post(url, data=data, headers=headers)
    print(f"  [buscar_rubrica] Status: {resp.status_code} | {len(resp.text)} bytes")
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] Resposta inesperada")
        return None
    return resp.text


def abrir_edicao_rubrica(session, id_rubrica, id_evento, guid):
    """
    Passo 3 — Abre o formulário de edição de uma rubrica.
    id_rubrica e id_evento: extraídos do HTML retornado por buscar_rubrica
    guid: mesmo GUID da página de rubricas
    """
    url = (
        f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar"
        f"?idRubrica={id_rubrica}&idEvento={id_evento}"
    )
    referer = f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto?id={guid}"
    headers = {**HEADERS_BASE, "Referer": referer}
    resp = session.get(url, headers=headers)
    print(f"  [abrir_edicao] Status: {resp.status_code} | {len(resp.text)} bytes")
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] Resposta inesperada")
        return None
    return resp.text


def recuperar_incidencia_ir(session, id_rubrica, id_evento, inicio_validade, onload=""):
    """
    Passo 4 — AJAX que carrega a lista de incidências de IR do form de edição.
    inicio_validade: ex '03/2022' (mês/ano de início de validade da rubrica)
    """
    from urllib.parse import quote as _quote

    url = (
        f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/RecuperarListaIncidenciaIR"
        f"?inicioValidade={_quote(inicio_validade)}&onload={onload}"
    )
    referer = (
        f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar"
        f"?idRubrica={id_rubrica}&idEvento={id_evento}"
    )
    headers = {**HEADERS_BASE, "Referer": referer}
    resp = session.get(url, headers=headers)
    print(f"  [incidencia_ir] Status: {resp.status_code} | {len(resp.text)} bytes")
    return resp.text if resp.status_code == 200 else None


def acessar_home_empresa(session):
    """
    Acessa a home da empresa após selecionar_empresa.
    Retorna HTML (contém o link Rubrica/CadastroCompleto?id=GUID) ou None.
    """
    url = "https://www.esocial.gov.br/portal/Home/Inicial?tipoEmpregador=EMPREGADOR_GERAL"
    headers = {**HEADERS_BASE, "Referer": "https://www.esocial.gov.br/portal/Home/Index"}
    resp = session.get(url, headers=headers)
    print(f"  [home] Status: {resp.status_code} | {len(resp.text)} bytes")
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] Home inesperada")
        return None
    return resp.text


def salvar_edicao(session, id_rubrica, id_evento, campos_form):
    """
    POST para salvar a edição de uma rúbrica.
    campos_form: dict retornado por parsear_form_edicao, já com
                 DadosRubrica.CodigoIncidenciaIR atualizado.
    Retorna (status_code, html_resposta).
    allow_redirects=False para detectar 302 → /Assinadoc.
    """
    url = "https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar"
    referer = (
        f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar"
        f"?idRubrica={id_rubrica}&idEvento={id_evento}"
    )
    headers = {
        **HEADERS_BASE,
        "Referer": referer,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    resp = session.post(url, data=campos_form, headers=headers, allow_redirects=False)
    print(f"  [salvar_edicao] Status: {resp.status_code} | Location: {resp.headers.get('Location', '-')}")
    return resp.status_code, resp.text


def acessar_assinadoc(session):
    """
    GET /portal/Assinadoc — página que contém o link .jnlp para assinar.
    Retorna HTML ou None.
    """
    url = "https://www.esocial.gov.br/portal/Assinadoc"
    headers = {
        **HEADERS_BASE,
        "Referer": "https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar",
    }
    resp = session.get(url, headers=headers)
    print(f"  [assinadoc] Status: {resp.status_code} | {len(resp.text)} bytes")
    if resp.status_code != 200:
        return None
    return resp.text


def baixar_jnlp(session, url_jnlp, pasta_temp):
    """
    Baixa o arquivo .jnlp para pasta_temp.
    Retorna caminho do arquivo salvo ou None.
    """
    os.makedirs(pasta_temp, exist_ok=True)
    headers = {**HEADERS_BASE, "Referer": "https://www.esocial.gov.br/portal/Assinadoc"}
    resp = session.get(url_jnlp, headers=headers)
    if resp.status_code != 200:
        print(f"  [!] Falha ao baixar .jnlp: {resp.status_code}")
        return None
    nome = url_jnlp.split("/")[-1].split("?")[0]
    if not nome.endswith(".jnlp"):
        nome = "rubrica.jnlp"
    caminho = os.path.join(pasta_temp, nome)
    with open(caminho, "wb") as f:
        f.write(resp.content)
    print(f"  [jnlp] Salvo em: {caminho}")
    return caminho


# ── Execução ──────────────────────────────────────────────────────────────────

CNPJ = "39.451.131/0001-20"
GUID_RUBRICA = "890006fb-698b-401f-8c1d-914f6b0761e1"  # GUID da página de rubricas
CODIGO_RUBRICA = "SEASTRALTR00000000000000000065"  # código a buscar
ID_RUBRICA = "14176733644"  # vem do HTML de busca
ID_EVENTO = "14176733644"  # vem do HTML de busca
INICIO_VALIDADE = "03/2022"  # vem do form de edição

session = requests.Session()
cookies_base = ler_cookies(COOKIES_FILE)
session.cookies.update(cookies_base)

_usuario_logado_procurador = cookies_base.get("UsuarioLogado", "")
_cpf_procurador = cookies_base.get("usuario_logado_ws", "")

print(f"\n[RUBRICA] {CNPJ}")

ok = selecionar_empresa(session, CNPJ)
if not ok:
    print("Falhou ao selecionar empresa")
    exit(1)

# Passo 1 — página de busca
html = acessar_rubrica(session, GUID_RUBRICA)
if html:
    salvar_html(html, CNPJ, "rubrica_pagina")

# Passo 2 — busca pelo código → HTML contém idRubrica e idEvento
html = buscar_rubrica(session, GUID_RUBRICA, CODIGO_RUBRICA)
if html:
    salvar_html(html, CNPJ, f"rubrica_busca_{CODIGO_RUBRICA}")

# Passo 3 — form de edição (preencha ID_RUBRICA e ID_EVENTO com os valores do HTML acima)
html = abrir_edicao_rubrica(session, ID_RUBRICA, ID_EVENTO, GUID_RUBRICA)
if html:
    salvar_html(html, CNPJ, f"rubrica_edicao_{ID_RUBRICA}")

trocar_perfil(session, _usuario_logado_procurador, _cpf_procurador)
print("\nConcluído.")
