import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox

from modules import module_checkpoint
from modules.pdf_generator import PdfGeneratorWorker
from modules.services.data_bus import DataBus
from modules.ui_pdf_generator import PedidoPdfGeneratorWidget


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def widget(qt_app):
    return PedidoPdfGeneratorWidget(parent_framework=None)


@pytest.fixture(autouse=True)
def _checkpoint_isolado(tmp_path, monkeypatch):
    """Isola o checkpoint de execução num diretório temporário (ver
    modules/module_checkpoint.py, consultado no início de iniciar_geracao)."""
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", tmp_path)


def test_iniciar_geracao_sem_checkpoint_nao_pergunta_nada(widget, monkeypatch, tmp_path):
    perguntou = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: perguntou.append(1))
    monkeypatch.setattr(PdfGeneratorWorker, "start", lambda self: None)
    widget.pasta_saida = str(tmp_path)
    widget.txt_pedidos.setPlainText("PED-100")

    widget.iniciar_geracao()

    assert perguntou == []
    assert widget.worker.pedidos_originais == ["PED-100"]


def test_iniciar_geracao_automatico_nunca_pergunta(widget, monkeypatch, tmp_path):
    module_checkpoint.save("pdf", ["PED-100", "PED-200"], {}, [{"pedido": "PED-100", "status": "sucesso"}])
    perguntou = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: perguntou.append(1))
    monkeypatch.setattr(PdfGeneratorWorker, "start", lambda self: None)
    widget.pasta_saida = str(tmp_path)
    widget.txt_pedidos.setPlainText("PED-100\nPED-200")

    widget.iniciar_geracao(modo_automatico=True)

    assert perguntou == []


def test_oferecer_retomada_aceita_preenche_lista_e_guarda_estado(widget, monkeypatch):
    module_checkpoint.save(
        "pdf",
        ["PED-100", "PED-200", "PED-300"],
        {"requisicoes_por_pedido": {"PED-200": ["REQ-9"]}},
        [{"pedido": "PED-100", "status": "sucesso", "detalhe": "PDF gerado com sucesso"}],
    )
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)

    widget._oferecer_retomada_checkpoint()

    assert widget.txt_pedidos.toPlainText() == "PED-200\tREQ-9\nPED-300\t"
    assert widget._resume_pedidos_originais == ["PED-100", "PED-200", "PED-300"]
    assert widget._resume_resultados_anteriores == [
        {"pedido": "PED-100", "status": "sucesso", "detalhe": "PDF gerado com sucesso"}
    ]
    assert "Retomando" in widget.txt_logs.toPlainText()


def test_oferecer_retomada_recusa_descarta_checkpoint(widget, monkeypatch):
    module_checkpoint.save("pdf", ["PED-100", "PED-200"], {}, [])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)

    widget._oferecer_retomada_checkpoint()

    assert widget._resume_pedidos_originais is None
    assert module_checkpoint.load("pdf") is None


def test_iniciar_geracao_retomada_passa_estado_pro_worker(widget, monkeypatch, tmp_path):
    module_checkpoint.save(
        "pdf",
        ["PED-100", "PED-200"],
        {},
        [{"pedido": "PED-100", "status": "sem_documento", "detalhe": "Documento ainda em processamento interno"}],
    )
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(PdfGeneratorWorker, "start", lambda self: None)
    widget.pasta_saida = str(tmp_path)

    widget.iniciar_geracao()

    assert widget.worker.pedidos == ["PED-200"]
    assert widget.worker.pedidos_originais == ["PED-100", "PED-200"]
    assert widget.worker._contagem_anterior == {"sucesso": 0, "sem_documento": 1, "falha": 0}


@pytest.fixture
def databus_limpo():
    DataBus.clear()
    yield
    DataBus.clear()


def _extracao(*pares):
    return [{"requisicao": req, "status": "Com pedido", "pedido": f"PO nº {ped}"} for req, ped in pares]


def test_nova_extracao_substitui_lista_da_extracao_anterior(widget, databus_limpo):
    DataBus.store_extraction_results(_extracao(("111", "5001"), ("222", "5002")))
    widget.importar_da_aba1()
    assert widget.txt_pedidos.toPlainText() == "5001\t111\n5002\t222"

    DataBus.store_extraction_results(_extracao(("333", "6001")))
    widget.ao_concluir_extracao()

    assert widget.txt_pedidos.toPlainText() == "6001\t333"


def test_nova_extracao_sobrescreve_edicao_manual_sobre_a_anterior(widget, databus_limpo):
    DataBus.store_extraction_results(_extracao(("111", "5001")))
    widget.importar_da_aba1()
    widget.txt_pedidos.setPlainText("9999")
    widget._user_editou_manualmente = True

    DataBus.store_extraction_results(_extracao(("333", "6001")))
    widget.ao_concluir_extracao()

    assert widget.txt_pedidos.toPlainText() == "6001\t333"
    assert widget._user_editou_manualmente is False


def test_nova_extracao_sem_pedidos_limpa_lista_antiga(widget, databus_limpo):
    DataBus.store_extraction_results(_extracao(("111", "5001")))
    widget.importar_da_aba1()

    DataBus.store_extraction_results([{"requisicao": "444", "status": "Sem pedido emitido"}])
    widget.ao_concluir_extracao()

    assert widget.txt_pedidos.toPlainText() == ""
    assert "não encontrou" in widget.lbl_import_status.text()


def test_importar_da_aba1_sem_dados_nao_apaga_texto_digitado(widget, databus_limpo):
    widget.txt_pedidos.setPlainText("manual")

    widget.importar_da_aba1()

    assert widget.txt_pedidos.toPlainText() == "manual"
    assert "Aguardando" in widget.lbl_import_status.text()


def test_importacao_mostra_de_qual_extracao_vieram_os_dados(widget, databus_limpo):
    DataBus.store_extraction_results(_extracao(("111", "5001")))

    widget.importar_da_aba1()

    hora = DataBus.get_extraction_time_label()
    assert f"(extração de {hora})" in widget.lbl_import_status.text()


def test_extracao_sem_pedidos_informa_a_hora_dela(widget, databus_limpo):
    DataBus.store_extraction_results([{"requisicao": "444", "status": "Sem pedido emitido"}])

    widget.ao_concluir_extracao()

    hora = DataBus.get_extraction_time_label()
    assert f"Aba 1, {hora}" in widget.lbl_import_status.text()
