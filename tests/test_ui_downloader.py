import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox

from modules import module_checkpoint
from modules.download_scraper import DownloadWorker
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
