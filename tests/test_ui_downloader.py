import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox

from modules import module_checkpoint
from modules.download_scraper import DownloadWorker
from modules.services.data_bus import DataBus
from modules.ui_downloader import OrcamentoDownloaderWidget


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def widget(qt_app):
    return OrcamentoDownloaderWidget(parent_framework=None)


@pytest.fixture(autouse=True)
def _checkpoint_isolado(tmp_path, monkeypatch):
    """Isola o checkpoint de execução num diretório temporário (ver
    modules/module_checkpoint.py, consultado no início de
    executar_downloads)."""
    monkeypatch.setattr(module_checkpoint, "USER_DATA_DIR", tmp_path)


def test_executar_downloads_sem_checkpoint_nao_pergunta_nada(widget, monkeypatch, tmp_path):
    perguntou = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: perguntou.append(1))
    monkeypatch.setattr(DownloadWorker, "start", lambda self: None)
    widget.pasta_download = str(tmp_path)
    widget.txt_req_list.setPlainText("111")

    widget.executar_downloads()

    assert perguntou == []
    assert widget.worker.scraper.requisicoes_originais == ["111"]


def test_executar_downloads_automatico_nunca_pergunta(widget, monkeypatch, tmp_path):
    """Fluxo automático (encadeado a partir da Aba 1) nunca deve travar
    esperando resposta de um diálogo."""
    module_checkpoint.save("downloader", ["111", "222"], {}, [{"requisicao": "111", "status": "salvo"}])
    perguntou = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: perguntou.append(1))
    monkeypatch.setattr(DownloadWorker, "start", lambda self: None)
    widget.pasta_download = str(tmp_path)
    widget.txt_req_list.setPlainText("111\n222")

    widget.executar_downloads(modo_automatico=True)

    assert perguntou == []


def test_oferecer_retomada_aceita_preenche_lista_e_guarda_estado(widget, monkeypatch):
    module_checkpoint.save(
        "downloader",
        ["111", "222", "333"],
        {},
        [{"requisicao": "111", "status": "salvo"}],
    )
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)

    widget._oferecer_retomada_checkpoint()

    assert widget.txt_req_list.toPlainText() == "222\n333"
    assert widget._resume_requisicoes_originais == ["111", "222", "333"]
    assert widget._resume_resultados_anteriores == [{"requisicao": "111", "status": "salvo"}]
    assert "Retomando" in widget.txt_logs.toPlainText()


def test_oferecer_retomada_recusa_descarta_checkpoint(widget, monkeypatch):
    module_checkpoint.save("downloader", ["111", "222"], {}, [])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)

    widget._oferecer_retomada_checkpoint()

    assert widget._resume_requisicoes_originais is None
    assert module_checkpoint.load("downloader") is None


def test_executar_downloads_retomada_passa_estado_pro_worker(widget, monkeypatch, tmp_path):
    module_checkpoint.save(
        "downloader",
        ["111", "222"],
        {},
        [{"requisicao": "111", "status": "sem_arquivo"}],
    )
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(DownloadWorker, "start", lambda self: None)
    widget.pasta_download = str(tmp_path)

    widget.executar_downloads()

    assert widget.worker.scraper.requisicoes == ["222"]
    assert widget.worker.scraper.requisicoes_originais == ["111", "222"]
    assert widget.worker.scraper.requisicoes_sem_arquivos == ["111"]


@pytest.fixture
def databus_limpo():
    DataBus.clear()
    yield
    DataBus.clear()


def _extracao(*requisicoes):
    return [{"requisicao": r, "status": "Com pedido", "pedido": f"PO nº {r}0"} for r in requisicoes]


def test_nova_extracao_substitui_lista_da_extracao_anterior(widget, databus_limpo):
    DataBus.store_extraction_results(_extracao("111", "222"))
    widget.importar_da_aba1()
    assert widget.txt_req_list.toPlainText() == "111\n222"

    DataBus.store_extraction_results(_extracao("333"))
    widget.ao_concluir_extracao()

    assert widget.txt_req_list.toPlainText() == "333"


def test_nova_extracao_sobrescreve_edicao_manual_sobre_a_anterior(widget, databus_limpo):
    DataBus.store_extraction_results(_extracao("111"))
    widget.importar_da_aba1()
    widget.txt_req_list.setPlainText("999")
    widget._user_editou_manualmente = True

    DataBus.store_extraction_results(_extracao("333"))
    widget.ao_concluir_extracao()

    assert widget.txt_req_list.toPlainText() == "333"
    assert widget._user_editou_manualmente is False


def test_nova_extracao_sem_pedidos_limpa_lista_antiga(widget, databus_limpo):
    DataBus.store_extraction_results(_extracao("111"))
    widget.importar_da_aba1()

    DataBus.store_extraction_results([{"requisicao": "444", "status": "Sem pedido emitido"}])
    widget.ao_concluir_extracao()

    assert widget.txt_req_list.toPlainText() == ""
    assert "não encontrou" in widget.lbl_import_status.text()


def test_importar_da_aba1_sem_dados_nao_apaga_texto_digitado(widget, databus_limpo):
    widget.txt_req_list.setPlainText("manual")

    widget.importar_da_aba1()

    assert widget.txt_req_list.toPlainText() == "manual"
    assert "Aguardando" in widget.lbl_import_status.text()


def test_importacao_mostra_de_qual_extracao_vieram_os_dados(widget, databus_limpo):
    DataBus.store_extraction_results(_extracao("111"))

    widget.importar_da_aba1()

    hora = DataBus.get_extraction_time_label()
    assert f"(extração de {hora})" in widget.lbl_import_status.text()


def test_extracao_sem_pedidos_informa_a_hora_dela(widget, databus_limpo):
    DataBus.store_extraction_results([{"requisicao": "444", "status": "Sem pedido emitido"}])

    widget.ao_concluir_extracao()

    hora = DataBus.get_extraction_time_label()
    assert f"Aba 1, {hora}" in widget.lbl_import_status.text()
