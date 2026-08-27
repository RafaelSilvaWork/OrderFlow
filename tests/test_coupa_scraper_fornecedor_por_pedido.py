import asyncio
import threading

from modules.coupa_scraper import CoupaScraper


class _FakeElement:
    """Simula um ElementHandle do Playwright - só o suficiente pra fornecedor
    (get_attribute/title) e pro texto cru do #msgbar (inner_text)."""

    def __init__(self, title=None, text=""):
        self._title = title
        self._text = text

    async def get_attribute(self, name):
        return self._title if name == "title" else None

    async def inner_text(self):
        return self._text

    async def click(self):
        pass


class _FakeReqPage:
    """Simula a página da requisição: msgbar com os PO's emitidos e,
    opcionalmente, um link de fornecedor na própria página (caso de 1
    pedido só). criado_por/solicitado_por ficam desligados via
    config_extrair nos testes, então não precisam de suporte aqui."""

    def __init__(self, msgbar_texto, fornecedor_title=None):
        self._msgbar_texto = msgbar_texto
        self._fornecedor_title = fornecedor_title
        self.url = "https://empresa.coupahost.com/requisition_headers/123"

    def set_default_timeout(self, ms):
        pass

    async def goto(self, url, wait_until=None, timeout=None):
        pass

    async def query_selector(self, selector):
        if selector == "#msgbar":
            return _FakeElement(text=self._msgbar_texto)
        if "suppliers/show" in selector and self._fornecedor_title:
            return _FakeElement(title=self._fornecedor_title)
        return None

    async def wait_for_selector(self, selector, state=None, timeout=None):
        return None

    async def evaluate(self, script, *args):
        return None


class _FakePoPage:
    """Simula a página de UM pedido (PO), aberta via context.new_page() -
    o fornecedor exposto e se a navegação falha dependem do número do PO
    embutido na URL (ver _FakeContext)."""

    def __init__(self, fornecedores_por_pedido, pedidos_com_erro, context):
        self._fornecedores_por_pedido = fornecedores_por_pedido
        self._pedidos_com_erro = pedidos_com_erro
        self._context = context
        self._numero_pedido = None

    def set_default_timeout(self, ms):
        pass

    async def goto(self, url, wait_until=None, timeout=None):
        self._context.goto_urls_log.append(url)
        self._numero_pedido = url.rstrip("/").split("/")[-1]
        if self._numero_pedido in self._pedidos_com_erro:
            raise Exception(f"Timeout ao abrir pedido {self._numero_pedido}")

    async def query_selector(self, selector):
        if "suppliers/show" in selector:
            title = self._fornecedores_por_pedido.get(self._numero_pedido)
            if title:
                return _FakeElement(title=title)
        return None

    async def wait_for_selector(self, selector, state=None, timeout=None):
        return None

    async def close(self):
        self._context.closed_pages_log.append(self._numero_pedido)


class _FakeContext:
    def __init__(self, req_page, fornecedores_por_pedido=None, pedidos_com_erro=None):
        self.pages = [req_page]
        self._fornecedores_por_pedido = fornecedores_por_pedido or {}
        self._pedidos_com_erro = pedidos_com_erro or set()
        self.goto_urls_log: list[str] = []
        self.closed_pages_log: list[str] = []
        self.new_page_calls = 0

    async def route(self, pattern, handler):
        pass

    async def new_page(self):
        self.new_page_calls += 1
        return _FakePoPage(self._fornecedores_por_pedido, self._pedidos_com_erro, self)


def _make_scraper(requisicoes=("123",)):
    login_event = threading.Event()
    login_event.set()
    return CoupaScraper(
        requisicoes=list(requisicoes),
        config_extrair={"criado_por": False, "solicitado_por": False},
        pause_event=None,
        login_confirmation_event=login_event,
        cancel_event=None,
    )


def test_requisicao_com_multiplos_pedidos_busca_fornecedor_de_cada_pedido(monkeypatch):
    """RC com 2 pedidos pra fornecedores diferentes - cada linha do resultado
    deve trazer o fornecedor do SEU PRÓPRIO pedido, não o da requisição."""
    monkeypatch.setattr("modules.coupa_scraper.get_coupa_base_url", lambda: "https://empresa.coupahost.com")

    msgbar_texto = "PO nº 606196 emitido. PO nº 606197 emitido."
    req_page = _FakeReqPage(msgbar_texto)  # sem fornecedor na própria página - não deve ser usado
    context = _FakeContext(
        req_page,
        fornecedores_por_pedido={
            "606196": "123 - FORNECEDOR A",
            "606197": "456 - FORNECEDOR B",
        },
    )
    scraper = _make_scraper()
    logs = []

    resultado = asyncio.run(scraper._extrair(context, logs.append, None, []))

    assert len(resultado) == 2
    assert resultado[0]["pedido"] == "PO nº 606196"
    assert resultado[0]["fornecedor"] == "FORNECEDOR A"
    assert resultado[0]["fornecedor_num"] == "123"
    assert resultado[1]["pedido"] == "PO nº 606197"
    assert resultado[1]["fornecedor"] == "FORNECEDOR B"
    assert resultado[1]["fornecedor_num"] == "456"
    assert context.goto_urls_log == [
        "https://empresa.coupahost.com/order_headers/606196",
        "https://empresa.coupahost.com/order_headers/606197",
    ]
    assert context.closed_pages_log == ["606196", "606197"]


def test_requisicao_com_um_unico_pedido_usa_fornecedor_da_propria_pagina(monkeypatch):
    """RC com 1 pedido só - sem ambiguidade, não deve abrir aba extra
    (context.new_page) pra buscar fornecedor: usa a própria página da
    requisição, como sempre funcionou."""
    monkeypatch.setattr("modules.coupa_scraper.get_coupa_base_url", lambda: "https://empresa.coupahost.com")

    msgbar_texto = "PO nº 999 emitido com sucesso."
    req_page = _FakeReqPage(msgbar_texto, fornecedor_title="789 - FORNECEDOR UNICO")
    context = _FakeContext(req_page)
    scraper = _make_scraper()
    logs = []

    resultado = asyncio.run(scraper._extrair(context, logs.append, None, []))

    assert len(resultado) == 1
    assert resultado[0]["fornecedor"] == "FORNECEDOR UNICO"
    assert resultado[0]["fornecedor_num"] == "789"
    assert context.new_page_calls == 0


def test_falha_ao_abrir_um_pedido_nao_derruba_a_extracao_dos_outros(monkeypatch):
    """Se abrir a página de um pedido falhar (timeout, pedido removido etc.),
    só aquele pedido fica com fornecedor "Não localizado" - os outros da
    mesma requisição continuam sendo processados normalmente."""
    monkeypatch.setattr("modules.coupa_scraper.get_coupa_base_url", lambda: "https://empresa.coupahost.com")

    msgbar_texto = "PO nº 111 emitido. PO nº 222 emitido."
    req_page = _FakeReqPage(msgbar_texto)
    context = _FakeContext(
        req_page,
        fornecedores_por_pedido={"222": "1 - FORNECEDOR OK"},
        pedidos_com_erro={"111"},
    )
    scraper = _make_scraper()
    logs = []

    resultado = asyncio.run(scraper._extrair(context, logs.append, None, []))

    assert len(resultado) == 2
    assert resultado[0]["fornecedor"] == "Não localizado"
    assert resultado[0]["fornecedor_num"] == "Não localizado"
    assert resultado[1]["fornecedor"] == "FORNECEDOR OK"
    assert any(
        "não foi possível identificar o fornecedor do pedido 111" in msg.lower() for msg in logs
    )
