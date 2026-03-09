import os
import re
import time
from urllib.parse import quote

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
        print(f"  [!] Tentativa {tentativa} — servidor sem sessão (status {resp.status_code}), retentando...")
        time.sleep(0.5)

    if not match:
        return False

    usuario_logado = match.group(1)

    session.cookies.set("UsuarioLogado", usuario_logado, domain="www.esocial.gov.br", path="/")
    session.cookies.set("usuario_logado_ws", cnpj_formatado, domain="www.esocial.gov.br", path="/")

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
    """Reseta o contexto de volta ao procurador após terminar uma empresa."""
    session.cookies.set("UsuarioLogado", usuario_logado_procurador, domain="www.esocial.gov.br", path="/")
    session.cookies.set("usuario_logado_ws", cpf_procurador, domain="www.esocial.gov.br", path="/")

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


def extrair_nome_empresa(session):
    """
    Extrai o nome da empresa do cookie UsuarioLogado.
    Retorna string com o nome ou "Empresa desconhecida" se não encontrar.
    """
    valor = session.cookies.get("UsuarioLogado", "")
    m = re.search(r"Nome=([^&]+)", valor)
    return m.group(1) if m else "Empresa desconhecida"


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
    """Abre a página de busca de rubricas. Retorna HTML ou None."""
    url = f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto?id={guid}"
    headers = {**HEADERS_BASE, "Referer": "https://www.esocial.gov.br/portal/FolhaPagamento/GestaoFolha"}
    resp = session.get(url, headers=headers)
    print(f"  [rubrica] Status: {resp.status_code} | {len(resp.text)} bytes")
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] Resposta inesperada")
        return None
    return resp.text


def buscar_rubrica(session, guid, codigo_rubrica, id_tabela_rubrica="0", pagina=""):
    """
    POST de busca pelo código da rubrica.
    Retorna HTML com os resultados (contém idRubrica e idEvento).
    """
    url = f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto?id={guid}"
    data = {"IdTabelaRubrica": id_tabela_rubrica, "Codigo": codigo_rubrica, "Pagina": pagina}
    headers = {**HEADERS_BASE, "Referer": url, "Content-Type": "application/x-www-form-urlencoded"}
    resp = session.post(url, data=data, headers=headers)
    print(f"  [buscar_rubrica] Status: {resp.status_code} | {len(resp.text)} bytes")
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] Resposta inesperada")
        return None
    return resp.text


def abrir_edicao_rubrica(session, id_rubrica, id_evento, guid):
    """Abre o formulário de edição de uma rubrica. Retorna HTML ou None."""
    url = (
        f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar"
        f"?idRubrica={id_rubrica}&idEvento={id_evento}"
    )
    headers = {**HEADERS_BASE, "Referer": f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto?id={guid}"}
    resp = session.get(url, headers=headers)
    print(f"  [abrir_edicao] Status: {resp.status_code} | {len(resp.text)} bytes")
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] Resposta inesperada")
        return None
    return resp.text


def salvar_edicao(session, id_rubrica, id_evento, campos_form):
    """
    POST para salvar a edição de uma rúbrica.
    Retorna (status_code, html_resposta).
    allow_redirects=False para detectar 302 → /Assinadoc.
    """
    url = "https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar"
    referer = f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar?idRubrica={id_rubrica}&idEvento={id_evento}"
    headers = {**HEADERS_BASE, "Referer": referer, "Content-Type": "application/x-www-form-urlencoded"}
    resp = session.post(url, data=campos_form, headers=headers, allow_redirects=False)
    print(f"  [salvar_edicao] Status: {resp.status_code} | Location: {resp.headers.get('Location', '-')}")
    return resp.status_code, resp.text


def acessar_assinadoc(session):
    """GET /portal/Assinadoc — página com o link .jnlp para assinar. Retorna HTML ou None."""
    url = "https://www.esocial.gov.br/portal/Assinadoc"
    headers = {**HEADERS_BASE, "Referer": "https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar"}
    resp = session.get(url, headers=headers)
    print(f"  [assinadoc] Status: {resp.status_code} | {len(resp.text)} bytes")
    return resp.text if resp.status_code == 200 else None


def baixar_jnlp(session, url_jnlp, pasta_temp):
    """Baixa o arquivo .jnlp para pasta_temp. Retorna caminho do arquivo salvo ou None."""
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
