import os
import re
import time
from urllib.parse import quote

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


PAUSA_COLETIVA_LIMIAR = 6.0  # se TODOS os workers > 6s, pausa coletiva
PAUSA_COLETIVA_DURACAO = 120  # segundos (2 minutos)
PAUSA_COLETIVA_COOLDOWN = (
    300  # após pausa coletiva, aguarda 5min antes de poder disparar outra
)

PAUSA_PERIODICA_A_CADA = 1000  # requests totais entre todos os workers
PAUSA_PERIODICA_DURACAO = 300  # segundos (5 minutos)


class Throttle:
    """Throttle adaptativo com pausa coletiva e pausa periódica a cada N requests."""

    LIMIAR_LENTO = 5.0
    LIMIAR_RAPIDO = 3.0
    DELAY_MAX = 2.0

    def __init__(self):
        self._delay = 0.0
        # Compartilhados entre processos (configurados via configurar_compartilhado)
        self._shared_times = None  # Array('d', n_workers)
        self._shared_pause_until = None  # Value('d', 0.0)
        self._shared_req_count = None  # Value('i', 0) — contador global de requests
        self._shared_lock = None  # Lock para incremento atômico
        self._worker_index = None
        self._n_workers = 0

    def configurar_compartilhado(
        self,
        shared_times,
        shared_pause_until,
        worker_index,
        n_workers,
        shared_req_count=None,
        shared_lock=None,
    ):
        """Conecta este throttle ao estado compartilhado entre workers."""
        self._shared_times = shared_times
        self._shared_pause_until = shared_pause_until
        self._worker_index = worker_index
        self._n_workers = n_workers
        self._shared_req_count = shared_req_count
        self._shared_lock = shared_lock

    def antes(self):
        """Chama antes de cada request. Aplica pausa coletiva/periódica ou delay individual."""
        if self._shared_pause_until is not None:
            restante = self._shared_pause_until.value - time.time()
            if restante > 0:
                print(
                    f"  [pausa] aguardando {restante:.0f}s...",
                    flush=True,
                )
                time.sleep(restante)
                self._delay = 0.0  # servidor descansou, reseta delay individual
                return

        if self._delay > 0:
            time.sleep(self._delay)

    def depois(self, duracao):
        """Chama depois de cada request com a duração em segundos."""
        # Atualiza tempo individual no array compartilhado
        if self._shared_times is not None and self._worker_index is not None:
            self._shared_times[self._worker_index] = duracao
            self._verificar_pausa_coletiva()

        # Incrementa contador global e verifica pausa periódica
        if self._shared_req_count is not None:
            self._verificar_pausa_periodica()

        if duracao > self.LIMIAR_LENTO:
            self._delay = min(self._delay + 0.5, self.DELAY_MAX)
            print(
                f"  [throttle] resposta lenta ({duracao:.1f}s) → delay={self._delay:.1f}s"
            )
        elif duracao < self.LIMIAR_RAPIDO and self._delay > 0:
            self._delay = max(self._delay - 0.25, 0.0)

    def _verificar_pausa_periodica(self):
        """A cada PAUSA_PERIODICA_A_CADA requests globais, pausa todos por 5min."""
        with self._shared_lock:
            self._shared_req_count.value += 1
            contagem = self._shared_req_count.value

        if contagem % PAUSA_PERIODICA_A_CADA == 0:
            # Só ativa se não já estiver em pausa
            if self._shared_pause_until.value <= time.time():
                pausa_ate = time.time() + PAUSA_PERIODICA_DURACAO
                self._shared_pause_until.value = pausa_ate
                self._delay = 0.0
                # Reseta tempos para evitar pausa coletiva imediata ao retomar
                if self._shared_times is not None:
                    for i in range(self._n_workers):
                        self._shared_times[i] = 0.0
                print(
                    f"\n  [PAUSA PERIÓDICA] {contagem} requests atingidas"
                    f" — pausando {PAUSA_PERIODICA_DURACAO}s (5min)\n",
                    flush=True,
                )

    def _verificar_pausa_coletiva(self):
        """Se TODOS os workers estão com resposta > LIMIAR, ativa pausa coletiva de 2min."""
        if self._shared_pause_until is None:
            return

        agora = time.time()
        pause_until = self._shared_pause_until.value

        # Pausa ativa — não re-disparar
        if pause_until > agora:
            return

        # Cooldown: após pausa terminar, aguarda COOLDOWN antes de poder disparar outra.
        # pause_until > 0 indica que já houve ao menos uma pausa.
        # (agora - pause_until) = tempo desde que a última pausa expirou.
        if pause_until > 0 and (agora - pause_until) < PAUSA_COLETIVA_COOLDOWN:
            return

        tempos = [self._shared_times[i] for i in range(self._n_workers)]
        if all(t > PAUSA_COLETIVA_LIMIAR for t in tempos):
            pausa_ate = agora + PAUSA_COLETIVA_DURACAO
            self._shared_pause_until.value = pausa_ate
            self._delay = 0.0
            # Reseta tempos para evitar re-disparo por requests em voo
            for i in range(self._n_workers):
                self._shared_times[i] = 0.0
            print(
                f"\n  [PAUSA COLETIVA] Todos os {self._n_workers} workers com resposta >"
                f" {PAUSA_COLETIVA_LIMIAR}s — pausando {PAUSA_COLETIVA_DURACAO}s"
                f" (tempos: {[f'{t:.1f}s' for t in tempos]})\n",
                flush=True,
            )

    @property
    def delay(self):
        return self._delay


