import asyncio
import threading

from modules.config import MAX_TENTATIVAS
from modules.coupa_scraper import CoupaScraper

_TIMEOUT_EXC_TEXT = (
    "Timeout 30000ms exceeded while navigating to "
    "https://empresa.coupahost.com/requisition_headers/123"
)
_CONNECTION_REFUSED_TEXT = "net::ERR_CONNECTION_REFUSED at https://empresa.coupahost.com/"


class _FakePage:
    """Simula só o suficiente da API do Playwright pra exercitar o retry de goto.

    Com config_extrair={}, uma requisição sem #msgbar cai direto em "Sem
    pedido emitido" logo após o primeiro query_selector de #msgbar - não
    precisa simular fornecedor/criado_por/etc.
    """

    def __init__(self, goto_effects):
        self._goto_effects = list(goto_effects)
        self.goto_calls = 0
        self.url = "https://empresa.coupahost.com/requisition_headers/123"

    def set_default_timeout(self, ms):
        pass

    async def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls += 1
        effect = self._goto_effects.pop(0)
        if isinstance(effect, Exception):
            raise effect

    async def query_selector(self, selector):
        return None

    async def wait_for_selector(self, selector, state=None, timeout=None):
        return None

    async def evaluate(self, script, *args):
        return None


class _FakeContext:
    def __init__(self, page):
        self.pages = [page]

    async def route(self, pattern, handler):
        pass


def _make_scraper(requisicoes=("123",)):
    login_event = threading.Event()
    login_event.set()
    return CoupaScraper(
        requisicoes=list(requisicoes),
        config_extrair={},
        pause_event=None,
        login_confirmation_event=login_event,
        cancel_event=None,
    )


def _timeout_exc():
    return Exception(_TIMEOUT_EXC_TEXT)


def _connection_refused_exc():
    return Exception(_CONNECTION_REFUSED_TEXT)


def test_retry_recupera_apos_timeout_transitorio(monkeypatch):
    monkeypatch.setattr("modules.coupa_scraper.get_coupa_base_url", lambda: "https://empresa.coupahost.com")

    # goto: home OK, 1a tentativa da requisicao falha, 2a tentativa OK
    page = _FakePage(goto_effects=[None, _timeout_exc(), None])
    context = _FakeContext(page)
    scraper = _make_scraper()
    logs = []

    resultado = asyncio.run(scraper._extrair(context, logs.append, None, []))

    assert page.goto_calls == 3
    assert resultado == [{"requisicao": "123", "status": "Sem pedido emitido"}]
    assert any("tentando novamente" in msg.lower() for msg in logs)
    assert not any("abortando" in msg.lower() for msg in logs)


def test_timeout_isolado_esgota_tentativas_mas_nao_aborta_lote(monkeypatch):
    """Timeout isolado (não é DNS/conexão recusada) não indica host inteiro
    fora do ar - só essa requisição fica marcada com erro, sem abortar."""
    monkeypatch.setattr("modules.coupa_scraper.get_coupa_base_url", lambda: "https://empresa.coupahost.com")
    monkeypatch.setattr("modules.coupa_scraper.ESPERA_ENTRE_TENTATIVAS", 0)

    # goto: home OK, todas as MAX_TENTATIVAS tentativas da requisicao falham
    page = _FakePage(goto_effects=[None] + [_timeout_exc() for _ in range(MAX_TENTATIVAS)])
    context = _FakeContext(page)
    scraper = _make_scraper()
    logs = []

    resultado = asyncio.run(scraper._extrair(context, logs.append, None, []))

    assert page.goto_calls == 1 + MAX_TENTATIVAS
    assert len(resultado) == 1
    assert resultado[0]["requisicao"] == "123"
    assert "demorou" in resultado[0]["erro"].lower()
    assert not any("abortando" in msg.lower() for msg in logs)


def test_timeout_isolado_no_meio_do_lote_continua_para_proxima(monkeypatch):
    """Depois de esgotar as tentativas numa requisição lenta, a próxima da
    lista ainda deve ser processada normalmente - não é o lote inteiro que
    para."""
    monkeypatch.setattr("modules.coupa_scraper.get_coupa_base_url", lambda: "https://empresa.coupahost.com")
    monkeypatch.setattr("modules.coupa_scraper.ESPERA_ENTRE_TENTATIVAS", 0)

    # home OK, MAX_TENTATIVAS falhas na req "123", depois a req "456" sobe de primeira
    page = _FakePage(
        goto_effects=[None] + [_timeout_exc() for _ in range(MAX_TENTATIVAS)] + [None]
    )
    context = _FakeContext(page)
    scraper = _make_scraper(requisicoes=["123", "456"])
    logs = []

    resultado = asyncio.run(scraper._extrair(context, logs.append, None, []))

    assert page.goto_calls == 1 + MAX_TENTATIVAS + 1
    assert len(resultado) == 2
    assert resultado[0]["requisicao"] == "123"
    assert "demorou" in resultado[0]["erro"].lower()
    assert resultado[1] == {"requisicao": "456", "status": "Sem pedido emitido"}


