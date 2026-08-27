from modules.services.data_bus import DataBus


def setup_function():
    DataBus.clear()


def test_store_and_get():
    DataBus.store("key", "value")
    assert DataBus.get("key") == "value"


def test_get_default():
    assert DataBus.get("missing", "default") == "default"


def test_has():
    DataBus.store("x", 1)
    assert DataBus.has("x")
    assert not DataBus.has("y")


def test_clear_key():
    DataBus.store("a", 1)
    DataBus.store("b", 2)
    DataBus.clear("a")
    assert not DataBus.has("a")
    assert DataBus.has("b")


def test_store_extraction_results_and_helpers():
    results = [
        {"requisicao": "100", "status": "Com pedido", "pedido": "PO 999"},
        {"requisicao": "101", "status": "Sem pedido emitido"},
        {"requisicao": "102", "erro": "falhou"},
    ]
    DataBus.store_extraction_results(results)

    reqs = DataBus.get_requisicoes_com_pedido()
    assert reqs == ["100"]

    pedidos = DataBus.get_pedidos_extraidos()
    assert len(pedidos) == 1
    assert pedidos[0].startswith("999")

    validos = DataBus.get_resultados_validos_para_email()
    assert len(validos) == 1
    assert validos[0]["requisicao"] == "100"