# Instância global — cada processo (worker) terá a sua via fork
_throttle = Throttle()


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
    for tentativa in range(1, 10):
        _throttle.antes()
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

    session.cookies.set(
        "UsuarioLogado", usuario_logado, domain="www.esocial.gov.br", path="/"
    )
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
    """Reseta o contexto de volta ao procurador após terminar uma empresa."""
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
    _throttle.antes()
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
    valor = (
        session.cookies.get("UsuarioLogado", domain="www.esocial.gov.br", path="/")
        or ""
    )
    m = re.search(r"Nome=([^&]+)", valor)
    return m.group(1) if m else "Empresa desconhecida"


def acessar_home_empresa(session):
    """
    Acessa a home da empresa após selecionar_empresa.
    Retorna HTML (contém o link Rubrica/CadastroCompleto?id=GUID) ou None.
    """
    url = (
        "https://www.esocial.gov.br/portal/Home/Inicial?tipoEmpregador=EMPREGADOR_GERAL"
    )
    headers = {
        **HEADERS_BASE,
        "Referer": "https://www.esocial.gov.br/portal/Home/Index",
    }
    _throttle.antes()
    resp = session.get(url, headers=headers)
    print(f"  [home] Status: {resp.status_code} | {len(resp.text)} bytes")
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] Home inesperada")
        return None
    return resp.text


def acessar_lista_remuneracao(session, competencia, guid, possui_dae="False"):
    """
    GET em ListaRemuneracao para obter o __RequestVerificationToken necessário
    para o POST de RemuneracaoCompleto.
    Retorna HTML ou None.
    """
    url = (
        f"https://www.esocial.gov.br/portal/FolhaPagamento/ListaRemuneracao"
        f"?Competencia={competencia}&Tipo=1200&PossuiDae={possui_dae}"
    )
    headers = {
        **HEADERS_BASE,
        "Referer": f"https://www.esocial.gov.br/portal/FolhaPagamento/GestaoFolha?id={guid}",
    }
    _throttle.antes()
    t0 = time.monotonic()
    resp = session.get(url, headers=headers)
    _throttle.depois(time.monotonic() - t0)
    print(
        f"  [lista] Status: {resp.status_code} | {len(resp.text)} bytes | competencia={competencia}"
    )
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] ListaRemuneracao inesperada")
        return None

    return resp.text


def acessar_tabela_funcionário(session, cpf, competencia, guid, possui_dae="False"):
    """
    GET para RemuneracaoCompleto com Referer apontando para ListaRemuneracao.
    Retorna o HTML com as tabelas de rúbricas ou None em caso de erro.
    """
    url = (
        f"https://www.esocial.gov.br/portal/FolhaPagamento/RemuneracaoCompleto"
        f"?cpf={cpf}&competencia={competencia}&possuiDae={possui_dae}&tipo=1200&visualizar=true"
    )
    headers = {
        **HEADERS_BASE,
        "Referer": (
            f"https://www.esocial.gov.br/portal/FolhaPagamento/ListaRemuneracao"
            f"?Competencia={competencia}&Tipo=1200&PossuiDae={possui_dae}"
        ),
    }
    _throttle.antes()
    t0 = time.monotonic()
    resp = session.get(url, headers=headers)
    _throttle.depois(time.monotonic() - t0)
    print(
        f"  [tabela] Status: {resp.status_code} | tamanho: {len(resp.text)} bytes | cpf={cpf} mes={competencia}"
    )
    if resp.status_code != 200 or "eSocial" not in resp.text:
        print("  [!] Resposta inesperada — sessão pode ter expirado")
        return None
    return resp.text


def acessar_rubrica(session, guid):
    """Abre a página de busca de rubricas. Retorna HTML ou None."""
    url = f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto?id={guid}"
    headers = {
        **HEADERS_BASE,
        "Referer": "https://www.esocial.gov.br/portal/FolhaPagamento/GestaoFolha",
    }
    _throttle.antes()
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
    _throttle.antes()
    t0 = time.monotonic()
    resp = session.post(url, data=data, headers=headers)
    _throttle.depois(time.monotonic() - t0)
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
    headers = {
        **HEADERS_BASE,
        "Referer": f"https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto?id={guid}",
    }
    _throttle.antes()
    t0 = time.monotonic()
    resp = session.get(url, headers=headers)
    _throttle.depois(time.monotonic() - t0)
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
    headers = {
        **HEADERS_BASE,
        "Referer": referer,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    _throttle.antes()
    resp = session.post(url, data=campos_form, headers=headers, allow_redirects=False)
    print(
        f"  [salvar_edicao] Status: {resp.status_code} | Location: {resp.headers.get('Location', '-')}"
    )
    return resp.status_code, resp.text


def acessar_assinadoc(session):
    """GET /portal/Assinadoc — página com o link .jnlp para assinar. Retorna HTML ou None."""
    url = "https://www.esocial.gov.br/portal/Assinadoc"
    headers = {
        **HEADERS_BASE,
        "Referer": "https://www.esocial.gov.br/portal/Rubrica/CadastroCompleto/Editar",
    }
    _throttle.antes()
    resp = session.get(url, headers=headers)
    print(f"  [assinadoc] Status: {resp.status_code} | {len(resp.text)} bytes")
    return resp.text if resp.status_code == 200 else None


def baixar_jnlp(session, url_jnlp, pasta_temp):
    """Baixa o arquivo .jnlp para pasta_temp. Retorna caminho do arquivo salvo ou None."""
    os.makedirs(pasta_temp, exist_ok=True)
    headers = {**HEADERS_BASE, "Referer": "https://www.esocial.gov.br/portal/Assinadoc"}
    _throttle.antes()
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