def test_erro_de_conexao_recusada_ainda_aborta_o_lote(monkeypatch):
    """Diferente do timeout isolado, DNS falhando ou conexão recusada
    realmente indicam o host inteiro inacessível - aborta o restante."""
    monkeypatch.setattr("modules.coupa_scraper.get_coupa_base_url", lambda: "https://empresa.coupahost.com")
    monkeypatch.setattr("modules.coupa_scraper.ESPERA_ENTRE_TENTATIVAS", 0)

    page = _FakePage(goto_effects=[None] + [_connection_refused_exc() for _ in range(MAX_TENTATIVAS)])
    context = _FakeContext(page)
    scraper = _make_scraper(requisicoes=["123", "456"])
    logs = []

    resultado = asyncio.run(scraper._extrair(context, logs.append, None, []))

    assert page.goto_calls == 1 + MAX_TENTATIVAS  # a requisicao "456" nunca chega a ser tentada
    assert resultado == [{"requisicao": "123", "erro": resultado[0]["erro"]}]
    assert any("abortando" in msg.lower() for msg in logs)


def test_extracao_concluida_normalmente_loga_resumo_final(monkeypatch):
    """AutomationWorker.log_with_progress procura por uma mensagem com
    "extração" + "concluída" pra levar a barra de progresso a 100% - sem
    _extrair() efetivamente logar isso ao terminar, a barra nunca chegava lá
    e nenhum resumo de sucesso aparecia no log (bug desde o commit inicial)."""
    monkeypatch.setattr("modules.coupa_scraper.get_coupa_base_url", lambda: "https://empresa.coupahost.com")

    page = _FakePage(goto_effects=[None, None])
    context = _FakeContext(page)
    scraper = _make_scraper()
    logs = []

    asyncio.run(scraper._extrair(context, logs.append, None, []))

    resumo = [msg for msg in logs if "extração" in msg.lower() and "concluída" in msg.lower()]
    assert len(resumo) == 1
    assert "0 pedido(s) encontrado(s)" in resumo[0]
    assert "1 sem pedido emitido" in resumo[0]
    assert "0 com erro" in resumo[0]


def test_extracao_cancelada_nao_loga_resumo_final(monkeypatch):
    """Cancelamento já tem sua própria mensagem terminal ("cancelada pelo
    usuário") - logar "concluída" também ficaria contraditório/confuso."""
    monkeypatch.setattr("modules.coupa_scraper.get_coupa_base_url", lambda: "https://empresa.coupahost.com")

    page = _FakePage(goto_effects=[None])
    context = _FakeContext(page)
    login_event = threading.Event()
    login_event.set()
    cancel_event = threading.Event()
    cancel_event.set()
    scraper = CoupaScraper(
        requisicoes=["123"],
        config_extrair={},
        pause_event=None,
        login_confirmation_event=login_event,
        cancel_event=cancel_event,
    )
    logs = []

    asyncio.run(scraper._extrair(context, logs.append, None, []))

    assert any("cancelada" in msg.lower() for msg in logs)
    assert not any("extração" in msg.lower() and "concluída" in msg.lower() for msg in logs)


def test_falha_nao_relacionada_a_rede_nao_aciona_retry(monkeypatch):
    """Um erro que não é de rede (ex: seletor quebrado) não deve ser retentado
    nem tratado como abortando o lote - só essa requisição falha."""
    monkeypatch.setattr("modules.coupa_scraper.get_coupa_base_url", lambda: "https://empresa.coupahost.com")

    page = _FakePage(goto_effects=[None, ValueError("Element not found: .po-number")])
    context = _FakeContext(page)
    scraper = _make_scraper()
    logs = []

    resultado = asyncio.run(scraper._extrair(context, logs.append, None, []))

    assert page.goto_calls == 2
    assert resultado == [{"requisicao": "123", "erro": "Falha na extração: Element not found: .po-number"}]
    assert not any("abortando" in msg.lower() for msg in logs)
